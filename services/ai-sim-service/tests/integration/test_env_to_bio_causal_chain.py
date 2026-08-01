"""A cadeia AMBIENTE → BIOLOGIA se fecha por `causation_id`, elo a elo.

O M2 fixou o padrão: um teste de cadeia causal precisa **andar** a cadeia, e não
observar que dois eventos aconteceram no mesmo tick. Coocorrência é correlação
temporal — a cadeia se provaria igualmente "verdadeira" num motor em que os
Engines não se conhecessem nem por metadado.

Aqui a cadeia atravessa a fronteira nova do M3: o ambiente físico produz um
evento, e esse `event_id` reaparece como `causation_id` de um evento BIOLÓGICO,
emitido por um Engine que não conhece o emissor do primeiro.
"""

from __future__ import annotations

import pytest
from tests.support import build_volcanic_planet
from tests.support import test_params as production_params

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state
from ecosfera_ai.simulation_engine.state import PlanetSeed

BIOLOGICAL = {
    "LifeEmerged",
    "SpeciesExtinct",
    "SpeciationOccurred",
    "TraitShift",
    "TrophicCollapse",
    "PopulationDeclined",
}


def _run(ticks: int = 320) -> list[DomainEvent]:
    params = production_params()
    store = InMemoryEventStore()
    planet = build_volcanic_planet(sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("chain", 2027), params))
    for _ in range(ticks):
        snapshot = planet.tick(snapshot).snapshot
    return list(store.events)


@pytest.fixture(scope="module")
def events() -> list[DomainEvent]:
    return _run()


def _by_id(events: list[DomainEvent]) -> dict[str, DomainEvent]:
    return {event.event_id: event for event in events}


def _walk_up(event: DomainEvent, index: dict[str, DomainEvent]) -> list[DomainEvent]:
    """Sobe a cadeia pelo `causation_id` até a raiz, sem entrar em ciclo."""
    chain = [event]
    seen = {event.event_id}
    current = event
    while current.causation_id and current.causation_id in index:
        parent = index[current.causation_id]
        if parent.event_id in seen:
            break
        chain.append(parent)
        seen.add(parent.event_id)
        current = parent
    return chain


def test_the_scenario_produces_both_physics_and_biology(events: list[DomainEvent]) -> None:
    """Sem os dois lados, os testes seguintes seriam vacuamente verdes."""
    kinds = {event.event_type for event in events}
    assert kinds & BIOLOGICAL, f"nenhum evento biológico foi emitido: {sorted(kinds)}"
    assert kinds - BIOLOGICAL, "nenhum evento físico foi emitido"


def test_life_emerged_points_back_at_the_environment_that_allowed_it(
    events: list[DomainEvent],
) -> None:
    """O marco do surgimento é EFEITO de um evento do ambiente, e o diz.

    O `causation_id` do `LifeEmerged` é o evento que produziu a capacidade de
    suporte corrente — que veio do Resource, que por sua vez foi causado pela
    química/hidrologia. A Evolution nunca leu o Canal B de ninguém: a
    proveniência viajou como metadado do delta (Spec §3).
    """
    index = _by_id(events)
    emerged = [e for e in events if e.event_type == "LifeEmerged"]
    assert emerged, "a vida nunca surgiu no cenário vulcânico"

    first = emerged[0]
    assert first.causation_id, "o surgimento não aponta para causa alguma"
    assert first.causation_id in index, "o causation_id não corresponde a evento emitido"

    parent = index[first.causation_id]
    assert parent.event_type not in BIOLOGICAL, (
        f"a vida foi causada por outro evento biológico ({parent.event_type}); "
        "o elo ambiente→biologia não existe"
    )
    assert parent.occurred_at.tick <= first.occurred_at.tick


def test_a_biological_event_walks_all_the_way_up_to_physics(events: list[DomainEvent]) -> None:
    """O passeio COMPLETO: de um evento biológico até uma raiz física.

    Este é o teste que a condição do M2 exigiu — andar a cadeia, e não observar
    coocorrência. Se um elo fosse cortado, o passeio pararia no próprio evento
    biológico e o comprimento cairia para 1.
    """
    index = _by_id(events)
    biological = [e for e in events if e.event_type in BIOLOGICAL and e.causation_id]
    assert biological, "nenhum evento biológico declarou causa"

    walks = [_walk_up(event, index) for event in biological]
    longest = max(walks, key=len)

    assert len(longest) >= 2, (
        "nenhum evento biológico alcançou um ancestral: a cadeia está cortada "
        f"({[e.event_type for e in longest]})"
    )
    root = longest[-1]
    assert root.event_type not in BIOLOGICAL, (
        f"a cadeia mais longa começa e termina na biologia: {[e.event_type for e in longest]}"
    )

    # Os elos são de Engines DIFERENTES: é isso que torna a cadeia uma
    # propriedade da composição, e não de um módulo que sabe tudo.
    engines = {e.engine_id for e in longest}
    assert len(engines) >= 2, f"a cadeia inteira veio de um Engine só: {engines}"


def test_causation_never_points_forward_in_time(events: list[DomainEvent]) -> None:
    """Um efeito não precede a causa — nem por um tick."""
    index = _by_id(events)
    for event in events:
        if event.causation_id and event.causation_id in index:
            assert index[event.causation_id].occurred_at.tick <= event.occurred_at.tick, (
                f"{event.event_type} no tick {event.occurred_at.tick} aponta para uma causa futura"
            )


def test_every_declared_cause_actually_exists(events: list[DomainEvent]) -> None:
    """Nenhum `causation_id` órfão: apontar para o nada é pior que não apontar."""
    index = _by_id(events)
    dangling = [
        (e.event_type, e.causation_id)
        for e in events
        if e.causation_id and e.causation_id not in index
    ]
    assert not dangling, f"causation_id sem evento correspondente: {dangling[:5]}"


def test_the_chain_is_reproducible(events: list[DomainEvent]) -> None:
    """Mesmo cenário, mesma cadeia — a proveniência é determinística."""
    again = _run()
    assert [(e.event_type, e.occurred_at.tick, e.causation_id) for e in again] == [
        (e.event_type, e.occurred_at.tick, e.causation_id) for e in events
    ]
