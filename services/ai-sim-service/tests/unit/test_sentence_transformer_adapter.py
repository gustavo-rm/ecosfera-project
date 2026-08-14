"""O adaptador de produção — lógica verificada, chamada real NÃO verificada aqui.

Honestidade sobre o que este arquivo prova e o que ele não prova.

**Prova:** a checagem de dimensão contra o schema, o nome do modelo que viaja com
cada vetor, o formato de saída e a recusa de um modelo incompatível. Tudo isso é
lógica do adaptador, e é exercitado injetando um carregador de teste.

**Não prova:** que `SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")`
funciona. A política de rede deste ambiente nega `huggingface.co` (403 no CONNECT)
e o CI sincroniza sem o extra `ai`, então nenhuma execução com pesos reais
aconteceu. Isso está declarado no ADR 0027 e aqui — em vez de implícito num teste
que pularia em silêncio.

A inversão do carregador é o que torna a primeira lista possível. Sem ela, o
adaptador seria código que ninguém consegue executar em lugar nenhum — a família
de defeito que este serviço já pagou duas vezes.
"""

from __future__ import annotations

from typing import Any

import pytest

from ecosfera_ai.domain.rag.embedding import EMBEDDING_DIMENSIONS
from ecosfera_ai.infrastructure.embeddings.sentence_transformer import (
    DEFAULT_MODEL_NAME,
    EmbeddingDimensionMismatchError,
    SentenceTransformerEmbedder,
)


class _FakeModel:
    """O mínimo da biblioteca que o adaptador usa."""

    def __init__(self, dimensions: int | None = EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions
        self.calls: list[dict[str, Any]] = []

    def get_sentence_embedding_dimension(self) -> int | None:
        return self._dimensions

    def encode(self, sentences: list[str], **kwargs: Any) -> Any:
        self.calls.append({"sentences": sentences, **kwargs})
        return [[0.1] * (self._dimensions or EMBEDDING_DIMENSIONS) for _ in sentences]


def _embedder(model: _FakeModel) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(loader=lambda _name: model)


def test_the_default_model_is_multilingual_and_768_dimensional() -> None:
    """A escolha não é preferência: o corpus é português e a coluna guarda 768."""
    assert "multilingual" in DEFAULT_MODEL_NAME
    assert "mpnet-base" in DEFAULT_MODEL_NAME


def test_the_model_name_is_reported_as_the_embedding_model() -> None:
    """É o nome gravado por linha — o que impede comparar dois espaços vetoriais."""
    embedder = SentenceTransformerEmbedder("modelo-x", loader=lambda _n: _FakeModel())
    assert embedder.name == "modelo-x"
    assert embedder.dimensions == EMBEDDING_DIMENSIONS


def test_a_model_of_the_wrong_dimension_is_refused_at_construction() -> None:
    """Falha ANTES de qualquer escrita, e não linha a linha no INSERT."""
    with pytest.raises(EmbeddingDimensionMismatchError, match="384"):
        SentenceTransformerEmbedder(loader=lambda _n: _FakeModel(dimensions=384))


def test_a_model_that_does_not_declare_its_dimension_is_accepted() -> None:
    """Nem toda implementação declara; a checagem por vetor abaixo continua valendo."""
    embedder = _embedder(_FakeModel(dimensions=None))
    assert embedder.dimensions == EMBEDDING_DIMENSIONS


class _RenamedModel(_FakeModel):
    """A biblioteca depois da renomeação: só o nome NOVO existe."""

    get_sentence_embedding_dimension = None  # type: ignore[assignment]

    def get_embedding_dimension(self) -> int | None:
        return self._dimensions


def test_either_name_of_the_dimension_method_is_accepted() -> None:
    """A `sentence-transformers` renomeou o método; os dois nomes valem.

    Achado ao rodar o modelo DE VERDADE no CI, e invisível para todo teste com
    carregador injetado até este: o falso implementava justamente o nome que o
    adaptador pedia, então a dupla concordava sozinha enquanto a biblioteca real
    já avisava `FutureWarning`.

    Fixar um nome só faria a checagem de dimensão sumir numa atualização de
    dependência — e é ela que impede vetores do tamanho errado de chegarem ao
    `INSERT`. Por isso a contraprova é o modelo que só tem o nome NOVO.
    """
    embedder = SentenceTransformerEmbedder(loader=lambda _n: _RenamedModel())
    assert embedder.dimensions == EMBEDDING_DIMENSIONS

    with pytest.raises(EmbeddingDimensionMismatchError, match="384"):
        SentenceTransformerEmbedder(loader=lambda _n: _RenamedModel(dimensions=384))


def test_the_encoding_is_normalized_so_the_two_adapters_share_a_scale() -> None:
    """Sem normalizar, um limiar calibrado num adaptador não valeria no outro."""
    model = _FakeModel()
    _embedder(model).embed(["texto"])
    assert model.calls[0]["normalize_embeddings"] is True


def test_the_texts_are_encoded_in_one_batch() -> None:
    model = _FakeModel()
    _embedder(model).embed(["a primeira", "a segunda"])
    assert model.calls == [{"sentences": ["a primeira", "a segunda"], "normalize_embeddings": True}]


def test_an_empty_batch_never_touches_the_model() -> None:
    model = _FakeModel()
    assert _embedder(model).embed([]) == ()
    assert model.calls == []


def test_the_output_is_a_tuple_of_float_tuples() -> None:
    vectors = _embedder(_FakeModel()).embed(["um", "dois"])
    assert len(vectors) == 2
    assert all(len(vector) == EMBEDDING_DIMENSIONS for vector in vectors)
    assert all(isinstance(value, float) for value in vectors[0])


def test_a_vector_of_the_wrong_size_is_refused_at_encoding_time() -> None:
    """A segunda rede: o modelo declarou uma dimensão e devolveu outra."""

    class _Lying(_FakeModel):
        def encode(self, sentences: list[str], **kwargs: Any) -> Any:
            return [[0.1] * 42 for _ in sentences]

    with pytest.raises(EmbeddingDimensionMismatchError, match="42"):
        _embedder(_Lying()).embed(["texto"])


def test_the_adapter_satisfies_the_embedding_port() -> None:
    """Conformidade com a porta — o mesmo recurso que `_port_conformance` usa."""
    from ecosfera_ai.domain.rag.embedding import EmbeddingModel

    port: EmbeddingModel = _embedder(_FakeModel())
    assert port.name == DEFAULT_MODEL_NAME


def test_the_library_is_imported_lazily() -> None:
    """O serviço sobe sem o extra `ai`: o import mora dentro do carregador padrão."""
    import ast
    from pathlib import Path

    source = Path("src/ecosfera_ai/infrastructure/embeddings/sentence_transformer.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    top_level = {
        node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(name.startswith("sentence_transformers") for name in top_level), (
        "a biblioteca é importada no topo e o serviço deixaria de subir sem o extra `ai`"
    )
