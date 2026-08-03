"""A cadeia METEORO → EXTINÇÃO é DERIVADA do Event Store, elo a elo.

O padrão fixado no M2 e reafirmado aqui: um teste de cadeia causal precisa
**andar** a cadeia pelo `causation_id`, e não observar que dois eventos caíram no
mesmo tick. Coocorrência é correlação temporal — provaria a mesma coisa num motor
em que os Engines não se conhecessem nem por metadado.

E a relação é DERIVADA, não profetizada: o `MeteorImpact` não declara
`consequences=["extinction"]` na emissão, porque pode não haver extinção alguma.
Quem liga causa a efeito é a projeção sobre o Event Store, depois do fato
(ADR-ARCH-0002).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed
from tests.support import build_scripted_planet

PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _run(ticks: int = 400) -> list[DomainEvent]:
    """Meteoros declarados num planeta que já tem vida instalada."""
    store = InMemoryEventStore()
    # Meteoro LETAL declarado: o catálogo de produção fere sem aniquilar, e a
    # cadeia sob teste termina em extinção.
    # Mortalidade DECLARADA acima de 1: a severidade é sorteada em [0,6; 1,0],
    # então `mortality=1.0` remove ~80% e a comunidade sobrevive acima do piso —
    # `MassMortality`, não extinção. Acima de 1 o produto satura no recorte
    # (`min(1.0, ...)`) e o aniquilamento é total em toda semente, que é o que
    # torna a cadeia até `SpeciesExtinct` um cenário e não um sorteio.
    planet = build_scripted_planet(EventKind.METEOR, lead=4, mortality=2.0, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("meteor", 2027), PARAMS))
    for _ in range(ticks):
        snapshot = planet.tick(snapshot).snapshot
    return list(store.events)


@pytest.fixture(scope="module")
def events() -> list[DomainEvent]:
    return _run()


def _index(events: list[DomainEvent]) -> dict[str, DomainEvent]:
    return {e.event_id: e for e in events}


def _walk_up(event: DomainEvent, index: dict[str, DomainEvent]) -> list[DomainEvent]:
    chain, seen, current = [event], {event.event_id}, event
    while current.causation_id and current.causation_id in index:
        parent = index[current.causation_id]
        if parent.event_id in seen:
            break
        chain.append(parent)
        seen.add(parent.event_id)
        current = parent
    return chain


def test_the_scenario_produces_impacts_and_extinctions(events: list[DomainEvent]) -> None:
    """Sem os dois lados, o resto seria vacuamente verde."""
    kinds = {e.event_type for e in events}
    assert "MeteorImpact" in kinds, "nenhum meteoro caiu"
    assert "SpeciesExtinct" in kinds, "nenhuma extinção ocorreu"


def test_a_catastrophic_extinction_walks_up_to_the_meteor(events: list[DomainEvent]) -> None:
    """O passeio COMPLETO: da extinção até o impacto que a causou."""
    index = _index(events)
    catastrophic = [
        e
        for e in events
        if e.event_type == "SpeciesExtinct" and str(e.cause_code) == "CATASTROPHIC_EVENT"
    ]
    assert catastrophic, "nenhuma extinção catastrófica foi registrada"

    walks = [_walk_up(e, index) for e in catastrophic]
    reaching = [w for w in walks if any(x.event_type == "MeteorImpact" for x in w)]
    assert reaching, (
        "nenhuma extinção catastrófica alcançou o meteoro pelo causation_id: "
        f"cadeias vistas = {[[x.event_type for x in w] for w in walks[:3]]}"
    )

    chain = reaching[0]
    assert len(chain) >= 2, "a cadeia tem um elo só — está cortada"
    assert {x.engine_id for x in chain} >= {"evolution", "event"}, (
        "a cadeia não atravessa Engines diferentes"
    )


def test_the_link_is_not_mere_cooccurrence(events: list[DomainEvent]) -> None:
    """A prova de que não é coincidência temporal.

    Muitos eventos caem no mesmo tick. O que este teste exige é o PONTEIRO: a
    extinção nomeia o impacto pelo `event_id` dele. Um motor sem proveniência
    teria a mesma coocorrência e nenhum ponteiro.
    """
    index = _index(events)
    extinctions = [e for e in events if e.event_type == "SpeciesExtinct" and e.causation_id]
    assert extinctions

    linked = [e for e in extinctions if e.causation_id in index]
    assert linked, "as extinções apontam para ids que não existem na trilha"

    for extinction in linked:
        parent = index[extinction.causation_id]  # type: ignore[index]
        assert parent.event_id == extinction.causation_id
        assert parent.occurred_at.tick <= extinction.occurred_at.tick


def test_the_meteor_does_not_declare_the_extinction_it_may_not_cause(
    events: list[DomainEvent],
) -> None:
    """`consequences` é PROJETADO, nunca declarado na emissão.

    Anunciar "extinction" no impacto seria profetizar: o meteoro pode cair num
    planeta sem vida, ou não matar ninguém.
    """
    for impact in [e for e in events if e.event_type == "MeteorImpact"]:
        assert impact.consequences == (), (
            "o meteoro declarou consequências que ainda não aconteceram"
        )


def test_the_physical_arm_of_the_chain_also_closes(events: list[DomainEvent]) -> None:
    """O meteoro tem DOIS braços: poeira→clima e mortalidade→biologia.

    Este é o físico. Sem ele, o aluno veria a extinção mas não o inverno de
    impacto que a acompanha.
    """
    index = _index(events)
    climate = [e for e in events if e.engine_id == "climate" and e.causation_id in index]
    assert climate, "o clima não registrou nada encadeado"

    trails = [_walk_up(e, index) for e in climate]
    assert any(len(t) >= 2 for t in trails), "o braço físico da cadeia está cortado"


def test_causation_never_points_forward(events: list[DomainEvent]) -> None:
    index = _index(events)
    for event in events:
        if event.causation_id and event.causation_id in index:
            assert index[event.causation_id].occurred_at.tick <= event.occurred_at.tick


def test_the_chain_is_reproducible(events: list[DomainEvent]) -> None:
    again = _run()
    assert [(e.event_type, e.occurred_at.tick, e.causation_id) for e in again] == [
        (e.event_type, e.occurred_at.tick, e.causation_id) for e in events
    ]
