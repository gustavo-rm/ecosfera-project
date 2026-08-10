"""Event Store PERSISTENTE: o envelope §4 sobrevive ao Postgres (M5).

**Verificação em CI, não local.** Este arquivo exige Postgres de verdade
(Testcontainers). Numa máquina sem Docker ele PULA; no CI, `ECOSFERA_REQUIRE_POSTGRES`
transforma a ausência em FALHA — o pulo continua disponível onde é honesto e deixa
de estar disponível onde seria esconderijo (`tests/docker_guard.py`).

O que se afirma aqui é o que o M2 não garantia: o envelope §4 como COLUNA
indexável, e não enterrado no JSONB. Sem isso, "quantas extinções catastróficas
houve?" e "qual a cadeia deste evento?" só se respondem varrendo a tabela.

Cobre também a migration 0004 aplicada limpa sobre o schema do M2.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations

from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT, EvolutionCauseCode
from ecosfera_ai.shared_kernel.events import EventEmitter, event_from_dict, event_to_dict
from ecosfera_ai.simulation_engine.params import load_params

PARAMS = load_params(Path("configs/simulation_params.yaml"))

pytestmark = requires_postgres()


@pytest.fixture(scope="module")
def engine() -> Iterator[Any]:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        url = container.get_connection_url()
        run_migrations(url)  # inclui a 0004 do M5
        yield create_async_engine(url, poolclass=NullPool, connect_args={"statement_cache_size": 0})


def _event(tick: int, *, causation: str | None = None) -> Any:
    return EventEmitter(engine_id="evolution", seed=2027, tick=tick, era=tick // 10).emit(
        SPECIES_EXTINCT,
        EvolutionCauseCode.CATASTROPHIC_EVENT,
        location={"region_id": "global"},
        participants=["species:community"],
        cause_detail={"biomass": 0.0, "biomass_before": 42.0},
        causation_id=causation,
    )


# --- A migration ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_migration_adds_the_envelope_columns(engine: Any) -> None:
    """A 0004 aplica limpa e o envelope §4 vira coluna."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'simulation' AND table_name = 'event_log'"
            )
        )
        columns = {row[0] for row in rows}

    for expected in (
        "event_id",
        "engine_id",
        "era",
        "seed",
        "cause_code",
        "correlation_id",
        "causation_id",
        "granularity",
    ):
        assert expected in columns, f"a migration 0004 não criou `{expected}`"
    # As colunas do M2 continuam — a 0004 ESTENDE, não substitui.
    for inherited in ("planet_id", "tick", "event_type", "payload"):
        assert inherited in columns


@pytest.mark.asyncio
async def test_the_query_indexes_exist(engine: Any) -> None:
    """Sem índice, o contrato de query do M6 vira varredura de tabela."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = 'simulation'")
        )
        indexes = {row[0] for row in rows}

    for expected in (
        "event_log_planet_era_tick_idx",
        "event_log_correlation_idx",
        "event_log_causation_idx",
        "event_log_cause_code_idx",
        # Composto desde a migration 0005: `event_id` é único POR PLANETA, não
        # globalmente. A chave global do M5 impedia gravar dois planetas de mesma
        # semente, porque a derivação do id não inclui planeta (ADR 0023).
        "event_log_planet_event_id_key",
    ):
        assert expected in indexes, f"índice `{expected}` ausente"


# --- O envelope sobrevive à persistência ---------------------------------------


@pytest.mark.asyncio
async def test_the_full_envelope_survives_a_round_trip(engine: Any) -> None:
    """Persistir e reler devolve o MESMO evento, campo a campo."""
    from sqlalchemy import text

    original = _event(7, causation="cause-abc")
    payload = event_to_dict(original)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO simulation.event_log
                    (planet_id, tick, event_type, payload, event_id, engine_id,
                     era, seed, cause_code, correlation_id, causation_id, granularity)
                VALUES
                    (:planet_id, :tick, :event_type, CAST(:payload AS jsonb), :event_id,
                     :engine_id, :era, :seed, :cause_code, :correlation_id,
                     :causation_id, :granularity)
                """
            ),
            {
                "planet_id": "pg-envelope",
                "tick": payload["tick"],
                "event_type": payload["event_type"],
                "payload": __import__("json").dumps(payload),
                "event_id": payload["event_id"],
                "engine_id": payload["engine_id"],
                "era": payload["era"],
                "seed": payload["seed"],
                "cause_code": payload["cause_code"],
                "correlation_id": payload["correlation_id"],
                "causation_id": payload["causation_id"],
                "granularity": payload["granularity"],
            },
        )

    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT payload FROM simulation.event_log WHERE event_id = :id"),
            {"id": payload["event_id"]},
        )
        stored = row.scalar_one()

    assert event_from_dict(stored) == original, "o envelope §4 não sobreviveu ao banco"


@pytest.mark.asyncio
async def test_the_same_event_cannot_be_stored_twice(engine: Any) -> None:
    """`event_id` é determinístico: reprocessar a corrida não duplica a trilha.

    A idempotência é propriedade do BANCO (índice único), não da disciplina de
    quem escreve — que é o que a torna confiável sob replay e reimport.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    duplicate = _event(9)
    payload = event_to_dict(duplicate)
    statement = text(
        "INSERT INTO simulation.event_log "
        "(planet_id, tick, event_type, payload, event_id) "
        "VALUES ('dup', :tick, :type, '{}'::jsonb, :id)"
    )
    values = {"tick": payload["tick"], "type": payload["event_type"], "id": payload["event_id"]}

    async with engine.begin() as conn:
        await conn.execute(statement, values)

    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(statement, values)


@pytest.mark.asyncio
async def test_the_same_event_id_is_allowed_in_a_different_planet(engine: Any) -> None:
    """O outro lado da migration 0005 — e a razão de ela existir.

    A derivação do `event_id` não inclui planeta, então dois planetas de mesma
    semente produzem ids idênticos. Com a chave única GLOBAL do M5, gravar o
    segundo era impossível: o banco recusava a corrida de um aluno como se fosse
    reprocessamento da de outro. Com `(planet_id, event_id)` isso passa a ser
    permitido — que é o que torna o isolamento entre planetas testável (ADR
    0023).
    """
    from sqlalchemy import text

    shared = _event(77)
    payload = event_to_dict(shared)
    statement = text(
        "INSERT INTO simulation.event_log "
        "(planet_id, tick, event_type, payload, event_id) "
        "VALUES (:planet, :tick, :type, '{}'::jsonb, :id)"
    )
    values = {"tick": payload["tick"], "type": payload["event_type"], "id": payload["event_id"]}

    async with engine.begin() as conn:
        await conn.execute(statement, {**values, "planet": "planeta-da-ana"})
        # MESMO event_id, planeta diferente: com a chave global isto levantaria
        # IntegrityError e a turma inteira ficaria presa ao primeiro aluno.
        await conn.execute(statement, {**values, "planet": "planeta-do-bruno"})

        stored = await conn.execute(
            text("SELECT planet_id FROM simulation.event_log WHERE event_id = :id"),
            {"id": payload["event_id"]},
        )
        assert {row[0] for row in stored} == {"planeta-da-ana", "planeta-do-bruno"}


@pytest.mark.asyncio
async def test_rows_written_before_the_envelope_are_invisible_to_the_new_reader(
    engine: Any,
) -> None:
    """Linha do M2 (sem envelope §4) não vira `DomainEvent` empobrecido.

    As colunas do envelope são nullable (ADR 0021), então linhas gravadas pelo
    caminho do M2 têm `event_id NULL`. Elas seguem válidas e legíveis por
    `load_events`, que é quem as escreveu — mas NÃO entram na porta de leitura
    nova: sem `cause_code` nem `causation_id`, reconstruí-las exigiria inventar
    campos, e o Tutor receberia um fato que o Event Store não contém.

    Fronteira registrada no ADR 0023.
    """
    from sqlalchemy import text

    from ecosfera_ai.application.platform.event_query import EventQuery
    from ecosfera_ai.infrastructure.persistence.postgres_event_store import PostgresEventQuery

    legacy = "planeta-legado"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO simulation.event_log (planet_id, tick, event_type, payload) "
                "VALUES (:p, 1, 'LifeEmerged', '{\"biomass\": 1.0}'::jsonb)"
            ),
            {"p": legacy},
        )
        stored = await conn.execute(
            text("SELECT count(*) FROM simulation.event_log WHERE planet_id = :p"), {"p": legacy}
        )
        assert stored.scalar_one() == 1, "a linha do M2 nem chegou a ser gravada"

    assert await PostgresEventQuery(engine).query(legacy, EventQuery()) == (), (
        "uma linha sem envelope §4 apareceu na porta de leitura nova"
    )


@pytest.mark.asyncio
async def test_querying_by_cause_code_and_correlation(engine: Any) -> None:
    """As consultas que o M6 vai fazer, contra o banco de verdade."""
    from sqlalchemy import text

    events = [_event(tick) for tick in (20, 21, 22)]
    async with engine.begin() as conn:
        for event in events:
            payload = event_to_dict(event)
            await conn.execute(
                text(
                    "INSERT INTO simulation.event_log "
                    "(planet_id, tick, event_type, payload, event_id, era, "
                    " cause_code, correlation_id) "
                    "VALUES ('pg-query', :tick, :type, '{}'::jsonb, :id, :era, :code, :corr)"
                ),
                {
                    "tick": payload["tick"],
                    "type": payload["event_type"],
                    "id": payload["event_id"],
                    "era": payload["era"],
                    "code": payload["cause_code"],
                    "corr": payload["correlation_id"],
                },
            )

    async with engine.connect() as conn:
        by_cause = await conn.execute(
            text(
                "SELECT count(*) FROM simulation.event_log "
                "WHERE planet_id = 'pg-query' AND cause_code = :code"
            ),
            {"code": "CATASTROPHIC_EVENT"},
        )
        assert by_cause.scalar_one() == 3

        target = event_to_dict(events[0])["correlation_id"]
        by_correlation = await conn.execute(
            text("SELECT count(*) FROM simulation.event_log WHERE correlation_id = :corr"),
            {"corr": target},
        )
        assert by_correlation.scalar_one() >= 1
