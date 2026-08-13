"""Modelos puros do RAG pedagógico (M6.2) — REGISTRO, nunca fato.

Este pacote carrega a linguagem que o Tutor usa, e a garantia de que ela não pode
ser confundida com o que aconteceu no planeta do aluno. O fato vive em
`domain/consumers` (M6.0/M6.1) e vem do Event Store; aqui vive só a forma de
dizer.

Fica em `domain/rag/` — e não no pacote `rag/` de topo que o esqueleto do Inc 0
reservou — pela mesma razão registrada no ADR 0025 para os consumidores: o que a
Spec §1 pede é a FRONTEIRA, e ela é verificada pelo `import-linter` sobre a
estratificação hexagonal que este serviço de fato usa.
"""

from __future__ import annotations

from ecosfera_ai.domain.rag.corpus import (
    CorpusCategory,
    CorpusEntry,
    CorpusManifest,
    MissingProvenanceError,
    load_manifest,
)
from ecosfera_ai.domain.rag.embedding import (
    DETERMINISTIC_MODEL_NAME,
    EMBEDDING_DIMENSIONS,
    DeterministicEmbedder,
    EmbeddingModel,
    cosine_similarity,
)
from ecosfera_ai.domain.rag.passage import FACT_BEARING_FIELDS, RetrievedPassage

__all__ = [
    "DETERMINISTIC_MODEL_NAME",
    "EMBEDDING_DIMENSIONS",
    "FACT_BEARING_FIELDS",
    "CorpusCategory",
    "CorpusEntry",
    "CorpusManifest",
    "DeterministicEmbedder",
    "EmbeddingModel",
    "MissingProvenanceError",
    "RetrievedPassage",
    "cosine_similarity",
    "load_manifest",
]
