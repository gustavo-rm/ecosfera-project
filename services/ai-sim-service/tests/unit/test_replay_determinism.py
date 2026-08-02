"""Replay determinístico: reconstruir uma era reproduz o original (RF-016/023)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import build_orchestrator

from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState, StateDelta
from ecosfera_ai.simulation_engine.timeline import (
    EVENT_ICE_FREE,
    EVENT_INTERVENTION,
    EVENT_LIFE_EMERGED,
    EVENT_SNOWBALL,
    EraCheckpoint,
    EventLogEntry,
    apply_event,
    detect_milestones,
    intervention_delta,
    replay,
    summarize,
)

PARAMS = load_params(Path("configs/simulation_params.yaml"))
ORCHESTRATOR = build_orchestrator(PARAMS)


def _genesis(seed: int = 42, planet_id: str = "p") -> PlanetState:
    return initial_state(PlanetSeed(planet_id=planet_id, seed=seed), PARAMS)


def test_replay_reproduces_the_original_trajectory_exactly() -> None:
    base = _genesis()
    state = base
    for _ in range(25):
        state = ORCHESTRATOR.tick(state).state

    rebuilt = replay(base, [], state.tick, ORCHESTRATOR, PARAMS.bounds)
    # RF-023: sem gravar um estado por tick, o motor reconstrói bit a bit.
    assert rebuilt == state


def test_replay_from_a_mid_trajectory_checkpoint_matches() -> None:
    base = _genesis()
    mid = base
    for _ in range(10):
        mid = ORCHESTRATOR.tick(mid).state
    final = mid
    for _ in range(10):
        final = ORCHESTRATOR.tick(final).state

    assert replay(mid, [], final.tick, ORCHESTRATOR, PARAMS.bounds) == final


def test_different_seeds_diverge_on_replay() -> None:
    a = _genesis(seed=1)
    b = _genesis(seed=2)
    rebuilt_a = replay(a, [], 15, ORCHESTRATOR, PARAMS.bounds)
    rebuilt_b = replay(b, [], 15, ORCHESTRATOR, PARAMS.bounds)
    assert rebuilt_a.temperature != rebuilt_b.temperature


def test_intervention_events_are_reapplied_during_replay() -> None:
    base = _genesis()
    intervention = EventLogEntry(
        planet_id="p", tick=3, event_type=EVENT_INTERVENTION, payload={"co2": 500.0}
    )

    without = replay(base, [], 8, ORCHESTRATOR, PARAMS.bounds)
    with_event = replay(base, [intervention], 8, ORCHESTRATOR, PARAMS.bounds)

    # A intervenção do aluno é o que o motor NÃO deriva sozinho: precisa do log.
    assert with_event.co2 > without.co2
    # E a reconstrução continua determinística: repetir dá o mesmo resultado.
    assert replay(base, [intervention], 8, ORCHESTRATOR, PARAMS.bounds) == with_event


def test_milestone_events_do_not_change_the_replayed_state() -> None:
    base = _genesis()
    marker = EventLogEntry(
        planet_id="p", tick=2, event_type=EVENT_LIFE_EMERGED, payload={"biomass": 0.001}
    )
    assert replay(base, [marker], 6, ORCHESTRATOR, PARAMS.bounds) == replay(
        base, [], 6, ORCHESTRATOR, PARAMS.bounds
    )


def test_intervention_delta_ignores_unknown_variables() -> None:
    # Tolerância a versões: um log antigo com chave desconhecida ainda reconstrói.
    delta = intervention_delta({"co2": 10.0, "nao_existe": 99.0})
    assert delta.d_co2 == 10.0


def test_apply_event_respects_physical_bounds() -> None:
    base = _genesis()
    drain = EventLogEntry("p", 0, EVENT_INTERVENTION, {"co2": -10_000.0})
    assert apply_event(base, drain, PARAMS.bounds).co2 == 0.0


def test_replay_rejects_a_checkpoint_ahead_of_the_target() -> None:
    base = _genesis()
    ahead = ORCHESTRATOR.tick(base).state
    with pytest.raises(ValueError, match="mais adiantado"):
        replay(ahead, [], 0, ORCHESTRATOR, PARAMS.bounds)


def test_detect_milestones_flags_life_emergence() -> None:
    before = _genesis()
    after = before.apply(StateDelta(d_biomass=0.5), PARAMS.bounds).advanced()
    events = detect_milestones("p", before, after)
    assert [e.event_type for e in events] == [EVENT_LIFE_EMERGED]


def test_detect_milestones_flags_snowball_and_ice_free_transitions() -> None:
    from dataclasses import replace as dc_replace

    base = _genesis()
    partially_iced = dc_replace(base, ice_cover=0.5)

    frozen = dc_replace(base, ice_cover=1.0, tick=1)
    assert [e.event_type for e in detect_milestones("p", partially_iced, frozen)] == [
        EVENT_SNOWBALL
    ]

    thawed = dc_replace(base, ice_cover=0.0, tick=1)
    assert [e.event_type for e in detect_milestones("p", partially_iced, thawed)] == [
        EVENT_ICE_FREE
    ]


def test_summarize_counts_events_per_era() -> None:
    state = _genesis()
    checkpoints = [
        EraCheckpoint("p", era=0, seed=42, start_tick=0, end_tick=0, state=state),
        EraCheckpoint("p", era=1, seed=42, start_tick=0, end_tick=10, state=state),
    ]
    summary = summarize(checkpoints, {1: 3})
    assert [(s.era, s.event_count) for s in summary] == [(0, 0), (1, 3)]
