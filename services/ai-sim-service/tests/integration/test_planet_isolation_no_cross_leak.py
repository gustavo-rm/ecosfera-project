"""ADVERSARIAL: a consulta de um planeta não pode devolver evento de outro.

O teste central da correção. Dois planetas, a MESMA semente, eventos do mesmo
tipo nos mesmos ticks — o pior caso possível, montado de propósito, porque com
semente compartilhada os `event_id` são byte a byte IDÊNTICOS entre os planetas.

O que se protege aqui não é uma consulta errada visível. É o Tutor narrando ao
aluno, com total confiança e citando eventos reais, a catástrofe do planeta de
OUTRO aluno. Toda afirmação seria derivável de um event log — só não do dele —, e
por isso nenhum teste de alucinação do M6.4 pegaria: a resposta estaria ancorada,
apenas na trilha errada.

Roda contra o Postgres de verdade (Testcontainers). Sem Docker pula numa máquina
de dev; no CI, `ECOSFERA_REQUIRE_POSTGRES` transforma a ausência em FALHA
(`tests/docker_guard.py`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations
from tests.support_events import SHARED_SEED, cascade

from ecosfera_ai.application.platform.event_query import EventQuery
from ecosfera_ai.engines.event.events import METEOR_IMPACT
from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT
from ecosfera_ai.infrastructure.persistence.postgres_event_store import (
    PostgresEventQuery,
    PostgresEventStore,
)

pytestmark = requires_postgres()

TERRA = "planeta-da-ana"
MARTE = "planeta-do-bruno"


@pytest.fixture(scope="module")
def engine() -> Iterator[Any]:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        url = container.get_connection_url()
        run_migrations(url)  # inclui a 0005, que torna a chave (planet_id, event_id)
        yield create_async_engine(url, poolclass=NullPool, connect_args={"statement_cache_size": 0})


@pytest.fixture
async def two_planets(engine: Any) -> AsyncIterator[PostgresEventQuery]:
    """Dois planetas com a MESMA semente e trilhas de `event_id` idênticos."""
    store = PostgresEventStore(engine)
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("DELETE FROM simulation.event_log"))

    ana = cascade(seed=SHARED_SEED, owner="ana")
    bruno = cascade(seed=SHARED_SEED, owner="bruno")
    assert [e.event_id for e in ana] == [e.event_id for e in bruno], (
        "a premissa do teste caiu: as sementes iguais deixaram de colidir os ids"
    )
    await store.append_many(TERRA, ana)
    await store.append_many(MARTE, bruno)
    yield PostgresEventQuery(engine)


async def test_both_planets_were_actually_stored(two_planets: PostgresEventQuery) -> None:
    """Sem isto, o isolamento passaria por não haver o que vazar.

    É a contraprova da migration 0005: com a chave única GLOBAL do M5, o segundo
    planeta seria recusado como reprocessamento do primeiro e este teste falharia
    aqui, antes de qualquer asserção de vazamento.
    """
    assert len(await two_planets.query(TERRA, EventQuery())) == 3
    assert len(await two_planets.query(MARTE, EventQuery())) == 3


async def test_no_event_of_the_other_planet_leaks_in_any_slice(
    two_planets: PostgresEventQuery,
) -> None:
    """Nenhum recorte devolve evento do outro planeta — nem o mais amplo."""
    slices = [
        EventQuery(),
        EventQuery(era=1),
        EventQuery(from_tick=0, to_tick=10_000),
        EventQuery(event_types=frozenset({SPECIES_EXTINCT})),
        EventQuery(engine_ids=frozenset({"evolution"})),
        EventQuery(cause_codes=frozenset({"THERMAL_INTOLERANCE"})),
        EventQuery(include_diagnostics=True),
    ]
    for spec in slices:
        terra = await two_planets.query(TERRA, spec)
        marte = await two_planets.query(MARTE, spec)

        # Contar não bastaria: os ids colidem, então uma trilha vazada teria o
        # mesmo tamanho. Quem denuncia é a MARCA — o conteúdo diverge onde o id
        # não diverge.
        assert all(e.cause_detail.get("owner") == "ana" for e in terra), (
            f"{spec} devolveu evento do outro planeta na consulta de {TERRA}"
        )
        assert all(e.cause_detail.get("owner") == "bruno" for e in marte), (
            f"{spec} devolveu evento do outro planeta na consulta de {MARTE}"
        )
        assert len(terra) <= 3 and len(marte) <= 3, f"{spec} devolveu a soma dos dois planetas"


async def test_the_causal_chain_does_not_walk_into_the_other_planet(
    two_planets: PostgresEventQuery,
) -> None:
    """A cadeia sobe DENTRO do planeta.

    Com `event_id` colidindo, uma subida sem escopo poderia trocar de corrida no
    meio do caminho e devolver a causa do planeta do outro aluno.
    """
    extinction = next(
        e for e in await two_planets.query(TERRA, EventQuery()) if e.event_type == SPECIES_EXTINCT
    )
    chain = await two_planets.causal_chain(TERRA, extinction.event_id)

    assert [e.event_type for e in chain] == [
        SPECIES_EXTINCT,
        "TemperatureShift",
        METEOR_IMPACT,
    ]
    assert len(chain) == 3, "a cadeia andou além do planeta"
    assert all(e.cause_detail.get("owner") == "ana" for e in chain), (
        "a cadeia trocou de corrida no meio: um elo veio do planeta do outro aluno"
    )


async def test_an_unknown_planet_returns_nothing_rather_than_everything(
    two_planets: PostgresEventQuery,
) -> None:
    """O modo de falhar importa: vazio, nunca "tudo".

    Um escopo aplicado como filtro opcional degradaria para "sem filtro" e
    devolveria a base inteira — que é a forma que o defeito do M5 tinha.
    """
    assert await two_planets.query("planeta-que-nao-existe", EventQuery()) == ()
    assert await two_planets.causal_chain("planeta-que-nao-existe", "seja-qual-for") == ()


async def test_deleting_by_planet_does_not_touch_the_other(
    two_planets: PostgresEventQuery, engine: Any
) -> None:
    """Escopo é escopo nos dois sentidos — o de Ana some, o de Bruno fica."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM simulation.event_log WHERE planet_id = :p"), {"p": TERRA}
        )

    assert await two_planets.query(TERRA, EventQuery()) == ()
    assert len(await two_planets.query(MARTE, EventQuery())) == 3


async def test_reprocessing_the_same_planet_stays_idempotent(
    two_planets: PostgresEventQuery, engine: Any
) -> None:
    """A idempotência do M5 sobrevive à chave composta — no grão certo."""
    store = PostgresEventStore(engine)
    await store.append_many(TERRA, cascade(seed=SHARED_SEED))
    assert len(await two_planets.query(TERRA, EventQuery())) == 3, "reprocessar duplicou a trilha"
