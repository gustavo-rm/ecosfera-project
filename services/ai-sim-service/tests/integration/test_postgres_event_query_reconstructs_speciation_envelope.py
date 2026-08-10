"""O envelope NOVO de `SpeciationOccurred` sobrevive ao Postgres, campo a campo.

**Verificação em CI, não local.** Exige Postgres de verdade (Testcontainers).
Sem daemon Docker este arquivo PULA; no CI, `ECOSFERA_REQUIRE_POSTGRES` torna a
ausência uma FALHA — o pulo continua onde é honesto e some onde seria esconderijo
(`tests/docker_guard.py`, política do M5).

## Por que um arquivo próprio, e não confiança no do M5

`test_event_store_persist_and_query` afirma que o envelope §4 sobrevive ao banco,
e é verdade — mas o evento que ele persiste é um `SpeciesExtinct` com
`participants=["species:community"]` e um `cause_detail` de DUAS chaves. O
envelope que a Fase 0 mudou é outro: três participantes com papéis e um
`cause_detail` de vinte e duas chaves, dezoito delas floats de genoma
(BIO-001/BIO-002, ADR 0023).

A diferença não é de tamanho, é de risco. O que pode se perder no caminho até o
JSONB e de volta é justamente o que aquele teste não tem: uma lista de três
elementos na ordem certa, e floats de genoma que precisam voltar com o ÚLTIMO
bit — um genoma relido com precisão degradada faria o replay divergir sem que
nada estourasse na leitura.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations
from tests.support import community_genome, speciation_event, speciation_snapshot

from ecosfera_ai.engines.evolution.events import (
    ANCESTOR_ROLE,
    LINEAGE_ROLE,
    SPECIATION_CAUSES,
)
from ecosfera_ai.shared_kernel.events import DomainEvent, event_from_dict, event_to_dict

pytestmark = requires_postgres()

PLANET = "pg-speciation"
TRAITS = ("temp_optimum", "temp_tolerance", "water_need", "size", "metabolism", "trophic_level")
GENE_KEYS = tuple(
    f"{prefix}_gene_{trait}"
    for prefix in ("ancestor", "lineage_a", "lineage_b")
    for trait in TRAITS
)


@pytest.fixture(scope="module")
def engine() -> Iterator[Any]:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        url = container.get_connection_url()
        run_migrations(url)
        yield create_async_engine(url, poolclass=NullPool, connect_args={"statement_cache_size": 0})


def _speciation(tick: int) -> DomainEvent:
    """Um `SpeciationOccurred` de verdade, emitido pelo Engine (não fabricado).

    Um por teste, com `tick` distinto. Não é fixture compartilhada de propósito:
    `event_log_event_id_key` é UNIQUE em `event_id` na tabela INTEIRA — reusar o
    mesmo evento faria o segundo insert violar a restrição, e o teste falharia
    por colisão de fixture em vez de por defeito de persistência.
    """
    return speciation_event(speciation_snapshot(community_genome(temp_optimum=26.0), tick=tick))


async def _persist(engine: Any, event: DomainEvent, *, planet_id: str = PLANET) -> None:
    """Grava pelo mesmo caminho do M5: envelope no JSONB e nas colunas indexáveis."""
    from sqlalchemy import text

    payload = event_to_dict(event)
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
                "planet_id": planet_id,
                "payload": json.dumps(payload),
                **{
                    key: payload[key]
                    for key in (
                        "tick",
                        "event_type",
                        "event_id",
                        "engine_id",
                        "era",
                        "seed",
                        "cause_code",
                        "correlation_id",
                        "causation_id",
                        "granularity",
                    )
                },
            },
        )


async def _read_back(engine: Any, event: DomainEvent) -> DomainEvent:
    from sqlalchemy import text

    async with engine.connect() as conn:
        stored = (
            await conn.execute(
                text("SELECT payload FROM simulation.event_log WHERE event_id = :id"),
                {"id": event.event_id},
            )
        ).scalar_one()
    return event_from_dict(stored if isinstance(stored, dict) else json.loads(stored))


# --- O envelope volta inteiro --------------------------------------------------


@pytest.mark.asyncio
async def test_the_speciation_envelope_survives_the_database(engine: Any) -> None:
    speciation = _speciation(7)
    await _persist(engine, speciation)
    assert await _read_back(engine, speciation) == speciation


@pytest.mark.asyncio
async def test_the_three_roles_come_back_in_order(engine: Any) -> None:
    """`participants` é lista no JSONB: ordem e papéis são o que dá sentido a ela.

    Sem a ordem, `lineage_a` e `lineage_b` trocam de lugar em silêncio e o
    `cause_detail` passa a apontar para a linhagem errada.
    """
    speciation = _speciation(11)
    await _persist(engine, speciation, planet_id=f"{PLANET}-roles")
    restored = await _read_back(engine, speciation)

    assert restored.participants == speciation.participants
    assert len([p for p in restored.participants if p.startswith(f"{ANCESTOR_ROLE}:")]) == 1
    assert len([p for p in restored.participants if p.startswith(f"{LINEAGE_ROLE}:")]) == 2


@pytest.mark.asyncio
async def test_every_cause_detail_key_comes_back(engine: Any) -> None:
    speciation = _speciation(17)
    await _persist(engine, speciation, planet_id=f"{PLANET}-keys")
    restored = await _read_back(engine, speciation)
    assert set(restored.cause_detail) == set(speciation.cause_detail)


@pytest.mark.asyncio
async def test_every_genome_trait_comes_back_bit_for_bit(engine: Any) -> None:
    """Sem `approx`: um genoma relido com precisão degradada faz o replay divergir.

    E a divergência não estouraria aqui — apareceria muito depois, como um
    replay que não bate, quando ninguém mais associa a causa ao banco.
    """
    speciation = _speciation(23)
    await _persist(engine, speciation, planet_id=f"{PLANET}-genomes")
    restored = await _read_back(engine, speciation)

    for key in GENE_KEYS:
        assert restored.cause_detail[key] == speciation.cause_detail[key], (
            f"o traço {key} voltou do banco diferente do que entrou"
        )


@pytest.mark.asyncio
async def test_the_lineage_identities_come_back(engine: Any) -> None:
    speciation = _speciation(29)
    await _persist(engine, speciation, planet_id=f"{PLANET}-lineages")
    restored = await _read_back(engine, speciation)

    for key in ("ancestor_lineage_id", "lineage_a_id", "lineage_b_id"):
        assert restored.cause_detail[key] == speciation.cause_detail[key]


# --- A consulta que o M6 vai fazer ---------------------------------------------


@pytest.mark.asyncio
async def test_the_new_cause_code_is_queryable_as_a_column(engine: Any) -> None:
    """As causas do BIO-002 são novas: precisam caber na coluna e ser indexáveis.

    Se coubessem só no JSONB, "por que houve especiação?" viraria varredura de
    tabela — que é exatamente o que a migration 0004 existe para evitar.
    """
    from sqlalchemy import text

    speciation = _speciation(31)
    await _persist(engine, speciation, planet_id=f"{PLANET}-query")
    assert speciation.cause_code in SPECIATION_CAUSES

    async with engine.connect() as conn:
        found = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM simulation.event_log "
                    "WHERE planet_id = :planet AND cause_code = :code"
                ),
                {"planet": f"{PLANET}-query", "code": str(speciation.cause_code.value)},
            )
        ).scalar_one()
    assert found == 1, "a causa da especiação não é consultável pela coluna indexada"


@pytest.mark.asyncio
async def test_the_event_type_is_queryable_too(engine: Any) -> None:
    """Contraprova da consulta acima: ela não está contando qualquer linha."""
    from sqlalchemy import text

    await _persist(engine, _speciation(37), planet_id=f"{PLANET}-type")
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT event_type FROM simulation.event_log WHERE planet_id = :planet"),
                {"planet": f"{PLANET}-type"},
            )
        ).scalars()
        assert list(rows) == ["SpeciationOccurred"]
