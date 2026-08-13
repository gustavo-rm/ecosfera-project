"""O corpus sobre pgvector: a busca do banco concorda com a de referência.

**Verificação em CI, não local.** Exige Postgres com a extensão `vector`
(Testcontainers, imagem `pgvector/pgvector:pg16`). Sem daemon Docker este arquivo
PULA; no CI, `ECOSFERA_REQUIRE_POSTGRES` torna a ausência uma FALHA — o pulo
continua onde é honesto e some onde seria esconderijo.

## Por que o embedder de referência, e não o semântico

O CI sincroniza `--extra sim --extra infra --group dev` — **sem o extra `ai`**. Um
teste que dependesse de `sentence-transformers` pularia exatamente onde precisa
rodar, e um pulo silencioso é o que a política de zero-skip existe para impedir.
O `DeterministicEmbedder` roda em qualquer lugar, e é por isso que ele é a
implementação de referência e não uma conveniência.

## O que se afirma, e por que a igualdade importa

O adaptador Postgres ordena PELO BANCO (`<=>` do pgvector, índice HNSW), enquanto
a implementação em memória ordena em Python. São dois caminhos para o mesmo
número, e o ADR 0023 ensinou o que acontece quando duas cópias da mesma regra
divergem em silêncio. Afirmar a IGUALDADE das duas — mesma ordem, mesmos scores —
é o que mantém a implementação de referência valendo como espelho do adaptador.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations
from tests.support_rag import manifest

from ecosfera_ai.application.rag.corpus_index import InMemoryCorpusIndex
from ecosfera_ai.application.rag.index_corpus import IndexCorpusUseCase
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase
from ecosfera_ai.domain.rag.corpus import CorpusCategory
from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder

pytestmark = requires_postgres()

MANIFEST = manifest()
QUERIES = (
    "especiação ancestral comum linhagens",
    "aptidão contextual ou absoluta",
    "efeito estufa gás carbônico",
    "extinção catastrófica",
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


@pytest.fixture
async def indexed(engine: Any) -> AsyncIterator[Any]:
    """Corpus de produção indexado num banco limpo."""
    from sqlalchemy import text

    from ecosfera_ai.infrastructure.persistence.postgres_corpus import PostgresCorpusIndex

    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM rag.corpus_entry"))
    index = PostgresCorpusIndex(engine)
    await IndexCorpusUseCase(DeterministicEmbedder(), index).execute(MANIFEST)
    yield index


# --- O schema existe como a migration 0006 o declarou -------------------------


async def test_the_migration_created_the_corpus_table_with_its_constraints(engine: Any) -> None:
    from sqlalchemy import text

    async with engine.connect() as conn:
        columns = await conn.execute(
            text(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'rag' AND table_name = 'corpus_entry'"
            )
        )
        nullable = {row.column_name: row.is_nullable for row in columns}

    for required in ("entry_id", "model_name", "category", "source", "content", "embedding"):
        assert nullable.get(required) == "NO", f"{required} deveria ser NOT NULL"


async def test_an_anonymous_entry_is_refused_by_the_database(engine: Any) -> None:
    """Proveniência é invariante de BANCO, e não convenção do YAML."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    zero = "[" + ",".join(["0.0"] * 768) + "]"
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO rag.corpus_entry "
                    "(entry_id, model_name, category, source, content, embedding) VALUES "
                    "('X', 'm', 'vocabulary_rule', '   ', 'texto', CAST(:v AS vector))"
                ),
                {"v": zero},
            )


async def test_an_external_reference_without_license_is_refused(engine: Any) -> None:
    """A regra de direito autoral, imposta pelo banco."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    zero = "[" + ",".join(["0.0"] * 768) + "]"
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO rag.corpus_entry "
                    "(entry_id, model_name, category, source, content, license, embedding) VALUES "
                    "('Y', 'm', 'external_reference', 'algum livro', 'trecho', '', "
                    "CAST(:v AS vector))"
                ),
                {"v": zero},
            )


# --- O corpus atravessa o banco inteiro --------------------------------------


async def test_the_whole_manifest_survives_the_round_trip(indexed: Any) -> None:
    retriever = RetrievePassagesUseCase(DeterministicEmbedder(), indexed)
    found = await retriever.execute("planeta vida clima espécie evolução", limit=100)
    assert {passage.entry_id for passage in found} == {entry.entry_id for entry in MANIFEST.entries}


async def test_provenance_survives_the_round_trip(indexed: Any) -> None:
    """Origem, faixa, códigos e a ressalva de conferência voltam intactos."""
    retriever = RetrievePassagesUseCase(DeterministicEmbedder(), indexed)
    found = await retriever.execute(
        "efeito estufa", limit=1, categories=frozenset({CorpusCategory.CURRICULUM_OBJECTIVE})
    )
    original = next(e for e in MANIFEST.entries if e.entry_id == found[0].entry_id)

    assert found[0].source == original.source
    assert found[0].bncc_codes == original.bncc_codes
    assert found[0].grade_band == original.grade_band
    assert found[0].code_verified == original.code_verified


# --- A paridade com a implementação de referência -----------------------------


@pytest.mark.parametrize("query", QUERIES)
async def test_postgres_and_the_reference_rank_the_same(indexed: Any, query: str) -> None:
    embedder = DeterministicEmbedder()
    memory = InMemoryCorpusIndex()
    await IndexCorpusUseCase(embedder, memory).execute(MANIFEST)

    from_db = await RetrievePassagesUseCase(embedder, indexed).execute(query, limit=5)
    in_memory = await RetrievePassagesUseCase(embedder, memory).execute(query, limit=5)

    assert [p.entry_id for p in from_db] == [p.entry_id for p in in_memory]
    for db_passage, memory_passage in zip(from_db, in_memory, strict=True):
        assert db_passage.similarity == pytest.approx(memory_passage.similarity, abs=1e-6)


async def test_the_category_filter_works_in_sql_too(indexed: Any) -> None:
    found = await RetrievePassagesUseCase(DeterministicEmbedder(), indexed).execute(
        "extinção", limit=20, categories=frozenset({CorpusCategory.VALIDATED_CORRECTION})
    )
    assert found
    assert all(p.category is CorpusCategory.VALIDATED_CORRECTION for p in found)


async def test_the_cause_code_filter_works_in_sql_too(indexed: Any) -> None:
    found = await RetrievePassagesUseCase(DeterministicEmbedder(), indexed).for_cause_code(
        "CATASTROPHIC_EVENT", limit=10
    )
    assert found
    assert found[0].entry_id == "VAL-Q8"
    assert all("CATASTROPHIC_EVENT" in p.relevant_cause_codes for p in found)


# --- Modelos não se misturam --------------------------------------------------


async def test_reindexing_is_idempotent(indexed: Any) -> None:
    """Indexar duas vezes o mesmo manifesto deixa o índice igual."""
    embedder = DeterministicEmbedder()
    before = await RetrievePassagesUseCase(embedder, indexed).execute("especiação", limit=50)
    await IndexCorpusUseCase(embedder, indexed).execute(MANIFEST)
    after = await RetrievePassagesUseCase(embedder, indexed).execute("especiação", limit=50)
    assert [p.entry_id for p in before] == [p.entry_id for p in after]


async def test_a_query_never_sees_another_models_vectors(indexed: Any, engine: Any) -> None:
    """A garantia contra comparar espaços vetoriais distintos.

    Uma linha de outro modelo é gravada à mão com um vetor que seria o mais
    próximo possível de qualquer consulta. Se a busca a devolvesse, o Tutor
    receberia a passagem errada com um número plausível ao lado — que é pior que
    um erro que estoura.
    """
    from sqlalchemy import text

    intruder = "[" + ",".join(["1.0"] * 768) + "]"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO rag.corpus_entry "
                "(entry_id, model_name, category, source, content, embedding) VALUES "
                "('INTRUSO', 'outro-modelo-v9', 'vocabulary_rule', 'teste', "
                "'texto de outro espaço vetorial', CAST(:v AS vector))"
            ),
            {"v": intruder},
        )

    found = await RetrievePassagesUseCase(DeterministicEmbedder(), indexed).execute(
        "especiação", limit=50
    )
    assert "INTRUSO" not in {passage.entry_id for passage in found}
