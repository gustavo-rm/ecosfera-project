"""A porta de embedding e a implementação de REFERÊNCIA — determinística.

Mesma escolha que este serviço já fez para persistência (in-memory × Postgres),
fila (inline × ARQ) e LLM (nulo × Ollama): o modelo de embedding é uma PORTA
com duas implementações, e a de referência é a que roda em qualquer lugar.

## Por que a de referência não é conveniência, e sim requisito

O CI deste serviço roda `uv sync --extra sim --extra infra --group dev` — **sem o
extra `ai`**. Um teste de pgvector que dependesse de `sentence-transformers`
PULARIA no CI, e um pulo silencioso é precisamente o que a política de zero-skip
deste repositório existe para impedir (`docs/ci-verification-matrix.md`). A
implementação de referência é o que torna a integração com o banco verificável
onde ela precisa ser verificada.

## O que ela é, honestamente: LÉXICA, não semântica

`DeterministicEmbedder` projeta tokens normalizados em dimensões fixas por hash
estável (`blake2b`), e normaliza o vetor. A similaridade de cosseno resultante
mede **sobreposição de vocabulário**, não proximidade de sentido: uma consulta
por "especiação" encontra as entradas que falam de especiação porque a palavra
está lá, e não porque o modelo entende o conceito.

Isso é suficiente para o M6.2 — que entrega INFRAESTRUTURA de recuperação e a
prova de que ela devolve a entrada certa — e é insuficiente para o produto final.
O adaptador semântico (`SentenceTransformerEmbedder`) é a implementação de
produção. Declarar a diferença aqui é o que impede alguém de medir a qualidade do
Tutor contra a linha de base errada.

### Duas limitações medidas, e não deduzidas

**Viés de comprimento.** O cosseno sobre saco-de-palavras favorece entradas
CURTAS: cada token de um texto curto pesa mais depois da normalização L2. O
roteiro de fumaça mostrou isso de forma concreta — a regra do ancestral comum
aparecia em 4º lugar numa consulta que continha as palavras "ancestral comum",
porque ela carregava, além da regra, o parágrafo que a justificava. A correção
foi no CORPUS e não no algoritmo: a entrada voltou a ser a regra curta e citável
que o manifesto sempre pediu (a justificativa vive no ADR citado como origem), e
ela subiu para 1º com 0,42. Entradas longas continuam em desvantagem, e é por
isso que o manifesto insiste em frases curtas.

**Similaridade não é comparável entre consultas de formatos diferentes.** Uma
consulta de dois tokens contra um texto longo produz número baixo (0,10) mesmo
sendo a resposta certa; uma consulta de quatro tokens bem casada produz 0,60. O
ranking DENTRO de uma consulta é significativo; o valor absoluto entre consultas
distintas não é. Quem for calibrar um corte de confiança no M6.4 precisa saber
disso antes de escolher um limiar único.

## Por que o nome do modelo viaja com cada vetor

Similaridade entre vetores de modelos diferentes não significa nada — são espaços
distintos. Se o corpus for reindexado com outro modelo e sobrarem linhas do
anterior, uma consulta compararia maçãs com laranjas e devolveria a passagem
errada com um número plausível ao lado. Por isso o nome do modelo é coluna, o
retriever filtra por ele, e trocar de modelo é auditável em vez de silencioso.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

# Dimensão fixada pela migration 0001 (`vector(768)`). O adaptador de produção
# tem de casar com ela — um modelo de outra dimensão falha alto na construção,
# em vez de gravar vetores que o banco recusaria linha a linha.
EMBEDDING_DIMENSIONS = 768

DETERMINISTIC_MODEL_NAME = "ecosfera-deterministic-v1"

_TOKEN = re.compile(r"[a-z0-9]+")

# Tokens de uma ou duas letras são, em português, quase só artigos, preposições e
# conjunções ("o", "a", "de", "em", "ao", "se"). Eles aparecem em toda entrada e
# em nenhuma consulta útil, e cada um deles é mais uma chance de colisão de hash
# contra um token que importa. Cortá-los é o filtro de ruído mais barato que
# existe aqui; "co2" e "gas" têm três caracteres e sobrevivem.
MIN_TOKEN_LENGTH = 3

# Quantas dimensões cada token ocupa. NÃO é ajuste fino: é o que faz o sinal
# vencer a colisão num corpus pequeno.
#
# Com uma dimensão por token, um token da consulta que colida com um token não
# relacionado de um documento curto produz exatamente a mesma contribuição que um
# acerto de verdade — e o documento curto ganha, porque a normalização L2 dá peso
# maior a cada token dele. Foi o que o roteiro de fumaça mostrou: uma consulta
# sobre especiação trouxe no topo a entrada sobre teias alimentares.
#
# Com três dimensões e sinais independentes, um acerto real soma nas TRÊS, e uma
# colisão acidental costuma coincidir em uma só. O sinal cresce ~3x contra o
# ruído sem que o vetor deixe de ser função pura do texto.
HASHES_PER_TOKEN = 3


class EmbeddingModel(Protocol):
    """A porta. Quem indexa e quem consulta dependem DESTA assinatura.

    `name` não é decorativo: ele é gravado com cada vetor e é o que impede a
    comparação entre espaços diferentes.
    """

    @property
    def name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]: ...


def normalize_tokens(text: str) -> list[str]:
    """Minúsculas, sem acento, só alfanumérico.

    A dobra de acentos é o que faz "especiação" e "especiacao" caírem no mesmo
    token — necessário num corpus em português consultado por chaves que às vezes
    chegam sem acento (um `cause_code`, por exemplo).
    """
    folded = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(char for char in folded if not unicodedata.combining(char))
    return [token for token in _TOKEN.findall(stripped) if len(token) >= MIN_TOKEN_LENGTH]


def _projections_of(token: str, dimensions: int) -> list[tuple[int, float]]:
    """As `HASHES_PER_TOKEN` posições (dimensão, sinal) que o token ocupa.

    O sinal por hash é o truque padrão com sinal: dois tokens que colidem numa
    dimensão colidem com sinais independentes e tendem a se cancelar, em vez de
    somar sempre.
    """
    projections: list[tuple[int, float]] = []
    for probe in range(HASHES_PER_TOKEN):
        digest = hashlib.blake2b(f"{probe}:{token}".encode(), digest_size=9).digest()
        dimension = int.from_bytes(digest[:8], "big") % dimensions
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        projections.append((dimension, sign))
    return projections


@dataclass(frozen=True, slots=True)
class DeterministicEmbedder:
    """Projeção léxica estável — a implementação de referência.

    Determinística por construção: o mesmo texto produz o mesmo vetor em qualquer
    máquina, qualquer processo, qualquer ordem de chamada. Nenhum `hash()` do
    Python (que é aleatorizado por processo) participa disso.
    """

    dimensions: int = EMBEDDING_DIMENSIONS

    @property
    def name(self) -> str:
        return DETERMINISTIC_MODEL_NAME

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._embed_one(text) for text in texts)

    def _embed_one(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        for token in normalize_tokens(text):
            for dimension, sign in _projections_of(token, self.dimensions):
                vector[dimension] += sign
        return _l2_normalized(vector)


def _l2_normalized(vector: list[float]) -> tuple[float, ...]:
    """Normaliza para que a similaridade de cosseno vire produto interno.

    O vetor nulo (texto sem token algum) permanece nulo: normalizá-lo exigiria
    dividir por zero, e inventar uma direção arbitrária faria um texto vazio
    parecer parecido com alguma coisa.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return tuple(vector)
    return tuple(value / norm for value in vector)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Similaridade de cosseno entre dois vetores de mesma dimensão."""
    if len(left) != len(right):
        raise ValueError(
            f"vetores de dimensões diferentes ({len(left)} e {len(right)}) — "
            "quase sempre o sinal de que dois modelos foram misturados"
        )
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


__all__ = [
    "DETERMINISTIC_MODEL_NAME",
    "EMBEDDING_DIMENSIONS",
    "DeterministicEmbedder",
    "EmbeddingModel",
    "cosine_similarity",
    "normalize_tokens",
]
