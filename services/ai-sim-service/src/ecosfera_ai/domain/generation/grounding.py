"""A verificação PÓS-GERAÇÃO — o portão anti-alucinação do M6.3.

O M6.1 podia afirmar fundamentação por construção: a frase saía de um template, e
todo valor nela vinha de um slot preenchido pelo dossiê. Um modelo generativo
apaga essa garantia. O que resta é conferir a saída DEPOIS, contra a mesma fonte
que o template usava.

## O que se confere, e por que estas três coisas

**Números.** Todo numeral da prosa gerada tem de aparecer no piso do M6.1. A
verificação é forte e não tem falso positivo: uma reescrita fiel pode OMITIR um
número, nunca acrescentar um. É o herdeiro direto da regra 3 do
`test_every_claim_is_grounded_in_context`, e pega a alucinação mais comum de um
modelo pequeno — inventar uma quantidade plausível.

**Formulação proibida.** A lista canônica do BIO-005 e a da aptidão absoluta
(Q5), as MESMAS que guardam os templates e o código-fonte desde a Fase 0. Um
modelo que escreva "a espécie desenvolveu resistência" ensina Lamarckismo com
gramática impecável, e nada além desta conferência o impediria.

**Acontecimento inventado.** Se a prosa fala de um meteoro e o dossiê daquele
planeta não tem `MeteorImpact`, o modelo acrescentou um fato. É a pior falha que
este desenho admite: fluente, plausível, e falsa sobre o planeta daquela criança.

## O que NÃO se confere, dito em voz alta

A cobertura de acontecimentos inventados é PARCIAL — só os tipos com termo
concreto próprio (ver `configs/generation_prompt.yaml`). Não há análise
sintática, não há verificação de que a relação causal foi preservada, e não há
robustez adversarial: isso é M6.4, e prometê-lo aqui daria falsa segurança.

## Passagens de registro NÃO entram nesta conta

Decisão central, e ela vem de um achado medido no ADR 0027: uma busca por
similaridade devolve, para a mesma consulta, tanto a regra de vocabulário quanto
a correção validada que diz o mesmo — as duas são orientação legítima. Se o
verificador tratasse o texto das passagens como afirmação a fundamentar, trocar
uma irmã pela outra mudaria o veredito sem que nada de factual tivesse mudado.

A regra é mais simples e mais forte do que arbitrar entre elas: **a prosa gerada
é conferida contra o PISO e o DOSSIÊ, nunca contra o corpus.** Passagem informa
língua; ela não é fonte de fato e não é objeto de fundamentação.
"""

from __future__ import annotations

import re

from ecosfera_ai.domain.consumers.explanation import Explanation
from ecosfera_ai.domain.consumers.factual_context import FactualContext
from ecosfera_ai.domain.consumers.vocabulary import (
    MASS_MORTALITY,
    POPULATION_DECLINED,
    SPECIATION_OCCURRED,
)
from ecosfera_ai.domain.consumers.wording import (
    absolute_fitness_phrases_in,
    linear_descent_phrases_in,
    teleological_phrases_in,
)
from ecosfera_ai.domain.generation.anchoring import DetectionCoverage, GroundingVerdict
from ecosfera_ai.domain.generation.fact_claims import (
    TEMPERATURE_SHIFT,
    directional_problems_in,
    speciation_problems_in,
)
from ecosfera_ai.domain.generation.prompt import PromptSpec

_NUMBER = re.compile(r"\d+")

# Os tipos que o M6.4 passou a conferir sem depender de termo concreto próprio.
_CLAIM_CHECKED = frozenset(
    {SPECIATION_OCCURRED, TEMPERATURE_SHIFT, POPULATION_DECLINED, MASS_MORTALITY}
)

# Os que seguem SEM checagem de invenção, e que por isso rebaixam a cobertura de
# um veredito aprovado. Declarados aqui, e não só no YAML, porque é este módulo
# que precisa dizer a verdade sobre si mesmo.
UNCHECKED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "LifeEmerged",
        "TrophicCollapse",
        "GreenhouseForcingChanged",
        "CarryingCapacityShift",
        "ClimateThresholdCrossed",
    }
)


def _coverage_for(spec: PromptSpec) -> DetectionCoverage:
    """O que esta verificação conferiu, e o que ela não conferiu.

    `checked` soma os tipos com termo concreto (M6.3) aos que ganharam checagem
    estrutural ou direcional (M6.4). `unchecked` é o resto — e existe para que um
    APROVADO nunca afirme mais conferência do que houve.
    """
    return DetectionCoverage(
        checked=frozenset(spec.detectable_event_types) | _CLAIM_CHECKED,
        unchecked=UNCHECKED_EVENT_TYPES,
    )


def _numbers_in(text: str) -> set[str]:
    return set(_NUMBER.findall(text))


def verify_grounding(
    generated: str,
    *,
    floor: Explanation,
    context: FactualContext,
    spec: PromptSpec,
) -> GroundingVerdict:
    """Confere a prosa gerada contra o piso e o dossiê que a originaram.

    Devolve TODOS os motivos de reprovação, e não o primeiro: o M6.4 vai montar
    conjunto de avaliação a partir destes registros, e saber que uma saída violou
    três regras é diferente de saber que violou alguma.
    """
    reasons: list[str] = []

    if not generated.strip():
        return GroundingVerdict(passed=False, reasons=("o modelo devolveu texto vazio",))

    # --- 1. Números ----------------------------------------------------------
    allowed = _numbers_in(floor.summary)
    for fact in floor.facts:
        allowed |= _numbers_in(fact.text)
        allowed |= {value for value in fact.slots.values() if value.isdigit()}
    for invented in sorted(_numbers_in(generated) - allowed):
        reasons.append(
            f"o número {invented!r} aparece na prosa gerada e não vem do piso — "
            "toda quantidade que chega ao aluno tem de sair do event log"
        )

    # --- 2. Formulação proibida ----------------------------------------------
    for phrase in teleological_phrases_in(generated):
        reasons.append(f"formulação teleológica {phrase!r} (BIO-005)")
    for phrase in absolute_fitness_phrases_in(generated):
        reasons.append(f"aptidão absoluta {phrase!r} (Q5): a aptidão é relação, não nota")

    # --- 3. Acontecimento inventado, por termo concreto -----------------------
    present = {event.event_type for event in context.events}
    lowered = generated.lower()
    for event_type in sorted(spec.detectable_event_types - present):
        for term in spec.signatures_for(event_type):
            if term in lowered:
                reasons.append(
                    f"a prosa fala em {term!r}, e o dossiê deste planeta não tem "
                    f"{event_type} — o modelo acrescentou um acontecimento"
                )

    # --- 4. Os três tipos sem termo concreto (M6.4, Task 0) -------------------
    #
    # Especiação por identificador estrutural; temperatura e população por
    # direção conferida contra o delta do log. Ver `fact_claims` para o porquê de
    # cada um, e por que a cobertura daqui é parcial e declarada.
    reasons.extend(speciation_problems_in(generated, context))
    reasons.extend(directional_problems_in(generated, context))

    # --- 5. Descendência linear na prosa (BIO-001) ----------------------------
    #
    # O tipo recusa "A deu origem a B" e o template não tem slot de linhagem;
    # nenhuma das duas garantias alcança prosa livre.
    for phrase in linear_descent_phrases_in(generated):
        reasons.append(
            f"descendência linear {phrase!r} (BIO-001): houve divisão a partir de um "
            "ancestral comum, e nenhuma linhagem é a versão antiga da outra"
        )

    return GroundingVerdict(
        passed=not reasons, reasons=tuple(reasons), coverage=_coverage_for(spec)
    )


def describe_failure(generated: str, verdict: GroundingVerdict) -> str:
    """Uma linha de log com o bastante para o M6.4 reconstruir o caso.

    O texto reprovado entra INTEIRO. Guardar só o motivo deixaria o M6.4 com uma
    contagem de falhas e nenhum exemplo — e é de exemplos reais que se monta um
    conjunto de avaliação que valha alguma coisa.
    """
    motives = "; ".join(verdict.reasons) or "sem motivo registrado"
    return f"geração reprovada na fundamentação [{motives}] | texto: {generated.strip()!r}"


__all__ = ["UNCHECKED_EVENT_TYPES", "describe_failure", "verify_grounding"]
