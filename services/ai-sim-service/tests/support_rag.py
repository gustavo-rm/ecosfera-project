"""Montagem do RAG pedagógico para os testes — sempre o corpus DE PRODUÇÃO.

O manifesto carregado é o mesmo que o serviço usa. Um corpus sintético provaria
que o mecanismo funciona e não provaria nada sobre o material que chega ao aluno
— e é o material que este marco existe para auditar.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.application.rag.corpus_index import InMemoryCorpusIndex
from ecosfera_ai.application.rag.index_corpus import IndexCorpusUseCase
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase
from ecosfera_ai.domain.rag.corpus import CorpusManifest, load_manifest
from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder

MANIFEST_PATH = Path("configs/pedagogical_corpus.yaml")


def manifest() -> CorpusManifest:
    return load_manifest(MANIFEST_PATH)


async def indexed_retriever() -> RetrievePassagesUseCase:
    """Corpus de produção indexado em memória, pronto para consulta."""
    embedder = DeterministicEmbedder()
    index = InMemoryCorpusIndex()
    await IndexCorpusUseCase(embedder, index).execute(manifest())
    return RetrievePassagesUseCase(embedder, index)
