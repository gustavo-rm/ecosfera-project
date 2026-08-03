"""Replay bit-a-bit reproduz eventos, perturbações e estado (RF-023, Spec §7).

O M4 acrescenta duas coisas que o replay tem de reconstruir: as DECISÕES do
Diretor (quais eventos, em que ticks) e as PERTURBAÇÕES que elas geram. Ambas
dependem de o Diretor ser função pura de `(world-state, RNG semeado)` — se ele
lesse a trilha, o replay seria impossível, porque a trilha é efeito da execução.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.shared_kernel.world_state import EventSlice, WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TICKS = 300
EVENT_FIELDS = tuple(EventSlice.__dataclass_fields__)


def _run(seed: int = 2027, ticks: int = TICKS) -> tuple[list[WorldStateSnapshot], list[str]]:
    store = InMemoryEventStore()
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("replay-m4", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot).snapshot
        trail.append(snapshot)
    return trail, [e.event_id for e in store.events]


def test_the_whole_trajectory_is_bit_identical() -> None:
    one, _ = _run()
    two, _ = _run()
    for a, b in zip(one, two, strict=True):
        assert a == b, f"os snapshots divergiram no tick {a.tick}"


def test_the_event_slice_replays_field_by_field() -> None:
    """Não basta o estado final: cada perturbação, em cada tick."""
    one, _ = _run()
    two, _ = _run()
    for field in EVENT_FIELDS:
        assert [getattr(s.event, field) for s in one] == [getattr(s.event, field) for s in two], (
            f"o campo `{field}` da EventSlice não replaya"
        )


def test_the_event_ids_replay_too() -> None:
    """A cadeia causal depende dos ids: variar quebraria a proveniência gravada."""
    _, one = _run()
    _, two = _run()
    assert one == two


def test_the_scenario_actually_exercised_the_director() -> None:
    """Sem eventos, os testes acima replayariam um planeta sem M4 algum."""
    trail, ids = _run()
    assert any(s.event.active_kind for s in trail), "o Diretor não agendou nada"
    assert ids, "nenhum evento foi emitido"


def test_the_event_slice_survives_the_planet_state_round_trip() -> None:
    """A ponte não pode zerar a fatia — seria a dívida do M3 repetida.

    Sem casa no `PlanetState`, a `EventSlice` voltaria zerada a cada tick e um
    evento em curso desapareceria no meio dele, sem erro nenhum.
    """
    trail, _ = _run()
    active = next((s for s in trail if s.event.active_kind), None)
    assert active is not None, "nenhum evento ativo para testar"

    rebuilt = snapshot_of(planet_state_of(active))
    for field in EVENT_FIELDS:
        assert getattr(rebuilt.event, field) == getattr(active.event, field), (
            f"o campo `{field}` se perdeu no round-trip"
        )


def test_different_seeds_produce_different_replays() -> None:
    one, _ = _run(seed=11, ticks=200)
    two, _ = _run(seed=12, ticks=200)
    assert [s.event.active_kind for s in one] != [s.event.active_kind for s in two]
