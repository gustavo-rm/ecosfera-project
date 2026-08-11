"""A cadeia é RECONSTRUÍDA, elo a elo, nas duas direções — e a ÁRVORE é afirmada.

Esta é a lógica central do M6.0 e a que mais precisa de teste. O motivo é o
espelho exato de um defeito real do M4: uma extinção catastrófica encadeava ao
`TemperatureShift` que por acaso ocorreu no mesmo tick, e não ao meteoro que a
causou (ADR 0019, decisão 4). Do lado da escrita, o teste de cadeia o encontrou.
Do lado da LEITURA, o mesmo erro produz um Tutor que conta a história causal
errada — com toda a autoridade de estar "ancorado no Event Store".

Por isso o padrão fixado no M2 vale aqui inteiro: **andar** a cadeia pelo
`causation_id`, nunca observar coocorrência. Dois eventos no mesmo tick provariam
a mesma coisa num motor em que os Engines não se conhecessem nem por metadado.

E a ÁRVORE, não só o caminho: descer é ramificado (um meteoro causa resfriamento,
incêndio e extinção ao mesmo tempo), subir é linear. Uma travessia descendente que
devolvesse a lista invertida da subida entregaria um ramo só.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import build_scripted_planet
from tests.support_context import branching_cascade, cyclic_trail, spans_two_eras

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.application.platform.event_query import InMemoryEventQuery
from ecosfera_ai.domain.consumers.causal_tree import build_causal_forest, descendants_of
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.engines.event.events import METEOR_IMPACT
from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
PLANET = "planet-chain"

CASCADE = branching_cascade()
METEOR, COOLING, WILDFIRE, CATASTROPHIC, ECOLOGICAL = CASCADE


def _context(events: list[DomainEvent], era: int = 1) -> FactualContext:
    return FactualContext.of(PLANET, ContextSlice.of_era(era), tuple(events))


# --- Descendo: a árvore, e não um ramo ---------------------------------------


def test_the_meteor_is_the_single_root_of_the_cascade() -> None:
    forest = build_causal_forest(CASCADE)
    assert len(forest) == 1
    assert forest[0].event.event_id == METEOR.event_id


def test_the_root_branches_into_its_three_direct_effects() -> None:
    """Três filhos DIRETOS. Um só significaria travessia linear disfarçada."""
    root = build_causal_forest(CASCADE)[0]
    assert {child.event.event_id for child in root.consequences} == {
        COOLING.event_id,
        WILDFIRE.event_id,
        CATASTROPHIC.event_id,
    }


def test_the_indirect_effect_hangs_under_its_own_cause_and_not_under_the_root() -> None:
    """A extinção ecológica é filha do RESFRIAMENTO, não do meteoro.

    É o elo que separa "morreu porque um meteoro caiu" de "morreu porque
    esfriou". Achatar a árvore num nível só apagaria a diferença.
    """
    root = build_causal_forest(CASCADE)[0]
    cooling = next(c for c in root.consequences if c.event.event_id == COOLING.event_id)
    assert [child.event.event_id for child in cooling.consequences] == [ECOLOGICAL.event_id]
    assert root.depth == 3


def test_descendants_walk_the_causation_id_and_not_the_tick() -> None:
    """Coocorrência não é elo: o incêndio e o resfriamento partilham o tick.

    Se a reconstrução olhasse o tempo, os dois apareceriam ligados entre si. O
    que os liga é o meteoro, e só ele.
    """
    assert COOLING.occurred_at.tick == WILDFIRE.occurred_at.tick
    assert descendants_of(CASCADE, COOLING.event_id) == (ECOLOGICAL,)
    assert descendants_of(CASCADE, WILDFIRE.event_id) == ()


def test_the_full_descent_from_the_meteor_reaches_every_consequence() -> None:
    assert {e.event_id for e in descendants_of(CASCADE, METEOR.event_id)} == {
        COOLING.event_id,
        WILDFIRE.event_id,
        CATASTROPHIC.event_id,
        ECOLOGICAL.event_id,
    }


# --- Subindo: o caminho até a raiz -------------------------------------------


async def test_the_event_slice_ascends_to_the_meteor_and_descends_from_it() -> None:
    """As duas direções sobre o MESMO `causation_id`, numa única leitura."""
    assembler = ContextAssembler(InMemoryEventQuery.of(PLANET, CASCADE))
    context = await assembler.execute(PLANET, ContextSlice.of_event(ECOLOGICAL.event_id))

    assert [e.event_id for e in context.ancestry] == [
        ECOLOGICAL.event_id,
        COOLING.event_id,
        METEOR.event_id,
    ]
    assert context.consequences_of(METEOR.event_id)
    assert context.cause_of(ECOLOGICAL.event_id) is not None
    assert str(context.cause_of(ECOLOGICAL.event_id).event_id) == COOLING.event_id  # type: ignore[union-attr]


# --- Fronteiras da fatia e trilha corrompida ----------------------------------


def test_an_effect_whose_cause_left_the_slice_becomes_a_local_root() -> None:
    """A fatia por era corta o elo — e o evento continua no dossiê, como raiz."""
    trail = spans_two_eras()
    second_era = _context([trail[1]], era=2)
    assert len(second_era.causal_roots) == 1
    assert second_era.causal_roots[0].event.event_id == trail[1].event_id
    assert second_era.cause_of(trail[1].event_id) is None


def test_a_corrupted_cyclic_trail_neither_hangs_nor_loses_events() -> None:
    """Ciclo em `causation_id` não sai de corrida alguma — sai de import malfeito.

    Perder o evento seria pior que exibi-lo com a causa truncada: o dossiê
    ficaria íntegro na aparência.
    """
    trail = cyclic_trail()
    forest = build_causal_forest(trail)
    seen = [event.event_id for root in forest for event in root.walk()]
    assert sorted(seen) == sorted(e.event_id for e in trail)
    assert len(seen) == len(set(seen)), "um evento apareceu duas vezes na floresta"


def test_the_descent_over_a_cyclic_trail_terminates() -> None:
    """A descida também precisa cortar o ciclo, e não só a construção da floresta."""
    trail = cyclic_trail()
    found = descendants_of(trail, trail[0].event_id)
    assert {e.event_id for e in found} <= {e.event_id for e in trail}
    assert len({e.event_id for e in found}) == len(found)


def test_every_event_of_the_slice_appears_exactly_once_in_the_forest() -> None:
    forest = build_causal_forest(CASCADE)
    seen = [event.event_id for root in forest for event in root.walk()]
    assert sorted(seen) == sorted(e.event_id for e in CASCADE)
    assert len(seen) == len(set(seen))


# --- A mesma forma numa corrida REAL, e não só nos fixtures -------------------


@pytest.fixture(scope="module")
def real_trail() -> list[DomainEvent]:
    """Meteoro LETAL declarado num planeta que já tem vida instalada.

    O catálogo de produção fere sem aniquilar; acima de 1 a mortalidade satura no
    recorte e o aniquilamento é total em toda semente — o que torna a cadeia até
    `SpeciesExtinct` um cenário, e não um sorteio (mesmo ajuste de
    `test_causal_chain_meteor_to_extinction`).
    """
    store = InMemoryEventStore()
    planet = build_scripted_planet(EventKind.METEOR, lead=4, mortality=2.0, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("meteor", 2027), PARAMS))
    for _ in range(400):
        snapshot = planet.tick(snapshot).snapshot
    return list(store.scientific_view())


async def test_a_real_run_reconstructs_the_meteor_to_extinction_chain(
    real_trail: list[DomainEvent],
) -> None:
    """Fim a fim: da corrida ao dossiê, com o elo meteoro→extinção navegável."""
    extinction = next(e for e in real_trail if e.event_type == SPECIES_EXTINCT)
    assembler = ContextAssembler(InMemoryEventQuery.of(PLANET, real_trail))
    context = await assembler.execute(PLANET, ContextSlice.of_event(extinction.event_id))

    chain = [e.event_type for e in context.ancestry]
    assert chain[0] == SPECIES_EXTINCT
    assert METEOR_IMPACT in chain, f"a extinção não sobe até o meteoro pelo causation_id: {chain}"

    meteor = next(e for e in context.ancestry if e.event_type == METEOR_IMPACT)
    downstream = {e.event_id for e in context.consequences_of(meteor.event_id)}
    assert extinction.event_id in downstream, "a descida do meteoro não alcança a extinção"
