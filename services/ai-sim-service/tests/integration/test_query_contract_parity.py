"""As duas implementações da porta respondem a MESMA coisa.

`InMemoryEventQuery` só vale como implementação de referência se o adaptador
Postgres concordar com ela. Sem paridade afirmada, a suíte rápida testaria um
comportamento e a produção teria outro — e a diferença apareceria como o Tutor
respondendo em produção o que nenhum teste previu.

A paridade é verificada campo a campo do `EventQuery`, sobre a MESMA trilha,
comparando os conjuntos de `event_id` devolvidos.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations
from tests.support_events import SHARED_SEED, cascade

from ecosfera_ai.application.platform.event_query import (
    EventQuery,
    InMemoryEventQuery,
)
from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT
from ecosfera_ai.infrastructure.persistence.postgres_event_store import (
    PostgresEventQuery,
    PostgresEventStore,
)
from ecosfera_ai.shared_kernel.events import DomainEvent

pytestmark = requires_postgres()

PLANET = "paridade"
TRAIL = cascade(seed=SHARED_SEED, owner="paridade")

SPECS: list[EventQuery] = [
    EventQuery(),
    EventQuery(era=1),
    EventQuery(era=99),
    EventQuery(from_tick=100, to_tick=101),
    EventQuery(from_tick=102, to_tick=102),
    EventQuery(from_tick=10_000),
    EventQuery(correlation_id=TRAIL[0].correlation_id),
    EventQuery(causation_id=TRAIL[0].event_id),
    EventQuery(cause_codes=frozenset({"THERMAL_INTOLERANCE"})),
    EventQuery(event_types=frozenset({SPECIES_EXTINCT})),
    EventQuery(engine_ids=frozenset({"climate", "evolution"})),
    EventQuery(include_diagnostics=True),
]


@pytest.fixture(scope="module")
def engine() -> Iterator[Any]:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        url = container.get_connection_url()
        run_migrations(url)
        yield create_async_engine(url, poolclass=NullPool, connect_args={"statement_cache_size": 0})


@pytest.fixture
async def both(engine: Any) -> AsyncIterator[tuple[InMemoryEventQuery, PostgresEventQuery]]:
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM simulation.event_log"))
    await PostgresEventStore(engine).append_many(PLANET, TRAIL)
    yield InMemoryEventQuery.of(PLANET, TRAIL), PostgresEventQuery(engine)


def _ids(events: Sequence[DomainEvent]) -> list[str]:
    return sorted(e.event_id for e in events)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: repr(s)[:60])
async def test_both_implementations_return_the_same_events(
    both: tuple[InMemoryEventQuery, PostgresEventQuery], spec: EventQuery
) -> None:
    memory, postgres = both
    assert _ids(await memory.query(PLANET, spec)) == _ids(await postgres.query(PLANET, spec))


async def test_both_walk_the_same_causal_chain(
    both: tuple[InMemoryEventQuery, PostgresEventQuery],
) -> None:
    memory, postgres = both
    target = TRAIL[-1].event_id
    assert [e.event_id for e in await memory.causal_chain(PLANET, target)] == [
        e.event_id for e in await postgres.causal_chain(PLANET, target)
    ]


async def test_both_are_empty_for_an_unknown_planet(
    both: tuple[InMemoryEventQuery, PostgresEventQuery],
) -> None:
    memory, postgres = both
    assert await memory.query("outro", EventQuery()) == ()
    assert await postgres.query("outro", EventQuery()) == ()


async def test_the_envelope_survives_the_round_trip_intact(
    both: tuple[InMemoryEventQuery, PostgresEventQuery],
) -> None:
    """Paridade de FORMA, não só de conjunto.

    O adaptador divide o envelope entre colunas indexáveis e payload; se a
    reconstrução perdesse `genes`, `resources` ou `cause_detail`, os dois lados
    ainda devolveriam os mesmos ids e o consumidor receberia um fato pobre.
    """
    memory, postgres = both
    from ecosfera_ai.shared_kernel.events import event_to_dict

    expected = {e.event_id: event_to_dict(e) for e in await memory.query(PLANET, EventQuery())}
    actual = {e.event_id: event_to_dict(e) for e in await postgres.query(PLANET, EventQuery())}
    assert expected == actual
