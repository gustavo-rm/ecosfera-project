"""Planet Engine: ordem determinística, validação de grafo e contrato de fatia."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ecosfera_ai.engines.noop.service import NoOpEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import EngineContractError, PlanetEngine
from ecosfera_ai.shared_kernel.engine import (
    EngineGraphError,
    TickContext,
    TickResult,
    validate_graph,
)
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta, WorldStateSnapshot


@dataclass(slots=True)
class _Recorder:
    """Engine mínimo que anota a ordem em que foi chamado e soma 1 à sua fatia."""

    engine_id: str
    writes: SliceRef
    field_name: str
    log: list[str]
    reads: frozenset[SliceRef] = frozenset()
    lagged_reads: frozenset[SliceRef] = frozenset()

    def tick(self, ctx: TickContext) -> TickResult:
        self.log.append(self.engine_id)
        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={self.field_name: 1.0},
            )
        )


def _snapshot() -> WorldStateSnapshot:
    return WorldStateSnapshot(planet_id="p", seed=11, tick=0, era=0)


def test_engines_run_in_the_registered_order() -> None:
    log: list[str] = []
    registry = EngineRegistry.of(
        [
            _Recorder("chemistry", SliceRef.CHEMISTRY, "ocean_carbon", log),
            _Recorder("climate", SliceRef.CLIMATE, "temperature", log),
            _Recorder("biota", SliceRef.BIOTA, "biomass", log),
        ]
    )

    outcome = PlanetEngine(registry).tick(_snapshot())

    assert log == ["chemistry", "climate", "biota"]
    assert registry.engine_ids == ("chemistry", "climate", "biota")
    assert outcome.snapshot.chemistry.ocean_carbon == 1.0
    assert outcome.snapshot.tick == 1


def test_each_engine_reads_the_effects_of_the_previous_one() -> None:
    """Composição sequencial: é o que dá sentido físico à ordem (ADR 0008)."""
    seen: list[float] = []

    @dataclass(slots=True)
    class _Reader:
        engine_id: str = "climate"
        reads: frozenset[SliceRef] = frozenset({SliceRef.CHEMISTRY})
        lagged_reads: frozenset[SliceRef] = frozenset()
        writes: SliceRef = SliceRef.CLIMATE

        def tick(self, ctx: TickContext) -> TickResult:
            seen.append(ctx.snapshot.chemistry.ocean_carbon)
            return TickResult(
                delta=StateDelta(engine_id=self.engine_id, tick=ctx.tick, writes=self.writes)
            )

    registry = EngineRegistry.of(
        [_Recorder("chemistry", SliceRef.CHEMISTRY, "ocean_carbon", []), _Reader()]
    )
    PlanetEngine(registry).tick(_snapshot())

    assert seen == [1.0], "o clima deveria ver o carbono que a química acabou de escrever"


def test_duplicate_engine_id_is_rejected_at_boot() -> None:
    with pytest.raises(EngineGraphError, match="engine_id duplicado"):
        validate_graph(
            [
                _Recorder("climate", SliceRef.CLIMATE, "temperature", []),
                _Recorder("climate", SliceRef.BIOTA, "biomass", []),
            ]
        )


def test_two_engines_writing_the_same_slice_is_rejected() -> None:
    with pytest.raises(EngineGraphError, match="dois donos"):
        EngineRegistry.of(
            [
                _Recorder("a", SliceRef.CLIMATE, "temperature", []),
                _Recorder("b", SliceRef.CLIMATE, "energy", []),
            ]
        )


def test_unresolved_cycle_is_detected() -> None:
    """Ler uma fatia escrita adiante no mesmo tick é ordem inconsistente."""
    early = _Recorder("climate", SliceRef.CLIMATE, "temperature", [])
    early.reads = frozenset({SliceRef.CHEMISTRY})
    late = _Recorder("chemistry", SliceRef.CHEMISTRY, "ocean_carbon", [])

    with pytest.raises(EngineGraphError, match="ciclo não resolvido"):
        EngineRegistry.of([early, late])


def test_declared_lag_resolves_the_cycle() -> None:
    """A defasagem de um tick é legítima — desde que declarada, não presumida."""
    early = _Recorder("climate", SliceRef.CLIMATE, "temperature", [])
    early.lagged_reads = frozenset({SliceRef.CHEMISTRY})
    late = _Recorder("chemistry", SliceRef.CHEMISTRY, "ocean_carbon", [])

    registry = EngineRegistry.of([early, late])

    assert registry.engine_ids == ("climate", "chemistry")


def test_engine_writing_outside_its_declared_slice_is_rejected() -> None:
    @dataclass(slots=True)
    class _Liar:
        engine_id: str = "liar"
        reads: frozenset[SliceRef] = frozenset()
        lagged_reads: frozenset[SliceRef] = frozenset()
        writes: SliceRef = SliceRef.CLIMATE

        def tick(self, ctx: TickContext) -> TickResult:
            return TickResult(
                delta=StateDelta(engine_id=self.engine_id, tick=ctx.tick, writes=SliceRef.BIOTA)
            )

    with pytest.raises(EngineContractError, match="declara escrever"):
        PlanetEngine(EngineRegistry.of([_Liar()])).tick(_snapshot())


@pytest.mark.parametrize(
    ("signed_by", "tick", "message"),
    [("outro", 0, "assinado por"), ("forger", 99, "devolveu delta do tick")],
)
def test_delta_provenance_is_checked(signed_by: str, tick: int, message: str) -> None:
    """Assinatura e tick errados quebram a rastreabilidade do Canal A."""

    @dataclass(slots=True)
    class _Forger:
        engine_id: str = "forger"
        reads: frozenset[SliceRef] = frozenset()
        lagged_reads: frozenset[SliceRef] = frozenset()
        writes: SliceRef = SliceRef.CLIMATE

        def tick(self, ctx: TickContext) -> TickResult:
            del ctx
            return TickResult(
                delta=StateDelta(engine_id=signed_by, tick=tick, writes=SliceRef.CLIMATE)
            )

    with pytest.raises(EngineContractError, match=message):
        PlanetEngine(EngineRegistry.of([_Forger()])).tick(_snapshot())


def test_noop_engine_proves_the_frame_orchestrates_both_channels() -> None:
    """Critério de conclusão do M0 (Spec §8), sem depender de física nenhuma."""
    planet = PlanetEngine(EngineRegistry.of([NoOpEngine()]))

    outcome = planet.tick(_snapshot())

    assert outcome.snapshot.tick == 1
    assert outcome.snapshot.resource == _snapshot().resource  # delta vazio
    assert [e.event_type for e in outcome.events] == ["EngineHeartbeat"]
    assert outcome.samples[0].engine_id == "noop"


def test_registry_publishes_slice_ownership() -> None:
    registry = EngineRegistry.of(
        [
            _Recorder("chemistry", SliceRef.CHEMISTRY, "ocean_carbon", []),
            _Recorder("climate", SliceRef.CLIMATE, "temperature", []),
        ]
    )
    assert registry.owned_slices == {
        SliceRef.CHEMISTRY: "chemistry",
        SliceRef.CLIMATE: "climate",
    }


def test_era_run_produces_a_checkpoint_and_the_event_log() -> None:
    planet = PlanetEngine(EngineRegistry.of([NoOpEngine()]))

    era = planet.run_era(_snapshot(), ticks=4)

    assert era.era == 0
    assert era.checkpoint.tick == 4
    assert era.checkpoint.era == 0, "o checkpoint FECHA a era, não abre a seguinte"
    assert PlanetEngine.open_next_era(era.checkpoint).era == 1
    assert len(era.events) == 4
    assert len(era.samples) == 4
