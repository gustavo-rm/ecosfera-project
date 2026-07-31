"""Replay bit-a-bit da fatia vertical do M1 (Spec §7, RF-023).

Reconstruir a era tem de reproduzir o snapshot E a sequência de eventos. Com três
Engines reais e RNG independente por Engine, é aqui que o determinismo da moldura
deixa de ser promessa e vira evidência.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ecosfera_ai.engines.legacy.bridge import snapshot_of
from ecosfera_ai.engines.legacy.orchestrator import build_planet_engine
from ecosfera_ai.shared_kernel.replay import verify_replay
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
ERA_TICKS = 30


def _planet():
    return build_planet_engine(PARAMS, budget=PARAMS.engine_budget)


@pytest.mark.parametrize("seed", [7, 2027, 31337])
def test_replay_reproduces_snapshot_and_events(seed: int) -> None:
    planet = _planet()
    checkpoint = snapshot_of(initial_state(PlanetSeed("replay-m1", seed), PARAMS))
    era = planet.run_era(checkpoint, ticks=ERA_TICKS)

    report = verify_replay(
        checkpoint.seed,
        checkpoint,
        era.events,
        stepper=planet.stepper(),
        until_tick=ERA_TICKS,
        expected=era.checkpoint,
    )

    assert report.matches_snapshot is True, "divergência de estado = bug de determinismo"
    assert report.matches_events is True, "divergência de eventos = bug de determinismo"
    assert report.deterministic is True


def test_the_causal_provenance_survives_the_replay() -> None:
    """A proveniência é parte do snapshot, então o replay tem de reproduzi-la."""
    planet = _planet()
    checkpoint = snapshot_of(initial_state(PlanetSeed("prov", 2027), PARAMS))
    era = planet.run_era(checkpoint, ticks=ERA_TICKS)

    rebuilt = verify_replay(
        checkpoint.seed,
        checkpoint,
        era.events,
        stepper=planet.stepper(),
        until_tick=ERA_TICKS,
    ).snapshot

    assert dict(rebuilt.provenance) == dict(era.checkpoint.provenance)
    assert rebuilt.provenance, "sem proveniência não haveria cadeia causal a reproduzir"


def test_two_independent_runs_agree_field_by_field() -> None:
    first = _planet().run_era(
        snapshot_of(initial_state(PlanetSeed("twin", 555), PARAMS)), ticks=ERA_TICKS
    )
    second = _planet().run_era(
        snapshot_of(initial_state(PlanetSeed("twin", 555), PARAMS)), ticks=ERA_TICKS
    )
    assert first.checkpoint == second.checkpoint
    assert [e.event_id for e in first.events] == [e.event_id for e in second.events]


def test_a_different_seed_produces_a_different_history() -> None:
    a = _planet().run_era(snapshot_of(initial_state(PlanetSeed("a", 1), PARAMS)), ticks=ERA_TICKS)
    b = _planet().run_era(snapshot_of(initial_state(PlanetSeed("a", 2), PARAMS)), ticks=ERA_TICKS)
    assert a.checkpoint != b.checkpoint
