"""`GeneratedExplanation` — prosa REESCRITA, e estruturalmente não um fato.

Terceiro tipo da mesma disciplina. O M6.2 separou passagem de fato; aqui se separa
TEXTO GERADO de fato, e pelo mesmo motivo levado um passo adiante: agora existe um
componente não-determinístico no caminho, e ele produz frases que *soam* como
afirmações sobre o planeta do aluno.

## A hierarquia de ancoragem, escrita no tipo

    Event Store  →  FactualContext (M6.0)  →  Explanation (M6.1)  →  aqui
                                              ^ o QUE aconteceu
    corpus       →  RetrievedPassage (M6.2)  ────────────────────────┘
                    ^ COMO se diz

O `floor_text` é a prosa do M6.1 — a fonte da verdade sobre o que aconteceu, já
auditada frase a frase. As passagens informam apenas registro e vocabulário. O
modelo REESCREVE o primeiro no registro das segundas; ele não decide o que houve,
e `verified` registra se a saída passou pela verificação de fundamentação ou se o
sistema recuou para o piso.

## Por que `fell_back` é um campo, e não um detalhe de log

Um recuo silencioso seria indistinguível de sucesso para qualquer camada acima —
e é exatamente o que o M6.4 precisa contar para saber se o modelo está ajudando.
Quem consome sabe, olhando o objeto, se está lendo o modelo ou o template.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ecosfera_ai.domain.consumers.explanation import Register
from ecosfera_ai.domain.rag.corpus import CorpusCategory

# Os campos que caracterizam um FATO derivado do Event Store. Nenhum deles pode
# aparecer aqui — `test_generated_explanation_is_not_a_fact_type` varre, com o
# mesmo rigor que o M6.2 aplicou à passagem recuperada.
FACT_BEARING_FIELDS: frozenset[str] = frozenset(
    {
        "event_id",
        "occurred_at",
        "cause_code",
        "cause_detail",
        "causation_id",
        "correlation_id",
        "participants",
        "consequences",
        "events",
        "speciations",
        "extinctions",
    }
)


@dataclass(frozen=True, slots=True)
class RegisterSource:
    """Qual passagem informou o registro, e de que categoria ela era.

    A categoria viaja junto porque o ADR 0027 mediu que a similaridade NÃO
    distingue uma regra de vocabulário da correção validada que diz o mesmo. Quem
    auditar precisa saber qual das duas entrou no prompt, e o M6.4 vai precisar
    disso para calibrar prioridade por categoria em vez de por nota.
    """

    entry_id: str
    category: CorpusCategory
    source: str
    similarity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "category": self.category.value,
            "source": self.source,
            "similarity": self.similarity,
        }


@dataclass(frozen=True, slots=True)
class DetectionCoverage:
    """QUAIS tipos de evento a verificação realmente conferiu.

    O M6.3 aprendeu, com o roteiro de fumaça, que um veredito de dois estados
    obriga "não avaliado" a se disfarçar de "reprovado". Este campo aplica a mesma
    disciplina ao outro eixo: um APROVADO não pode se passar por mais conferência
    do que houve.

    Sem isto, a lacuna que o M6.4 veio fechar seria invisível de novo — uma prosa
    inventando um `TemperatureShift` recebia exatamente o mesmo "passou" de uma
    prosa impecável, e nada no objeto distinguia as duas.
    """

    checked: frozenset[str] = frozenset()
    unchecked: frozenset[str] = frozenset()

    @property
    def is_complete(self) -> bool:
        return not self.unchecked

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": sorted(self.checked),
            "unchecked": sorted(self.unchecked),
            "complete": self.is_complete,
        }


@dataclass(frozen=True, slots=True)
class GroundingVerdict:
    """O resultado da verificação pós-geração, com o motivo por extenso.

    `reasons` existe para o M6.4: uma falha que diz apenas "reprovado" não monta
    conjunto de avaliação. Cada motivo nomeia o que foi encontrado e onde.

    ## Três estados, e não dois

    `evaluated` existe porque o roteiro de fumaça mostrou a confusão: com o modelo
    desligado, a saída dizia `veredito: reprovado` — e não houve reprovação
    alguma, não houve texto para verificar. Um booleano só obriga "não avaliado" a
    se disfarçar de "reprovado", e é justamente a diferença que o M6.4 precisa
    para não somar indisponibilidade de rede à taxa de alucinação.
    """

    passed: bool
    reasons: tuple[str, ...] = ()
    evaluated: bool = True
    coverage: DetectionCoverage = DetectionCoverage()

    @classmethod
    def not_evaluated(cls) -> GroundingVerdict:
        """Não houve geração; não há o que verificar."""
        return cls(passed=False, reasons=(), evaluated=False)

    @property
    def summary(self) -> str:
        """Como se diz o estado em uma palavra, para log e inspeção humana."""
        if not self.evaluated:
            return "não avaliado (não houve geração)"
        if not self.passed:
            return "reprovado"
        if self.coverage.is_complete:
            return "passou"
        return f"passou (cobertura parcial: {len(self.coverage.unchecked)} tipo(s) sem checagem)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "evaluated": self.evaluated,
            "reasons": list(self.reasons),
            "coverage": self.coverage.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class GeneratedExplanation:
    """O texto que chega ao aluno, com a proveniência inteira do caminho.

    `text` é o que se lê. Quando `fell_back` é verdadeiro, `text` É o
    `floor_text` — não uma versão degradada dele, e sim exatamente o piso do
    M6.1, que já era prosa correta e auditável.
    """

    planet_id: str
    register: Register
    text: str
    floor_text: str
    verdict: GroundingVerdict
    fell_back: bool
    model_name: str = ""
    register_sources: tuple[RegisterSource, ...] = ()
    # Motivo do recuo, quando houve: falha de rede, tempo esgotado, saída vazia,
    # ou reprovação na verificação. Fica separado de `verdict.reasons` porque um
    # recuo por rede não é uma reprovação de fundamentação, e contá-los juntos
    # daria ao M6.4 uma taxa de alucinação inflada por indisponibilidade.
    fallback_reason: str = ""
    slot_values: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_model_authored(self) -> bool:
        """Verdadeiro só quando o aluno está lendo o modelo, e não o template."""
        return not self.fell_back

    def to_dict(self) -> dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "register": self.register.value,
            "text": self.text,
            "floor_text": self.floor_text,
            "verdict": self.verdict.to_dict(),
            "fell_back": self.fell_back,
            "fallback_reason": self.fallback_reason,
            "model_name": self.model_name,
            "register_sources": [source.to_dict() for source in self.register_sources],
        }


__all__ = [
    "FACT_BEARING_FIELDS",
    "DetectionCoverage",
    "GeneratedExplanation",
    "GroundingVerdict",
    "RegisterSource",
]
