"""Contrato de replay (Spec §7): reconstruir a era bit-a-bit a partir da semente."""

from __future__ import annotations

from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.engines.noop.service import NoOpEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.shared_kernel.replay import ReplayMismatchError, replay, verify_replay
from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
ERA_TICKS = 8


def _noop_planet() -> PlanetEngine:
    return PlanetEngine(EngineRegistry.of([NoOpEngine()]))


def _snapshot(seed: int = 2027) -> WorldStateSnapshot:
    return WorldStateSnapshot(planet_id="p", seed=seed, tick=0, era=0)


def test_replay_rebuilds_the_snapshot_bit_for_bit() -> None:
    planet = _noop_planet()
    checkpoint = _snapshot()
    era = planet.run_era(checkpoint, ticks=ERA_TICKS)

    rebuilt = replay(
        checkpoint.seed,
        checkpoint,
        era.events,
        stepper=planet.stepper(),
        until_tick=ERA_TICKS,
    )

    assert rebuilt == era.checkpoint, "igualdade estrutural = reconstrução bit-a-bit"


def test_replay_regenerates_the_same_event_sequence() -> None:
    """Segundo critério do §7: a MESMA sequência, não só o mesmo estado."""
    planet = _noop_planet()
    checkpoint = _snapshot()
    era = planet.run_era(checkpoint, ticks=ERA_TICKS)

    report = verify_replay(
        checkpoint.seed,
        checkpoint,
        era.events,
        stepper=planet.stepper(),
        until_tick=ERA_TICKS,
    )

    assert report.matches_events is True
    assert report.deterministic is True
    assert [e.event_id for e in report.events] == [e.event_id for e in era.events]


def test_replay_through_the_real_deterministic_core() -> None:
    """O núcleo científico de verdade, atravessando a moldura, reproduz a era."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    checkpoint = snapshot_of(initial_state(PlanetSeed("replay", 4242), PARAMS))

    era = planet.run_era(checkpoint, ticks=ERA_TICKS)
    report = verify_replay(
        checkpoint.seed,
        checkpoint,
        era.events,
        stepper=planet.stepper(),
        until_tick=ERA_TICKS,
        expected=era.checkpoint,
    )

    assert report.matches_snapshot is True, "divergência aqui é bug de determinismo"
    assert report.deterministic is True


def test_replay_of_a_foreign_seed_is_refused() -> None:
    planet = _noop_planet()
    with pytest.raises(ReplayMismatchError, match="não pode ser reproduzido"):
        replay(999, _snapshot(seed=1), (), stepper=planet.stepper(), until_tick=1)


def test_replay_before_the_checkpoint_is_refused() -> None:
    planet = _noop_planet()
    checkpoint = _snapshot()
    era = planet.run_era(checkpoint, ticks=ERA_TICKS)
    with pytest.raises(ReplayMismatchError, match="anterior ao checkpoint"):
        replay(
            checkpoint.seed,
            era.checkpoint,
            (),
            stepper=planet.stepper(),
            until_tick=1,
        )


def test_replay_detects_a_stepper_that_does_not_advance() -> None:
    """Sem essa guarda, um motor defeituoso travaria o replay em laço infinito."""
    from ecosfera_ai.shared_kernel.replay import StepOutcome

    with pytest.raises(ReplayMismatchError, match="não avançou o tick"):
        replay(
            1,
            _snapshot(seed=1),
            (),
            stepper=lambda snapshot: StepOutcome(snapshot),
            until_tick=5,
        )
