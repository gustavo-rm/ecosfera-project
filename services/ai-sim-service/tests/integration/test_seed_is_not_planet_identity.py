"""A semente NÃO identifica o planeta — e a query tem de distingui-los mesmo assim.

`PlanetSeed` carrega `planet_id` e `seed` como campos independentes: dois
planetas podem compartilhar semente, e é o que acontece quando uma turma recebe
"usem a semente 2027". A semente controla a estocasticidade da trajetória, não a
identidade da corrida.

O ponto é fechar uma saída tentadora: como o envelope §4 carrega `seed` e não
carrega planeta, alguém poderia escopar por semente e achar que resolveu. Estes
testes mostram por que não resolve.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations
from tests.support_events import SHARED_SEED, cascade

from ecosfera_ai.application.platform.event_query import EventQuery
from ecosfera_ai.infrastructure.persistence.postgres_event_store import (
    PostgresEventQuery,
    PostgresEventStore,
)

pytestmark = requires_postgres()

ANA = "turma-a-ana"
BRUNO = "turma-a-bruno"


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
async def classroom(engine: Any) -> AsyncIterator[PostgresEventQuery]:
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM simulation.event_log"))

    store = PostgresEventStore(engine)
    await store.append_many(ANA, cascade(seed=SHARED_SEED, owner="ana"))
    await store.append_many(BRUNO, cascade(seed=SHARED_SEED, owner="bruno"))
    yield PostgresEventQuery(engine)


async def test_the_query_tells_the_two_apart_despite_the_shared_seed(
    classroom: PostgresEventQuery,
) -> None:
    ana = await classroom.query(ANA, EventQuery())
    bruno = await classroom.query(BRUNO, EventQuery())

    assert len(ana) == len(bruno) == 3
    assert {e.cause_detail.get("owner") for e in ana} == {"ana"}
    assert {e.cause_detail.get("owner") for e in bruno} == {"bruno"}


async def test_the_seed_carried_by_the_events_is_the_same_on_both_sides(
    classroom: PostgresEventQuery,
) -> None:
    """Contraprova: escopar por semente não separaria nada.

    As duas trilhas trazem a mesma semente. Quem separa é o planeta, que vive no
    armazenamento — exatamente a decisão do ADR 0023.
    """
    ana = await classroom.query(ANA, EventQuery())
    bruno = await classroom.query(BRUNO, EventQuery())

    assert {e.seed for e in ana} == {e.seed for e in bruno}, (
        "as sementes divergiram — o cenário deixou de ser adversarial"
    )
    assert {e.event_id for e in ana} == {e.event_id for e in bruno}, (
        "os ids divergiram — a colisão que motiva a chave composta sumiu"
    )
