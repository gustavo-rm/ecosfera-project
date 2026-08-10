"""O contrato de query do Event Store — o que o M6 vai assinar.

O M5 entrega a SUPERFÍCIE de leitura, não consumidores. Implementar consumidores
agora fixaria decisões de produto ainda em aberto (o que `/species` significa —
`docs/decisions/pending.md`); entregar o contrato permite ao M6 assinar sem
renegociar o formato.

Cobre também as três projeções do ADR-ARCH-0002: científica e técnica
implementadas, educacional deixada para o M6 com a garantia de que o envelope
carrega tudo de que ela precisará.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ecosfera_ai.application.platform.event_query import (
    EventQuery,
    InMemoryEventQuery,
    ScientificProjection,
    TechnicalProjection,
    educational_payload_is_complete,
)
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.shared_kernel.engine import TickBudget
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
PLANET = "query"


def _trail(budget: TickBudget | None = None, ticks: int = 300) -> list[DomainEvent]:
    store = InMemoryEventStore()
    planet = build_planet_engine(PARAMS, budget=budget or PARAMS.engine_budget, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("query", 2027), PARAMS))
    for _ in range(ticks):
        snapshot = planet.tick(snapshot).snapshot
    return list(store.events)


@pytest.fixture(scope="module")
def events() -> list[DomainEvent]:
    return _trail()


# --- A superfície de consulta -------------------------------------------------


async def test_an_empty_query_restricts_nothing_but_diagnostics(events: list[DomainEvent]) -> None:
    """Diagnóstico técnico fica FORA por padrão (ADR-ARCH-0002).

    A visão científica não deve ver estouro de orçamento como se fosse fenômeno
    do planeta.
    """
    found = await InMemoryEventQuery.of(PLANET, events).query(PLANET, EventQuery())
    assert found, "a consulta vazia não devolveu nada"
    assert all(not e.is_diagnostic for e in found)


async def test_query_by_tick_window(events: list[DomainEvent]) -> None:
    """Só a janela de ticks — o nome antigo prometia era e não a exercitava."""
    window = await InMemoryEventQuery.of(PLANET, events).query(
        PLANET, EventQuery(from_tick=50, to_tick=100)
    )
    assert window
    assert all(50 <= e.occurred_at.tick <= 100 for e in window)


async def test_query_by_era() -> None:
    """O campo que a varredura do ADR 0023 achou aplicado e sem teste.

    Trilha SINTÉTICA de propósito: um laço de `tick()` não atravessa era, então
    a corrida real fica toda na era 0 e o filtro seria indistinguível de um
    campo decorativo — que é exatamente o defeito sob correção.
    """
    from tests.support_events import cascade

    early = cascade(era=0, base_tick=10, owner="contrato")
    late = cascade(era=3, base_tick=400, owner="contrato")
    store = InMemoryEventQuery.of(PLANET, [*early, *late])

    found = await store.query(PLANET, EventQuery(era=3))
    assert {e.event_id for e in found} == {e.event_id for e in late}
    assert await store.query(PLANET, EventQuery(era=99)) == ()


async def test_query_by_causation_walks_one_step_down(events: list[DomainEvent]) -> None:
    """Também aplicado e sem teste: os filhos diretos de um evento."""
    linked = next(e for e in events if e.causation_id)
    children = await InMemoryEventQuery.of(PLANET, events).query(
        PLANET, EventQuery(causation_id=linked.causation_id)
    )
    assert children
    assert all(e.causation_id == linked.causation_id for e in children)
    assert linked.event_id in {e.event_id for e in children}


async def test_query_by_cause_code(events: list[DomainEvent]) -> None:
    """ "Quantas extinções catastróficas houve?" sem varrer a trilha inteira."""
    codes = {str(e.cause_code.value) for e in events if not e.is_diagnostic}
    chosen = sorted(codes)[0]
    found = await InMemoryEventQuery.of(PLANET, events).query(
        PLANET, EventQuery(cause_codes=frozenset({chosen}))
    )
    assert found
    assert all(str(e.cause_code.value) == chosen for e in found)


async def test_query_by_engine(events: list[DomainEvent]) -> None:
    """Só o Engine — o nome antigo prometia tipo de evento e não o exercitava."""
    found = await InMemoryEventQuery.of(PLANET, events).query(
        PLANET, EventQuery(engine_ids=frozenset({"climate"}))
    )
    assert found
    assert all(e.engine_id == "climate" for e in found)


async def test_query_by_event_type(events: list[DomainEvent]) -> None:
    """O terceiro campo que a varredura achou aplicado e sem teste."""
    types = {e.event_type for e in events if not e.is_diagnostic}
    chosen = sorted(types)[0]
    found = await InMemoryEventQuery.of(PLANET, events).query(
        PLANET, EventQuery(event_types=frozenset({chosen}))
    )
    assert found
    assert all(e.event_type == chosen for e in found)


async def test_the_query_is_scoped_to_a_planet(events: list[DomainEvent]) -> None:
    """O escopo que o M5 declarava e não aplicava — agora na dimensão certa.

    A implementação em memória guarda trilhas POR PLANETA justamente para poder
    expressar o vazamento; uma lista única não teria o que vazar, e o teste
    passaria por vacuidade.
    """
    store = InMemoryEventQuery({"ana": tuple(events), "bruno": ()})
    assert await store.query("ana", EventQuery())
    assert await store.query("bruno", EventQuery()) == ()
    assert await store.query("planeta-inexistente", EventQuery()) == ()


async def test_query_by_correlation_groups_one_tick(events: list[DomainEvent]) -> None:
    """A correlação agrupa o que aconteceu no MESMO tick — a base da cadeia."""
    target = events[len(events) // 2].correlation_id
    found = await InMemoryEventQuery.of(PLANET, events).query(
        PLANET, EventQuery(correlation_id=target)
    )
    assert len(found) >= 1
    assert len({e.occurred_at.tick for e in found}) == 1


async def test_the_causal_chain_walks_from_effect_to_root(events: list[DomainEvent]) -> None:
    query = InMemoryEventQuery.of(PLANET, events)
    linked = [e for e in events if e.causation_id]
    assert linked, "nenhum evento declarou causa"

    chains = [await query.causal_chain(PLANET, e.event_id) for e in linked]
    longest = max(chains, key=len)
    assert len(longest) >= 2, "a cadeia não anda"
    assert longest[0].event_id == max(chains, key=len)[0].event_id
    # Sobe no tempo: cada elo é igual ou anterior ao anterior.
    ticks = [e.occurred_at.tick for e in longest]
    assert ticks == sorted(ticks, reverse=True)


async def test_an_unknown_id_yields_an_empty_chain(events: list[DomainEvent]) -> None:
    assert await InMemoryEventQuery.of(PLANET, events).causal_chain(PLANET, "nao-existe") == ()


async def test_a_causation_cycle_stops_instead_of_looping_forever() -> None:
    """Trilha corrompida não trava o consumidor.

    O M5 aceita import de simulação vinda de outra máquina (ADR 0021), então um
    `causation_id` em ciclo é entrada possível, não hipótese. Travar num laço
    infinito seria pior que devolver a cadeia parcial.
    """
    from dataclasses import replace

    from tests.support_events import cascade

    trail = cascade(owner="ciclo")
    # A raiz passa a apontar o próprio neto como causa.
    looped = [replace(trail[0], causation_id=trail[-1].event_id), *trail[1:]]

    chain = await InMemoryEventQuery.of(PLANET, looped).causal_chain(PLANET, looped[-1].event_id)
    assert len(chain) == 3, f"o ciclo não foi cortado: {len(chain)} elos"
    assert len({e.event_id for e in chain}) == len(chain), "um evento repetiu na cadeia"


# --- As três projeções --------------------------------------------------------


def test_the_scientific_projection_is_ordered_by_simulation_time(
    events: list[DomainEvent],
) -> None:
    """Ordenada por tempo de SIMULAÇÃO, não por ordem de chegada.

    A ordem de chegada é acidente de execução; a pesquisa quer o fenômeno.
    """
    projected = ScientificProjection(events).of()
    keys = [(e.occurred_at.era, e.occurred_at.tick) for e in projected]
    assert keys == sorted(keys)
    assert all(not e.is_diagnostic for e in projected)


async def test_the_scientific_projection_counts_mechanisms(events: list[DomainEvent]) -> None:
    counts = ScientificProjection(events).by_cause()
    assert counts
    assert sum(counts.values()) == len(ScientificProjection(events).of())


async def test_the_technical_projection_is_the_exact_complement(events: list[DomainEvent]) -> None:
    """Científica e técnica particionam a trilha: nada some, nada duplica."""
    scientific = ScientificProjection(events).of()
    technical = TechnicalProjection(events).diagnostics()
    assert len(scientific) + len(technical) == len(events)
    assert not {e.event_id for e in scientific} & {e.event_id for e in technical}


async def test_the_technical_projection_sees_budget_overruns() -> None:
    """O operador quer ver o que o motor reclamou — e só isso."""
    starved = _trail(budget=TickBudget(max_duration_s=-1.0), ticks=3)
    technical = TechnicalProjection(starved)
    assert technical.diagnostics(), "o estouro de orçamento não chegou à visão técnica"
    assert technical.by_engine(), "o diagnóstico não identifica o Engine"


def test_the_educational_view_would_have_everything_it_needs(
    events: list[DomainEvent],
) -> None:
    """A visão educacional é do M6 — aqui só se confere que nada lhe falta.

    Ela precisará do mecanismo, do elo causal, do instante e dos números que
    sustentam a frase. Descobrir uma falta só no M6 seria descobrir tarde.
    """
    assert educational_payload_is_complete(events)
