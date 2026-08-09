"""O determinismo por semente e o replay bit-a-bit sobreviveram à Fase 0.

Mudar o envelope de um evento é a maneira mais barata de quebrar o replay sem
que nada estoure: basta um identificador sorteado dentro do `cause_detail` e a
mesma semente passa a produzir trilhas diferentes — a simulação continua
"funcionando" e o passado deixa de ser reconstruível (Spec §7, RF-023).

A Fase 0 acrescentou TRÊS identidades por especiação (um ancestral e duas
linhagens). Elas saem de `uuid5` sobre (semente, era, tick, papel), como os
`event_id`. Este arquivo é onde essa afirmação é verificada em vez de confiada.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from tests.support import (
    build_quiet_planet,
    community_genome,
    speciation_event,
    speciation_snapshot,
)
from tests.support import test_params as _production_params

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.evolution.events import lineages_for
from ecosfera_ai.shared_kernel.events import (
    EVENT_NAMESPACE,
    event_from_dict,
    event_to_dict,
)
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TICKS = 200


def _run(seed: int = 2027) -> tuple[list[object], list[dict[str, object]]]:
    """Trajetória e trilha COMPLETA — envelope a envelope, não só os ids."""
    store = InMemoryEventStore()
    from ecosfera_ai.engines.composition import build_planet_engine

    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("fase0", seed), PARAMS))
    trail: list[object] = [snapshot]
    for _ in range(TICKS):
        snapshot = planet.tick(snapshot).snapshot
        trail.append(snapshot)
    return trail, [event_to_dict(e) for e in store.events]


# --- A trajetória e a trilha continuam bit-a-bit ------------------------------


def test_the_trajectory_is_still_bit_identical_under_the_same_seed() -> None:
    one, _ = _run()
    two, _ = _run()
    for a, b in zip(one, two, strict=True):
        assert a == b


def test_the_whole_envelope_replays_field_by_field() -> None:
    """Não basta o `event_id`: os campos novos entram na comparação.

    Um id determinístico com um `cause_detail` sorteado passaria num teste que
    só olha ids — e é justamente `cause_detail` que a Fase 0 mexeu.
    """
    _, one = _run()
    _, two = _run()
    assert one == two


def test_a_different_seed_still_produces_a_different_trail() -> None:
    """Contraprova: sem ela, um motor congelado passaria nos testes acima."""
    _, one = _run(seed=2027)
    _, two = _run(seed=99)
    assert one != two


def test_the_physical_baseline_did_not_move() -> None:
    """A Fase 0 mexeu em EVENTO, não em física — o planeta é o mesmo.

    O envelope é Canal B: alterá-lo não pode tocar o world-state. Se a
    trajetória tivesse mudado, a mudança teria vazado do canal de observação
    para o canal determinístico, que é a inversão que o ADR-ARCH-0002 proíbe.
    """
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("baseline", 2027), _production_params()))
    for _ in range(120):
        snapshot = planet.tick(snapshot, publish=False).snapshot
    assert snapshot.biota.biomass > 0.0
    assert snapshot.tick == 120


# --- As identidades novas são derivadas, não sorteadas ------------------------


def test_the_lineage_identities_are_uuid5_over_the_simulation_coordinates() -> None:
    """Derivadas de (semente, era, tick, papel) — reconstruíveis, não sorteadas."""
    lineages = lineages_for(2027, 3, 42)
    for role, value in (
        ("ancestor", lineages.ancestor),
        ("lineage_a", lineages.first),
        ("lineage_b", lineages.second),
    ):
        expected = uuid.uuid5(EVENT_NAMESPACE, f"lineage|2027|3|42|{role}")
        assert value == str(expected), f"a identidade de {role} não é derivada"


def test_the_same_speciation_yields_the_same_identities_twice() -> None:
    world = speciation_snapshot(community_genome(temp_optimum=26.0))
    first = speciation_event(world).cause_detail
    second = speciation_event(world).cause_detail
    assert dict(first) == dict(second)


# --- O envelope novo sobrevive à ida e volta do Event Store -------------------


def test_the_new_envelope_survives_serialization() -> None:
    """O Event Store guarda o envelope inteiro, ou a trilha vira resumo."""
    event = speciation_event()
    restored = event_from_dict(event_to_dict(event))
    assert restored == event
    assert dict(restored.cause_detail) == dict(event.cause_detail)
    assert restored.participants == event.participants
