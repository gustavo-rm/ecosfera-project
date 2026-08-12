"""Modelos de domínio do feedback causal. Puros: sem FastAPI, sem I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Direction(StrEnum):
    """Sentido da variação de uma grandeza.

    `NONE` entra no M6.1 e não é um terceiro sentido: é a AUSÊNCIA de afirmação
    direcional. Um passo narrado a partir de um evento nem sempre mede uma
    grandeza que sobe ou desce — "uma população ancestral se dividiu em duas
    linhagens" não tem direção, e uma especiação não é um aumento de nada.

    Antes disso, o único jeito de preencher o campo seria escolher `UP` por
    convenção — e uma direção escolhida por convenção é uma afirmação sem origem
    no Event Store, chegando à resposta da API como se fosse dado. É exatamente
    a alucinação que o M6 existe para tornar impossível, e ela não precisa de um
    LLM para acontecer.
    """

    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Observation:
    """Uma variável observada do estado do planeta e sua variação no tick.

    `variable` usa a linguagem ubíqua do domínio (ex.: 'co2', 'temperature').
    `delta` é a variação relativa (adimensional) produzida pelo motor de simulação.
    """

    variable: str
    delta: float

    @property
    def direction(self) -> Direction:
        return Direction.UP if self.delta >= 0 else Direction.DOWN


@dataclass(frozen=True, slots=True)
class CausalStep:
    """Um passo rastreável da cadeia causal (RF-039: 'por que isso aconteceu')."""

    cause: str
    effect: str
    direction: Direction
    rule_id: str
    explanation: str


@dataclass(frozen=True, slots=True)
class CausalExplanation:
    """Explicação causal apropriada à idade, ancorada em dados reais (RF-033/034/039).

    No MVP é gerada por regras determinísticas; no Inc 6 o mesmo objeto pode ser
    enriquecido pelo LLM+RAG — o contrato de saída não muda (estabilidade).
    """

    planet_id: str
    summary: str
    chain: list[CausalStep] = field(default_factory=list)
    grounded: bool = True  # False quando o LLM extrapola sem evidência (Inc 6)
    source: str = "rules"  # 'rules' | 'llm+rag'
