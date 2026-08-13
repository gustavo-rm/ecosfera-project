"""Adaptador pgvector do corpus — a busca por similaridade no banco de verdade.

Implementa `CorpusIndex` sobre `rag.corpus_entry` (migration 0006). A ordenação
por similaridade é feita PELO BANCO, com o operador de distância de cosseno do
pgvector e o índice HNSW — não em Python sobre tudo o que foi lido.

Este é um desvio consciente da escolha do ADR 0023, que manda ler a trilha
inteira e filtrar em Python para não ter duas cópias do predicado. Aqui a razão
não vale: similaridade vetorial não é um predicado que possa divergir entre duas
implementações — é uma função matemática fechada, e o `<=>` do pgvector calcula a
mesma coisa que `cosine_similarity`. O que se ganha é o índice ANN, que é o
motivo de existir uma extensão vetorial. O teste de paridade com a implementação
de referência é o que mantém a afirmação honesta.

## O modelo entra no WHERE, sempre

Toda consulta filtra por `model_name`. Sem isso, um corpus reindexado com outro
modelo deixaria linhas de dois espaços vetoriais convivendo, e a busca devolveria
a passagem errada com um número plausível ao lado — que é pior que um erro que
estoura.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ecosfera_ai.application.rag.corpus_index import CorpusIndex, IndexedEntry, ScoredEntry
from ecosfera_ai.domain.rag.corpus import CorpusCategory, CorpusEntry

_DELETE_MODEL = text("DELETE FROM rag.corpus_entry WHERE model_name = :model_name")

_INSERT = text(
    """
    INSERT INTO rag.corpus_entry (
        entry_id, model_name, category, source, content, topic,
        cause_codes, bncc_codes, grade_band, code_verified, license, embedding
    ) VALUES (
        :entry_id, :model_name, :category, :source, :content, :topic,
        :cause_codes, :bncc_codes, :grade_band, :code_verified, :license,
        CAST(:embedding AS vector)
    )
    """
)

# `1 - (embedding <=> query)` converte a DISTÂNCIA de cosseno do pgvector em
# SIMILARIDADE, que é a grandeza que a porta expõe. Manter as duas convenções
# misturadas seria o convite clássico ao ranking invertido.
_SEARCH = """
    SELECT entry_id, category, source, content, topic, cause_codes, bncc_codes,
           grade_band, code_verified, license,
           1 - (embedding <=> CAST(:query AS vector)) AS similarity
      FROM rag.corpus_entry
     WHERE model_name = :model_name
       {category_filter}
       {cause_filter}
     ORDER BY embedding <=> CAST(:query AS vector), entry_id
     LIMIT :limit
"""


def _vector_literal(vector: Sequence[float]) -> str:
    """Formato textual que o pgvector aceita para CAST."""
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


def _row_to_scored(row: Any) -> ScoredEntry:
    return ScoredEntry(
        entry=CorpusEntry(
            entry_id=row.entry_id,
            category=CorpusCategory(row.category),
            source=row.source,
            text=row.content,
            topic=row.topic,
            cause_codes=tuple(row.cause_codes or ()),
            bncc_codes=tuple(row.bncc_codes or ()),
            grade_band=row.grade_band,
            code_verified=row.code_verified,
            license=row.license,
        ),
        similarity=float(row.similarity),
    )


class PostgresCorpusIndex:
    """`CorpusIndex` sobre pgvector."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def replace_all(self, model_name: str, entries: Sequence[IndexedEntry]) -> None:
        """Substitui a indexação DAQUELE modelo, numa transação só.

        Apagar e inserir juntos é o que torna a reindexação atômica: um corpus
        meio antigo e meio novo responderia consultas com uma mistura que ninguém
        revisou.
        """
        rows = [
            {
                "entry_id": item.entry.entry_id,
                "model_name": model_name,
                "category": item.entry.category.value,
                "source": item.entry.source,
                "content": item.entry.text,
                "topic": item.entry.topic,
                "cause_codes": list(item.entry.cause_codes),
                "bncc_codes": list(item.entry.bncc_codes),
                "grade_band": item.entry.grade_band,
                "code_verified": item.entry.code_verified,
                "license": item.entry.license,
                "embedding": _vector_literal(item.embedding),
            }
            for item in entries
        ]
        async with self._engine.begin() as conn:
            await conn.execute(_DELETE_MODEL, {"model_name": model_name})
            if rows:
                await conn.execute(_INSERT, rows)

    async def search(
        self,
        model_name: str,
        query: Sequence[float],
        *,
        limit: int,
        categories: frozenset[CorpusCategory] | None = None,
        cause_code: str | None = None,
    ) -> Sequence[ScoredEntry]:
        params: dict[str, Any] = {
            "model_name": model_name,
            "query": _vector_literal(query),
            "limit": limit,
        }
        category_filter = ""
        if categories is not None:
            params["categories"] = [category.value for category in sorted(categories)]
            category_filter = "AND category = ANY(:categories)"
        cause_filter = ""
        if cause_code is not None:
            params["cause_code"] = cause_code
            cause_filter = "AND :cause_code = ANY(cause_codes)"

        statement = text(_SEARCH.format(category_filter=category_filter, cause_filter=cause_filter))
        async with self._engine.connect() as conn:
            result = await conn.execute(statement, params)
            return tuple(_row_to_scored(row) for row in result)


def _port_conformance(engine: AsyncEngine) -> CorpusIndex:
    """Prova, em tempo de checagem de tipo, que o adaptador satisfaz a porta.

    Mesmo recurso que `postgres_event_store` usa: sem esta linha o adaptador
    poderia divergir da assinatura e o mypy nada diria, porque nada o atribui à
    porta no código de produção.
    """
    return PostgresCorpusIndex(engine)


__all__ = ["PostgresCorpusIndex"]
