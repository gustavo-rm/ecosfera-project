"""Casos de uso do RAG pedagógico (M6.2): indexar o corpus e recuperar registro.

Offline e read-side. Não tocam no laço de simulação, no world-state nem nos
Engines — e, nesta subetapa, não geram texto algum: o retriever devolve
passagens, quem compõe é o M6.3.
"""

from __future__ import annotations

from ecosfera_ai.application.rag.corpus_index import (
    CorpusIndex,
    IndexedEntry,
    InMemoryCorpusIndex,
    ScoredEntry,
)
from ecosfera_ai.application.rag.index_corpus import (
    EmbeddingModelMismatchError,
    IndexCorpusUseCase,
    IndexReport,
)
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase, passages_to_dicts

__all__ = [
    "CorpusIndex",
    "EmbeddingModelMismatchError",
    "InMemoryCorpusIndex",
    "IndexCorpusUseCase",
    "IndexReport",
    "IndexedEntry",
    "RetrievePassagesUseCase",
    "ScoredEntry",
    "passages_to_dicts",
]
