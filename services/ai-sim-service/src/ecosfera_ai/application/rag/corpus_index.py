"""A porta de armazenamento do corpus indexado, e a implementação de referência.

Mesmo desenho das outras portas deste serviço: uma assinatura, duas
implementações que passam os MESMOS testes — em memória e sobre pgvector. É o
que torna a de referência utilizável como espelho do adaptador real, em vez de
uma simplificação que ninguém compara com nada.

## O modelo faz parte da chave, sempre

Toda operação carrega o nome do modelo de embedding. Não é metadado: comparar
vetores de modelos diferentes é comparar espaços distintos, e o resultado é um
número plausível ao lado da passagem errada — que é pior que um erro visível.
Indexar substitui apenas as linhas DAQUELE modelo, e consultar filtra por ele.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ecosfera_ai.domain.rag.corpus import CorpusCategory, CorpusEntry
from ecosfera_ai.domain.rag.embedding import cosine_similarity


@dataclass(frozen=True, slots=True)
class IndexedEntry:
    """Uma entrada do corpus com o vetor que a representa."""

    entry: CorpusEntry
    embedding: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ScoredEntry:
    """Uma entrada recuperada e o quanto ela se parece com a consulta."""

    entry: CorpusEntry
    similarity: float


class CorpusIndex(Protocol):
    """Porta de escrita e leitura do corpus indexado.

    Assíncrona como todas as portas de persistência deste serviço — o adaptador
    real é o Postgres, e uma porta síncrona forçaria ou a bloquear o event loop
    ou a não implementar a porta (a mesma razão registrada no ADR 0023).
    """

    async def replace_all(self, model_name: str, entries: Sequence[IndexedEntry]) -> None: ...

    async def search(
        self,
        model_name: str,
        query: Sequence[float],
        *,
        limit: int,
        categories: frozenset[CorpusCategory] | None = None,
        cause_code: str | None = None,
    ) -> Sequence[ScoredEntry]: ...


@dataclass(slots=True)
class InMemoryCorpusIndex:
    """Corpus em memória — a implementação de referência.

    Guarda POR MODELO, e não numa lista só. Um único balde não conseguiria sequer
    expressar a mistura entre modelos, e o teste que a proíbe passaria por não
    haver o que misturar — o mesmo raciocínio que fez o `InMemoryEventQuery`
    guardar trilhas por planeta (ADR 0023).
    """

    _by_model: dict[str, list[IndexedEntry]] | None = None

    def __post_init__(self) -> None:
        if self._by_model is None:
            self._by_model = {}

    @property
    def _store(self) -> dict[str, list[IndexedEntry]]:
        assert self._by_model is not None
        return self._by_model

    async def replace_all(self, model_name: str, entries: Sequence[IndexedEntry]) -> None:
        """Substitui a indexação DAQUELE modelo — as dos outros ficam intactas."""
        self._store[model_name] = list(entries)

    async def search(
        self,
        model_name: str,
        query: Sequence[float],
        *,
        limit: int,
        categories: frozenset[CorpusCategory] | None = None,
        cause_code: str | None = None,
    ) -> Sequence[ScoredEntry]:
        scored = [
            ScoredEntry(entry=item.entry, similarity=cosine_similarity(query, item.embedding))
            for item in self._store.get(model_name, [])
            if _matches(item.entry, categories, cause_code)
        ]
        return tuple(sorted(scored, key=_rank_key)[:limit])


def _matches(
    entry: CorpusEntry,
    categories: frozenset[CorpusCategory] | None,
    cause_code: str | None,
) -> bool:
    if categories is not None and entry.category not in categories:
        return False
    return cause_code is None or cause_code in entry.cause_codes


def _rank_key(scored: ScoredEntry) -> tuple[float, str]:
    """Maior similaridade primeiro; o id desempata.

    O desempate não é detalhe: sem ele, duas entradas de similaridade idêntica
    sairiam em ordem de inserção, e o mesmo corpus devolveria rankings diferentes
    conforme a ordem de indexação.
    """
    return (-scored.similarity, scored.entry.entry_id)


__all__ = [
    "CorpusIndex",
    "InMemoryCorpusIndex",
    "IndexedEntry",
    "ScoredEntry",
]
