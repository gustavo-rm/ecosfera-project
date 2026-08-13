"""Mesmo texto e mesmo modelo produzem o MESMO vetor — sempre, em qualquer processo.

Determinismo aqui não é elegância: é a condição para o índice ser auditável. Se o
mesmo texto gerasse vetores diferentes entre execuções, reindexar mudaria
silenciosamente o que o Tutor recupera, e ninguém conseguiria reproduzir a
recuperação que gerou determinada explicação.

A armadilha concreta em Python é o `hash()` embutido, que é ALEATORIZADO por
processo (PYTHONHASHSEED). Um embedder de hashing escrito com ele passaria em
qualquer teste dentro de um mesmo processo e produziria índices diferentes a cada
reinício do serviço. Por isso o vetor sai de `blake2b`, e por isso um dos testes
abaixo roda num SUBPROCESSO — dentro do mesmo processo o defeito seria invisível.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ecosfera_ai.domain.rag.embedding import (
    DETERMINISTIC_MODEL_NAME,
    EMBEDDING_DIMENSIONS,
    DeterministicEmbedder,
    cosine_similarity,
    normalize_tokens,
)

SERVICE_ROOT = Path(__file__).resolve().parents[2]
TEXT = "Duas linhagens compartilham um ancestral comum que sofreu especiação."


def test_the_same_text_yields_the_same_vector() -> None:
    embedder = DeterministicEmbedder()
    assert embedder.embed([TEXT]) == embedder.embed([TEXT])


def test_two_embedders_agree() -> None:
    assert DeterministicEmbedder().embed([TEXT]) == DeterministicEmbedder().embed([TEXT])


def test_the_vector_survives_a_fresh_process() -> None:
    """O teste que pega o `hash()` aleatorizado — invisível dentro de um processo."""
    probe = (
        "from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder;"
        f"print(DeterministicEmbedder().embed([{TEXT!r}])[0][:8])"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", probe],
            cwd=SERVICE_ROOT,
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin", "PYTHONHASHSEED": seed},
        ).stdout
        for seed in ("0", "1", "12345")
    }
    assert len(runs) == 1, f"o vetor mudou com o PYTHONHASHSEED: {runs}"


def test_the_batch_is_just_the_items() -> None:
    """Codificar em lote não pode depender de quem está junto no lote."""
    embedder = DeterministicEmbedder()
    other = "A aptidão é contextual."
    batch = embedder.embed([TEXT, other])
    assert batch[0] == embedder.embed([TEXT])[0]
    assert batch[1] == embedder.embed([other])[0]


def test_the_vector_has_the_dimension_the_schema_stores() -> None:
    vector = DeterministicEmbedder().embed([TEXT])[0]
    assert len(vector) == EMBEDDING_DIMENSIONS


def test_the_model_name_travels_with_the_embedder() -> None:
    """É o nome gravado por linha, e o que impede comparar espaços diferentes."""
    assert DeterministicEmbedder().name == DETERMINISTIC_MODEL_NAME


def test_an_empty_batch_is_empty() -> None:
    assert DeterministicEmbedder().embed([]) == ()


def test_a_text_without_tokens_yields_the_null_vector() -> None:
    """Sem token não há direção. Inventar uma faria o vazio parecer com algo."""
    vector = DeterministicEmbedder().embed(["!!! ... ???"])[0]
    assert set(vector) == {0.0}
    assert cosine_similarity(vector, DeterministicEmbedder().embed([TEXT])[0]) == 0.0


# --- A normalização de token, que é onde o português entra --------------------


def test_accents_are_folded_so_the_query_matches_without_them() -> None:
    """ "especiação" e "especiacao" caem no mesmo token — um `cause_code` chega sem acento."""
    assert normalize_tokens("Especiação") == normalize_tokens("especiacao")


def test_very_short_tokens_are_dropped() -> None:
    """Artigos e preposições são ruído em toda entrada e sinal em nenhuma consulta."""
    assert normalize_tokens("o a de em ao se") == []
    assert "co2" in normalize_tokens("o CO2 do ar")


def test_identical_texts_are_maximally_similar() -> None:
    embedder = DeterministicEmbedder()
    vector = embedder.embed([TEXT])[0]
    assert cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_unrelated_texts_are_far_apart() -> None:
    embedder = DeterministicEmbedder()
    first = embedder.embed(["ancestral comum linhagens especiação"])[0]
    second = embedder.embed(["circulação oceânica aquecimento desigual"])[0]
    assert cosine_similarity(first, second) < 0.2
