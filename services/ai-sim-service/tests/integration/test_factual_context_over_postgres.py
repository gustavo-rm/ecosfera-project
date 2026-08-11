"""O dossiê montado sobre o Event Store REAL é o mesmo montado em memória.

**Verificação em CI, não local.** Exige Postgres de verdade (Testcontainers). Sem
daemon Docker este arquivo PULA; no CI, `ECOSFERA_REQUIRE_POSTGRES` torna a
ausência uma FALHA — o pulo continua onde é honesto e some onde seria esconderijo
(`tests/docker_guard.py`, política do M5).

## Por que este arquivo existe, tendo o teste de paridade da porta

`test_query_contract_parity` já afirma que `InMemoryEventQuery` e
`PostgresEventQuery` respondem igual. Isso cobre a PORTA. O que não cobre é o
consumidor em cima dela — e o risco do M6.0 está justamente aí, porque o dossiê
depende de campos que **não viraram coluna**.

`event_id`, `cause_code` e `causation_id` são colunas indexáveis; `participants`,
`environmental_factors`, `resources` e `cause_detail` viajam dentro do `payload`
JSONB. E são exatamente esses que o dossiê promove a fato estruturado: os papéis
`ancestor:`/`lineage:` que provam ancestral comum (BIO-001) e o `cause_detail` de
onde sai a distância genética. Uma degradação no caminho até o JSONB e de volta
apareceria como um dossiê mais pobre — não como uma exceção.

Afirmar a IGUALDADE dos dois dossiês, e não apenas que o de Postgres "tem
conteúdo", é o que torna o teste capaz de detectar perda parcial: um dossiê
empobrecido continua parecendo íntegro sozinho.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations
from tests.support import speciation_event
from tests.support_context import branching_cascade

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.application.platform.event_query import InMemoryEventQuery
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, ExtinctionNature
from ecosfera_ai.shared_kernel.events import DomainEvent

pytestmark = requires_postgres()

PLANET = "pg-factual-context"
CASCADE = branching_cascade()
METEOR, COOLING, _WILDFIRE, CATASTROPHIC, ECOLOGICAL = CASCADE


@pytest.fixture(scope="module")
def engine() -> Iterator[Any]:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        url = container.get_connection_url()
        run_migrations(url)
        yield create_async_engine(url, poolclass=NullPool, connect_args={"statement_cache_size": 0})


@pytest.fixture(scope="module")
def trail() -> list[DomainEvent]:
    """A cascata mais uma especiação REAL, emitida pelo Engine.

    A especiação entra porque é o envelope mais pesado que este serviço grava —
    três participantes com papéis e um `cause_detail` de vinte e duas chaves — e
    porque é o fato cuja leitura errada o BIO-001 existe para impedir.
    """
    return [*CASCADE, speciation_event()]


@pytest.fixture
async def stored(engine: Any, trail: list[DomainEvent]) -> AsyncIterator[Any]:
    """Grava a trilha num banco limpo — mesmo padrão do teste de paridade.

    A limpeza por teste não é zelo: `event_id` é determinístico, então reusar a
    trilha entre testes casaria com `ON CONFLICT DO NOTHING` e o segundo teste
    passaria a ler o que o primeiro gravou. Verde por acidente de ordem.
    """
    from sqlalchemy import text

    from ecosfera_ai.infrastructure.persistence.postgres_event_store import (
        PostgresEventQuery,
        PostgresEventStore,
    )

    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM simulation.event_log"))
    await PostgresEventStore(engine).append_many(PLANET, trail)
    yield PostgresEventQuery(engine)


async def test_the_era_dossier_is_identical_over_both_implementations(
    stored: Any, trail: list[DomainEvent]
) -> None:
    """Mesma fatia, mesmo dossiê — byte a byte no JSON."""
    era = ContextSlice.of_era(1)
    from_db = await ContextAssembler(stored).execute(PLANET, era)
    in_memory = await ContextAssembler(InMemoryEventQuery.of(PLANET, trail)).execute(PLANET, era)
    assert from_db.to_dict() == in_memory.to_dict()


async def test_the_causal_tree_survives_the_roundtrip(stored: Any) -> None:
    """O elo é coluna, mas a ÁRVORE é reconstruída — e continua ramificada."""
    context = await ContextAssembler(stored).execute(PLANET, ContextSlice.of_era(1))
    root = next(n for n in context.causal_roots if n.event.event_id == METEOR.event_id)
    assert len(root.consequences) == 3
    assert root.depth == 3


async def test_the_speciation_roles_survive_the_jsonb(
    stored: Any, trail: list[DomainEvent]
) -> None:
    """Os papéis vivem no `payload`, e é deles que sai o ancestral comum."""
    speciation = trail[-1]
    context = await ContextAssembler(stored).execute(
        PLANET, ContextSlice.of_era(speciation.occurred_at.era)
    )
    fact = next(f for f in context.speciations if f.event_id == speciation.event_id)
    assert len(fact.lineages) == 2
    assert fact.ancestor not in fact.lineages
    assert fact.genetic_distance is not None


async def test_the_extinction_distinction_survives_the_roundtrip(stored: Any) -> None:
    """`cause_code` é coluna; a família continua derivável dela (ADR 0019)."""
    context = await ContextAssembler(stored).execute(PLANET, ContextSlice.of_era(1))
    by_id = {f.event_id: f for f in context.extinctions}
    assert by_id[CATASTROPHIC.event_id].nature is ExtinctionNature.CATASTROPHIC
    assert by_id[CATASTROPHIC.event_id].triggered_by == METEOR.event_id
    assert by_id[ECOLOGICAL.event_id].nature is ExtinctionNature.ECOLOGICAL


async def test_the_event_slice_ascends_and_descends_over_the_real_store(stored: Any) -> None:
    """As duas direções contra o Event Store persistente, escopadas no planeta."""
    context = await ContextAssembler(stored).execute(
        PLANET, ContextSlice.of_event(ECOLOGICAL.event_id)
    )
    assert [e.event_id for e in context.ancestry] == [
        ECOLOGICAL.event_id,
        COOLING.event_id,
        METEOR.event_id,
    ]
    assert {e.event_id for e in context.consequences_of(METEOR.event_id)} >= {
        COOLING.event_id,
        ECOLOGICAL.event_id,
    }


async def test_an_unknown_planet_yields_an_empty_dossier_over_postgres(stored: Any) -> None:
    """O escopo é do banco, e um planeta sem trilha devolve vazio, nunca "tudo"."""
    context = await ContextAssembler(stored).execute("pg-nao-existe", ContextSlice.of_era(1))
    assert context.is_empty
