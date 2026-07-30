"""Planet Engine — o orquestrador do tick (Spec §5.3, ADR-ARCH-0001 Emenda 3).

É o antigo `TickOrchestrator` promovido: mesma responsabilidade, contrato novo.
Não contém regra científica alguma — se um dia contiver, é sinal de que uma
regra ficou sem Engine dono.

Cinco fases por tick:

1. publica o snapshot read-only ao Engine da vez;
2. o Engine calcula delta (Canal A) e eventos (Canal B) lendo só o que declarou;
3. o Planet compõe o delta aplicando as invariantes e **republica** o snapshot
   ao Engine seguinte (a ordem de acoplamento é o que dá sentido à §5.3);
4. fecha o tick avançando o contador;
5. **só então** aciona o `ObservabilitySink`.

A fase 5 vir por último não é estilo: é a invariante do ADR-ARCH-0002. Enquanto
o cálculo acontece, nada é medido nem registrado de forma que possa voltar para
dentro dele. O orçamento por tick também obedece a isso — estourar o teto emite
um `DiagnosticEvent` e não altera um bit do resultado.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.shared_kernel.engine import (
    Engine,
    PerfSample,
    TickBudget,
    TickContext,
    TickResult,
)
from ecosfera_ai.shared_kernel.events import (
    CoreCauseCode,
    DomainEvent,
    EventEmitter,
    diagnostic_event,
)
from ecosfera_ai.shared_kernel.observability import NullSink, ObservabilitySink, span
from ecosfera_ai.shared_kernel.replay import StepOutcome
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    Invariant,
    InvariantBreach,
    WorldStateSnapshot,
    compose,
)

PLANET_ENGINE_ID = "planet"


class EngineContractError(Exception):
    """Um Engine devolveu um delta fora do que declarou escrever."""


@dataclass(frozen=True, slots=True)
class PlanetTickOutcome:
    """Resultado de um tick completo do planeta."""

    snapshot: WorldStateSnapshot
    events: tuple[DomainEvent, ...] = ()
    samples: tuple[PerfSample, ...] = ()
    breaches: tuple[InvariantBreach, ...] = ()


@dataclass(frozen=True, slots=True)
class EraOutcome:
    """Resultado de uma era: checkpoint final e o log append-only do percurso.

    O `checkpoint` fecha a era `era` e carrega esse mesmo número no cabeçalho.
    Promover o estado à era seguinte é decisão da linha do tempo (borda
    assíncrona), não do loop — e é o que mantém o replay comparável campo a
    campo com o que foi gravado.
    """

    era: int
    checkpoint: WorldStateSnapshot
    events: tuple[DomainEvent, ...] = ()
    samples: tuple[PerfSample, ...] = ()


class PlanetEngine:
    """Orquestra os Engines registrados em ordem determinística."""

    engine_id = PLANET_ENGINE_ID

    def __init__(
        self,
        registry: EngineRegistry,
        *,
        invariants: Sequence[Invariant] = (),
        budget: TickBudget | None = None,
        sink: ObservabilitySink | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._registry = registry
        self._invariants = tuple(invariants)
        self._budget = budget or TickBudget()
        self._sink: ObservabilitySink = sink or NullSink()
        # Relógio injetável: o tempo é medida LATERAL, então precisa ser
        # substituível em teste sem que isso toque no cálculo.
        self._clock = clock

    @property
    def registry(self) -> EngineRegistry:
        return self._registry

    @property
    def engine_ids(self) -> tuple[str, ...]:
        return self._registry.engine_ids

    def tick(self, snapshot: WorldStateSnapshot, *, publish: bool = True) -> PlanetTickOutcome:
        """Executa um tick e devolve o snapshot fechado.

        `publish=False` roda o mesmo cálculo sem tocar a observabilidade — é o
        modo do replay: reconstruir uma era é reproduzir, não reocorrer, e
        reemitir duplicaria a trilha do Event Store.
        """
        working = snapshot
        events: list[DomainEvent] = []
        samples: list[PerfSample] = []
        breaches: list[InvariantBreach] = []

        for engine in self._registry.engines:
            context = TickContext(
                snapshot=working,
                rng=rng_for(snapshot.seed, engine.engine_id, snapshot.tick),
                tick=snapshot.tick,
                era=snapshot.era,
                budget=self._budget,
            )
            with span("engine.tick", engine=engine.engine_id, tick=snapshot.tick):
                started = self._clock()
                result = engine.tick(context)
                duration = self._clock() - started

            self._assert_contract(engine, result, snapshot)
            composition = compose(working, [result.delta], self._invariants)
            working = composition.snapshot
            breaches.extend(composition.breaches)
            events.extend(result.events)
            samples.append(
                PerfSample(
                    engine_id=engine.engine_id,
                    tick=snapshot.tick,
                    era=snapshot.era,
                    duration_s=duration,
                    events_emitted=len(result.events),
                    entities_processed=result.entities_processed,
                )
            )

        closed = working.advanced()

        # Canal B lateral. Construído DEPOIS de `closed`: nada aqui pode
        # influenciar o snapshot que acabou de ser fechado.
        diagnostics = self._diagnose(snapshot, tuple(samples), tuple(breaches))
        all_events = tuple(events) + diagnostics
        if publish:
            self._publish(all_events, tuple(samples))

        return PlanetTickOutcome(closed, all_events, tuple(samples), tuple(breaches))

    def run_era(
        self, snapshot: WorldStateSnapshot, ticks: int, *, publish: bool = True
    ) -> EraOutcome:
        """Roda uma era inteira e devolve o checkpoint append-only + eventos.

        Gravar o checkpoint é da borda assíncrona (persistência); aqui ele só é
        PRODUZIDO, porque o loop determinístico não faz I/O.
        """
        current = snapshot
        events: list[DomainEvent] = []
        samples: list[PerfSample] = []
        for _ in range(ticks):
            outcome = self.tick(current, publish=publish)
            current = outcome.snapshot
            events.extend(outcome.events)
            samples.extend(outcome.samples)
        return EraOutcome(snapshot.era, current, tuple(events), tuple(samples))

    @staticmethod
    def open_next_era(checkpoint: WorldStateSnapshot) -> WorldStateSnapshot:
        """Promove um checkpoint fechado ao início da era seguinte."""
        return replace(checkpoint, era=checkpoint.era + 1)

    def stepper(self) -> Callable[[WorldStateSnapshot], StepOutcome]:
        """Função pura de avanço, no formato que `shared_kernel.replay` consome."""

        def step(snapshot: WorldStateSnapshot) -> StepOutcome:
            outcome = self.tick(snapshot, publish=False)
            return StepOutcome(outcome.snapshot, outcome.events)

        return step

    def _assert_contract(
        self, engine: Engine, result: TickResult, snapshot: WorldStateSnapshot
    ) -> None:
        """Confere que o Engine escreveu exatamente a fatia que declarou."""
        delta = result.delta
        if delta.writes is not engine.writes:
            raise EngineContractError(
                f"{engine.engine_id!r} declara escrever {engine.writes} mas "
                f"devolveu um delta de {delta.writes}"
            )
        if delta.engine_id != engine.engine_id:
            raise EngineContractError(
                f"delta assinado por {delta.engine_id!r} veio de {engine.engine_id!r}"
            )
        if delta.tick != snapshot.tick:
            raise EngineContractError(
                f"{engine.engine_id!r} devolveu delta do tick {delta.tick}, "
                f"esperado {snapshot.tick}"
            )

    def _diagnose(
        self,
        snapshot: WorldStateSnapshot,
        samples: Sequence[PerfSample],
        breaches: Sequence[InvariantBreach],
    ) -> tuple[DomainEvent, ...]:
        """Traduz orçamento estourado e invariante recortada em eventos §4."""
        emitter = EventEmitter(
            engine_id=PLANET_ENGINE_ID,
            seed=snapshot.seed,
            tick=snapshot.tick,
            era=snapshot.era,
        )
        diagnostics: list[DomainEvent] = []
        for sample in samples:
            for limit in sample.exceeded(self._budget):
                diagnostics.append(
                    diagnostic_event(
                        emitter,
                        CoreCauseCode.BUDGET_EXCEEDED,
                        {
                            "engine": sample.engine_id,
                            "limit": limit,
                            "duration_s": sample.duration_s,
                            "events_emitted": sample.events_emitted,
                            "entities_processed": sample.entities_processed,
                        },
                    )
                )
        for breach in breaches:
            diagnostics.append(
                diagnostic_event(
                    emitter,
                    CoreCauseCode.INVARIANT_BREACH,
                    {
                        "invariant": breach.invariant,
                        "slice": str(breach.slice_ref),
                        "field": breach.field,
                        "value": breach.value,
                        "limit": breach.limit,
                    },
                )
            )
        return tuple(diagnostics)

    def _publish(self, events: Sequence[DomainEvent], samples: Sequence[PerfSample]) -> None:
        """Único ponto de contato com a observabilidade — sempre pós-cálculo."""
        for sample in samples:
            self._sink.record_metrics(sample)
        for event in events:
            self._sink.emit(event)
