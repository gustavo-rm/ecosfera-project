"""Determinismo e reprodutibilidade do orquestrador por semente (RF-023)."""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.simulation_engine.params import build_orchestrator, initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed, StateDelta

PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _first_tick_delta(seed: int) -> StateDelta:
    orchestrator = build_orchestrator(PARAMS)
    state = initial_state(PlanetSeed(planet_id="p", seed=seed), PARAMS)
    return orchestrator.tick(state).delta


def test_same_seed_yields_same_delta() -> None:
    # RF-023: mesma semente => exatamente o mesmo StateDelta (reprodutibilidade).
    assert _first_tick_delta(42) == _first_tick_delta(42)


def test_different_seeds_yield_different_deltas() -> None:
    # Sementes distintas divergem por causa do ruído meteorológico/vital.
    assert _first_tick_delta(42) != _first_tick_delta(7)


def test_trajectory_is_reproducible_across_ticks() -> None:
    # Reexecutar a trajetória do zero reproduz cada tick (base de replay, RF-016).
    orch_a = build_orchestrator(PARAMS)
    a0 = initial_state(PlanetSeed(planet_id="p", seed=99), PARAMS)
    a1 = orch_a.tick(a0)
    a2 = orch_a.tick(a1.state)

    orch_b = build_orchestrator(PARAMS)
    b0 = initial_state(PlanetSeed(planet_id="other", seed=99), PARAMS)
    b1 = orch_b.tick(b0)
    b2 = orch_b.tick(b1.state)

    assert a1.delta == b1.delta
    assert a2.delta == b2.delta
    assert a2.state.tick == 2
