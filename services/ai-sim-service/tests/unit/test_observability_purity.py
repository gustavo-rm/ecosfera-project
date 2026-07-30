"""A invariante do ADR-ARCH-0002: a simulação nunca depende da observabilidade.

Três afirmações verificáveis:

1. o sink é acionado DEPOIS que o tick foi composto e fechado;
2. o resultado do tick é idêntico com o sink ligado e desligado;
3. estourar o orçamento emite `DiagnosticEvent` e não muda um bit do estado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.noop.service import NoOpEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.shared_kernel.engine import (
    PerfSample,
    TickBudget,
    TickContext,
    TickResult,
)
from ecosfera_ai.shared_kernel.events import CoreCauseCode, DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore, NullSink
from ecosfera_ai.shared_kernel.world_state import (
    NonNegativeStocks,
    SliceRef,
    StateDelta,
    WorldStateSnapshot,
)


@dataclass(slots=True)
class _SpySink:
    """Sink que registra QUANDO foi chamado, não só o quê."""

    calls: list[str] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)

    def record_metrics(self, sample: PerfSample) -> None:
        self.calls.append(f"metrics:{sample.engine_id}")

    def emit(self, event: DomainEvent) -> None:
        self.calls.append(f"event:{event.event_type}")
        self.events.append(event)

    def log(self, message: str, /, **fields: object) -> None:
        self.calls.append(f"log:{message}")


@dataclass(slots=True)
class _Reporter:
    """Engine que anota, no próprio log, o instante em que calculou."""

    calls: list[str]
    engine_id: str = "reporter"
    reads: frozenset[SliceRef] = frozenset()
    lagged_reads: frozenset[SliceRef] = frozenset()
    writes: SliceRef = SliceRef.BIOTA

    def tick(self, ctx: TickContext) -> TickResult:
        self.calls.append("compute:reporter")
        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={"biomass": 1.0},
            )
        )


def _snapshot() -> WorldStateSnapshot:
    return WorldStateSnapshot(planet_id="p", seed=3, tick=0, era=0)


def test_sink_is_only_touched_after_the_tick_is_composed() -> None:
    sink = _SpySink()
    planet = PlanetEngine(EngineRegistry.of([_Reporter(sink.calls), NoOpEngine()]), sink=sink)

    planet.tick(_snapshot())

    computes = [i for i, call in enumerate(sink.calls) if call.startswith("compute:")]
    observations = [
        i for i, call in enumerate(sink.calls) if call.startswith(("metrics:", "event:"))
    ]
    assert computes and observations
    assert max(computes) < min(observations), (
        "toda observação tem de vir depois de todo cálculo: o contrário abriria "
        "caminho para a simulação enxergar a própria telemetria"
    )


def test_the_tick_result_does_not_depend_on_the_sink() -> None:
    registry = EngineRegistry.of([NoOpEngine()])
    with_sink = PlanetEngine(registry, sink=InMemoryEventStore()).tick(_snapshot())
    without_sink = PlanetEngine(registry, sink=NullSink()).tick(_snapshot())

    assert with_sink.snapshot == without_sink.snapshot
    assert [e.event_id for e in with_sink.events] == [e.event_id for e in without_sink.events]


def test_exceeding_the_budget_emits_a_diagnostic_without_changing_the_tick() -> None:
    """Pular um Engine lento faria o resultado depender da carga da máquina."""
    registry = EngineRegistry.of([NoOpEngine()])
    generous = PlanetEngine(registry, budget=TickBudget()).tick(_snapshot())
    impossible = PlanetEngine(registry, budget=TickBudget(max_duration_s=-1.0)).tick(_snapshot())

    assert impossible.snapshot == generous.snapshot

    diagnostics = [e for e in impossible.events if e.is_diagnostic]
    assert len(diagnostics) == 1
    assert diagnostics[0].cause_code is CoreCauseCode.BUDGET_EXCEEDED
    assert diagnostics[0].cause_detail["limit"] == "duration_s"
    assert not [e for e in generous.events if e.is_diagnostic]


def test_invariant_breach_becomes_a_diagnostic_event() -> None:
    @dataclass(slots=True)
    class _Drainer:
        engine_id: str = "drainer"
        reads: frozenset[SliceRef] = frozenset()
        lagged_reads: frozenset[SliceRef] = frozenset()
        writes: SliceRef = SliceRef.BIOTA

        def tick(self, ctx: TickContext) -> TickResult:
            return TickResult(
                delta=StateDelta(
                    engine_id=self.engine_id,
                    tick=ctx.tick,
                    writes=self.writes,
                    values={"biomass": -10.0},
                )
            )

    planet = PlanetEngine(
        EngineRegistry.of([_Drainer()]),
        invariants=[NonNegativeStocks({SliceRef.BIOTA: ("biomass",)})],
    )

    outcome = planet.tick(_snapshot())

    assert outcome.snapshot.biota.biomass == 0.0
    diagnostics = [e for e in outcome.events if e.is_diagnostic]
    assert diagnostics[0].cause_code is CoreCauseCode.INVARIANT_BREACH
    assert diagnostics[0].cause_detail["field"] == "biomass"


def test_wall_clock_never_reaches_the_world_state() -> None:
    """Dois relógios diferentes, o mesmo snapshot: o tempo é medida lateral."""
    registry = EngineRegistry.of([NoOpEngine()])
    ticks = iter([0.0, 100.0])
    slow = PlanetEngine(registry, clock=lambda: next(ticks)).tick(_snapshot())
    fast = PlanetEngine(registry, clock=lambda: 0.0).tick(_snapshot())

    assert slow.snapshot == fast.snapshot
    assert slow.samples[0].duration_s == 100.0
    assert fast.samples[0].duration_s == 0.0


def test_event_store_projects_scientific_and_technical_views() -> None:
    store = InMemoryEventStore()
    planet = PlanetEngine(
        EngineRegistry.of([NoOpEngine()]),
        budget=TickBudget(max_duration_s=-1.0),
        sink=store,
    )

    outcome = planet.tick(_snapshot())

    assert [e.event_type for e in store.scientific_view()] == ["EngineHeartbeat"]
    assert len(store.technical_view()) == 1
    assert len(store.by_correlation(outcome.events[0].correlation_id)) == 2


def test_replay_mode_does_not_republish_events() -> None:
    """Reconstruir uma era é reproduzir, não reocorrer: a trilha não duplica."""
    store = InMemoryEventStore()
    planet = PlanetEngine(EngineRegistry.of([NoOpEngine()]), sink=store)

    planet.tick(_snapshot())
    planet.tick(_snapshot(), publish=False)

    assert len(store.events) == 1
