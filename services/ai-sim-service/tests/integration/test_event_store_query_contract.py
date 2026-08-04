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


def test_an_empty_query_restricts_nothing_but_diagnostics(events: list[DomainEvent]) -> None:
    """Diagnóstico técnico fica FORA por padrão (ADR-ARCH-0002).

    A visão científica não deve ver estouro de orçamento como se fosse fenômeno
    do planeta.
    """
    found = InMemoryEventQuery(events).query(EventQuery())
    assert found, "a consulta vazia não devolveu nada"
    assert all(not e.is_diagnostic for e in found)


def test_query_by_era_and_tick_window(events: list[DomainEvent]) -> None:
    window = InMemoryEventQuery(events).query(EventQuery(from_tick=50, to_tick=100))
    assert window
    assert all(50 <= e.occurred_at.tick <= 100 for e in window)


def test_query_by_cause_code(events: list[DomainEvent]) -> None:
    """ "Quantas extinções catastróficas houve?" sem varrer a trilha inteira."""
    codes = {str(e.cause_code.value) for e in events if not e.is_diagnostic}
    chosen = sorted(codes)[0]
    found = InMemoryEventQuery(events).query(EventQuery(cause_codes=frozenset({chosen})))
    assert found
    assert all(str(e.cause_code.value) == chosen for e in found)


def test_query_by_engine_and_event_type(events: list[DomainEvent]) -> None:
    found = InMemoryEventQuery(events).query(EventQuery(engine_ids=frozenset({"climate"})))
    assert found
    assert all(e.engine_id == "climate" for e in found)


def test_query_by_correlation_groups_one_tick(events: list[DomainEvent]) -> None:
    """A correlação agrupa o que aconteceu no MESMO tick — a base da cadeia."""
    target = events[len(events) // 2].correlation_id
    found = InMemoryEventQuery(events).query(EventQuery(correlation_id=target))
    assert len(found) >= 1
    assert len({e.occurred_at.tick for e in found}) == 1


def test_the_causal_chain_walks_from_effect_to_root(events: list[DomainEvent]) -> None:
    query = InMemoryEventQuery(events)
    linked = [e for e in events if e.causation_id]
    assert linked, "nenhum evento declarou causa"

    chains = [query.causal_chain(e.event_id) for e in linked]
    longest = max(chains, key=len)
    assert len(longest) >= 2, "a cadeia não anda"
    assert longest[0].event_id == max(chains, key=len)[0].event_id
    # Sobe no tempo: cada elo é igual ou anterior ao anterior.
    ticks = [e.occurred_at.tick for e in longest]
    assert ticks == sorted(ticks, reverse=True)


def test_an_unknown_id_yields_an_empty_chain(events: list[DomainEvent]) -> None:
    assert InMemoryEventQuery(events).causal_chain("nao-existe") == ()


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


def test_the_scientific_projection_counts_mechanisms(events: list[DomainEvent]) -> None:
    counts = ScientificProjection(events).by_cause()
    assert counts
    assert sum(counts.values()) == len(ScientificProjection(events).of())


def test_the_technical_projection_is_the_exact_complement(events: list[DomainEvent]) -> None:
    """Científica e técnica particionam a trilha: nada some, nada duplica."""
    scientific = ScientificProjection(events).of()
    technical = TechnicalProjection(events).diagnostics()
    assert len(scientific) + len(technical) == len(events)
    assert not {e.event_id for e in scientific} & {e.event_id for e in technical}


def test_the_technical_projection_sees_budget_overruns() -> None:
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
