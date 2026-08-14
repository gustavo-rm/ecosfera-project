"""Adaptador de produção do embedding — sentence-transformers, multilíngue.

## O modelo escolhido, e por quê

`paraphrase-multilingual-mpnet-base-v2`: 768 dimensões (casa com a coluna
`vector(768)` das migrations 0001/0006) e treinado em multilíngue, incluindo
português. A escolha do idioma não é preferência: este corpus é material
curricular brasileiro, e registro e vocabulário só funcionam se indexados na
língua-alvo. Um modelo só-inglês recuperaria por tradução implícita e erraria
justamente nos termos que importam ("especiação", "aptidão", "ancestral comum").

## O que está VERIFICADO e o que não está

Verificado: a lógica deste adaptador — a checagem de dimensão, o nome do modelo
que viaja com cada vetor, a normalização e o formato de saída — exercitada por
teste com um carregador injetado.

**Não verificado neste ambiente:** a chamada real à biblioteca com pesos
baixados. A política de rede deste ambiente nega `huggingface.co` (403 no CONNECT),
e o CI deste serviço sincroniza sem o extra `ai`. Portanto nenhuma execução com o
modelo de verdade aconteceu aqui, e isso está declarado no ADR 0027 em vez de
implícito — a implementação de referência (`DeterministicEmbedder`) é a que roda
no CI e a que sustenta os testes de integração com pgvector.

## Por que o carregador é injetável

`loader` existe para que a lógica acima seja testável sem rede e sem 2 GB de
dependência. Não é um gancho de teste pendurado na produção: é a mesma inversão
que este serviço usa em toda porta, e o padrão é o único jeito de o adaptador ter
cobertura real num ambiente que não pode baixar pesos.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from ecosfera_ai.domain.rag.embedding import EMBEDDING_DIMENSIONS

# Multilíngue e 768-dim — ver a nota de módulo sobre a escolha.
DEFAULT_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"


class _SentenceTransformerLike(Protocol):
    """O mínimo que este adaptador usa da biblioteca."""

    def get_sentence_embedding_dimension(self) -> int | None: ...

    def encode(self, sentences: list[str], **kwargs: Any) -> Any: ...


class EmbeddingDimensionMismatchError(ValueError):
    """O modelo carregado não tem a dimensão que o schema espera.

    Falha na CONSTRUÇÃO, antes de qualquer escrita. Deixar passar produziria
    erro linha a linha no `INSERT` — ou, pior, um índice pela metade — quando a
    causa real é a escolha do modelo.
    """


def _default_loader(model_name: str) -> _SentenceTransformerLike:
    """Import preguiçoso: o serviço sobe sem o extra `ai` instalado."""
    from sentence_transformers import SentenceTransformer

    loaded: _SentenceTransformerLike = SentenceTransformer(model_name)
    return loaded


class SentenceTransformerEmbedder:
    """`EmbeddingModel` sobre sentence-transformers."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        *,
        loader: Callable[[str], _SentenceTransformerLike] | None = None,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self._model = (loader or _default_loader)(model_name)

        declared = self._model.get_sentence_embedding_dimension()
        if declared is not None and declared != dimensions:
            raise EmbeddingDimensionMismatchError(
                f"o modelo {model_name!r} produz vetores de {declared} dimensões e o "
                f"schema guarda {dimensions}; escolha um modelo compatível ou migre a coluna"
            )

    @property
    def name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Codifica em lote, normalizado — a similaridade vira produto interno.

        `normalize_embeddings=True` é o que alinha este adaptador à convenção da
        implementação de referência. Sem ele os dois produziriam escalas
        diferentes de similaridade, e um limiar calibrado sobre um não valeria
        para o outro.
        """
        if not texts:
            return ()
        encoded = self._model.encode(list(texts), normalize_embeddings=True)
        vectors = tuple(tuple(float(value) for value in row) for row in encoded)
        for vector in vectors:
            if len(vector) != self._dimensions:
                raise EmbeddingDimensionMismatchError(
                    f"o modelo {self._model_name!r} devolveu {len(vector)} dimensões, "
                    f"e não {self._dimensions}"
                )
        return vectors


__all__ = [
    "DEFAULT_MODEL_NAME",
    "EmbeddingDimensionMismatchError",
    "SentenceTransformerEmbedder",
]
