"""A EXPLICAÇÃO renderizada — prosa para o aluno, com a origem de cada afirmação.

O M6.0 entregou o fato neutro; este módulo entrega a frase. É a Visão Educacional
do ADR-ARCH-0002 (Correção 1) finalmente sendo RENDERIZADA pelo consumidor: o
Engine dá o esqueleto causal como dado, o dossiê o organiza, e aqui ele vira
língua portuguesa.

## O piso de qualidade

Esta subetapa existe para provar, ANTES de qualquer LLM, que o dossiê do M6.0 já
é rico o bastante para produzir explicação correta por template. O que o M6.3
gerar terá de ser pelo menos tão bom quanto isto — e "tão bom" aqui tem um
critério mecânico, não uma impressão: cada afirmação da prosa é rastreável a um
campo do dossiê que a originou.

## Por que um template também alucina

Não ter LLM não é imunidade. Um template que diga "a espécie não conseguiu se
adaptar" numa extinção catastrófica está afirmando algo que o dossiê **não
contém** — e a criança que o lê fica com a concepção equivocada exatamente como
ficaria se um modelo o tivesse escrito. A diferença entre template e LLM é a
facilidade de auditar, não a existência do risco.

Daí o `Grounding`: todo fato renderizado carrega o `event_id` de onde saiu e os
campos que preencheram seus slots. Um fato sem origem não é explicação — é
invenção com boa gramática.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ecosfera_ai.domain.consumers.factual_context import ContextSlice
from ecosfera_ai.shared_kernel.events import SimulationTime


class Register(StrEnum):
    """Nível de leitura da prosa — a costura de faixa etária do M6.1.

    Duas variantes, e deliberadamente não um sistema de diferenciação: o M6.1
    decide a COSTURA, e o M6.3 a estende acrescentando linhas ao YAML, sem tocar
    em assinatura alguma.

    `SIMPLE` existe hoje só para os três fatos de maior risco pedagógico — as
    duas famílias de extinção e a especiação —, que são justamente aqueles em que
    uma frase longa demais faz o aluno perder a lição. Nos demais o renderizador
    cai para `STANDARD`, e isso é decisão: uma frase padrão correta é melhor que
    uma simplificação improvisada em tempo de execução.
    """

    STANDARD = "standard"
    SIMPLE = "simple"


@dataclass(frozen=True, slots=True)
class Grounding:
    """De onde a afirmação saiu — o que separa explicação de invenção.

    `event_id` é o evento do dossiê que originou o fato. `fields` são os caminhos
    (pontilhados) que preencheram os slots do template, resolvíveis contra o
    dossiê. `test_every_claim_is_grounded_in_context` percorre os dois.

    `event_id` é None num caso só, e ele é legítimo: a frase de período tranquilo
    não afirma nada sobre um evento — afirma algo sobre a FATIA INTEIRA (que ela
    não tem acontecimento notável). A origem dessa afirmação é o dossiê como um
    todo, e é isso que `fields` registra.
    """

    event_id: str | None
    fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"event_id": self.event_id, "fields": list(self.fields)}


@dataclass(frozen=True, slots=True)
class ExplainedFact:
    """Uma frase, o template que a produziu e a origem de cada valor nela."""

    template_id: str
    register: Register
    text: str
    occurred_at: SimulationTime
    grounding: Grounding
    # Os valores efetivamente substituídos nos slots. Ficam explícitos para que a
    # verificação de ancoragem seja MECÂNICA: todo número que aparece na frase
    # tem de estar aqui, e todo valor daqui tem de ser derivável do dossiê.
    slots: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "register": self.register.value,
            "text": self.text,
            "tick": self.occurred_at.tick,
            "era": self.occurred_at.era,
            "grounding": self.grounding.to_dict(),
            "slots": dict(self.slots),
        }


@dataclass(frozen=True, slots=True)
class Explanation:
    """O que o aluno lê, mais tudo de que se precisa para auditar a frase.

    `summary` é EXATAMENTE a junção dos textos de `facts`, em ordem cronológica,
    e não um resumo por cima deles. A distinção é a que impede a alucinação mais
    provável de um renderizador: um resumo que sintetiza tem de afirmar algo que
    nenhum fato isolado afirma, e esse algo não teria origem no dossiê.
    """

    planet_id: str
    slice: ContextSlice
    register: Register
    facts: tuple[ExplainedFact, ...] = ()
    summary: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.facts

    def to_dict(self) -> dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "slice": self.slice.to_dict(),
            "register": self.register.value,
            "summary": self.summary,
            "facts": [fact.to_dict() for fact in self.facts],
        }


__all__ = ["ExplainedFact", "Explanation", "Grounding", "Register"]
