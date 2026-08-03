"""O Diretor é determinístico: mesma semente, mesmos eventos, mesmos ticks (RF-023).

Sem isto o replay bit-a-bit não existe — reconstruir uma era exige que o sorteio
do Diretor caia igual, e um sorteio que dependesse de relógio, hash de processo
ou ordem de dicionário quebraria a reconstrução sem quebrar nenhum outro teste.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TICKS = 400


def _run(seed: int) -> tuple[list[tuple[str, int]], list[WorldStateSnapshot]]:
    store = InMemoryEventStore()
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("determinism", seed), PARAMS))
    trail = [snapshot]
    for _ in range(TICKS):
        snapshot = planet.tick(snapshot).snapshot
        trail.append(snapshot)
    fired = [(e.event_type, e.occurred_at.tick) for e in store.events if e.engine_id == "event"]
    return fired, trail


def test_the_same_seed_fires_the_same_events_at_the_same_ticks() -> None:
    first, _ = _run(2027)
    second, _ = _run(2027)
    assert first, "nenhum evento foi sorteado — o teste não afirmaria nada"
    assert first == second


def test_the_perturbation_trajectory_is_identical_under_the_same_seed() -> None:
    """Não só QUAIS eventos: a perturbação escalar tick a tick também."""
    _, one = _run(2027)
    _, two = _run(2027)
    assert [s.event.dust_load for s in one] == [s.event.dust_load for s in two]
    assert [s.event.cooling_forcing for s in one] == [s.event.cooling_forcing for s in two]
    assert [s.event.active_kind for s in one] == [s.event.active_kind for s in two]


def test_different_seeds_diverge() -> None:
    """Contraprova: sem ela, um Diretor que nunca sorteasse nada passaria acima."""
    one, _ = _run(11)
    two, _ = _run(12)
    assert one != two, "duas sementes produziram exatamente a mesma história"


def test_the_event_ids_are_deterministic_too() -> None:
    """Os `event_id` entram na cadeia causal: variar quebraria a proveniência."""
    store_a, store_b = InMemoryEventStore(), InMemoryEventStore()
    for store in (store_a, store_b):
        planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=store)
        snapshot = snapshot_of(initial_state(PlanetSeed("ids", 5), PARAMS))
        for _ in range(200):
            snapshot = planet.tick(snapshot).snapshot
    assert [e.event_id for e in store_a.events] == [e.event_id for e in store_b.events]
