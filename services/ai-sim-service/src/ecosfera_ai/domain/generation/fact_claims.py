"""Afirmações que a prosa faz sobre o planeta, conferidas contra o dossiê.

Fecha a lacuna que o ADR 0028 declarou em voz alta: a detecção de acontecimento
inventado do M6.3 dependia de um TERMO CONCRETO por tipo de evento ("meteoro",
"glacial"), e três tipos não têm termo próprio — `SpeciationOccurred`,
`TemperatureShift` e `PopulationDeclined`. Eles passavam sem verificação.

**Não é uma lacuna adversarial.** É a MESMA classe de alucinação que o M6.1
encontrou e corrigiu no antigo motor de regras, que concluía `co2↑ ⇒ temperatura↑`
sem conferir se um `TemperatureShift` ocorreu naquele planeta. Correta como
ciência geral, não derivável daquele event log — a definição de alucinação que o
M6 inteiro adota. Ela reapareceu na camada de geração, e é aqui que se fecha.

## Por que a especiação é o caso mais grave, e o mais tratável

Mais grave porque é exatamente o que a Fase 0 (BIO-001) existe para proteger, e
porque as duas garantias que o projeto já tem **não alcançam prosa**: o
`SpeciationFact` recusa "A deu origem a B" no TIPO, e o template do M6.1 não tem
slot de linhagem — mas um modelo escreve a escada de progresso em português sem
tocar em nenhum dos dois.

Mais tratável porque os identificadores ESTRUTURAIS já existem no dossiê, e
porque há um fato decisivo sobre o prompt: **o modelo nunca recebe id de linhagem
algum.** O prompt leva o resumo do piso e as passagens; o piso não tem slot de
linhagem justamente por decisão do M6.1. Logo, um identificador que apareça na
prosa não pode ter vindo do material — ele foi inventado, inclusive quando por
acaso coincidir com um id real.

## As afirmações direcionais, e o que se pode e não se pode afirmar delas

"A temperatura subiu" não tem termo exclusivo: `temperatura` aparece legitimamente
no vocabulário de mecanismo do M6.1. O que a torna uma AFIRMAÇÃO é a direção. Por
isso a conferência é sobre o par (assunto, direção), e ela responde duas coisas:

* se o dossiê não tem o evento, a afirmação é invenção;
* se tem, o sinal do delta registrado no `cause_detail` tem de bater com a direção
  afirmada — dizer que esfriou onde o log diz que esquentou é contradizer o log,
  não apenas inventar.

O que esta conferência NÃO alcança: afirmação direcional sem palavra de direção
conhecida, paráfrase criativa ("o planeta ficou um forno"), e magnitude sem
número. A cobertura é parcial, e `DetectionCoverage` existe para que ela nunca
seja apresentada como completa.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ecosfera_ai.domain.consumers.factual_context import FactualContext
from ecosfera_ai.domain.consumers.vocabulary import (
    MASS_MORTALITY,
    POPULATION_DECLINED,
    SPECIATION_OCCURRED,
)

TEMPERATURE_SHIFT = "TemperatureShift"

# Um id de linhagem é um uuid5 derivado da semente. O modelo nunca recebe nenhum,
# então a forma basta: qualquer token com esta cara na prosa é invenção.
_IDENTIFIER = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
# `lineage:algo` / `ancestor:algo` — a forma que o envelope §4 usa em
# `participants`. Se vazar para a prosa, o modelo está lendo estrutura em voz alta.
_ROLE_PREFIX = re.compile(r"\b(?:lineage|ancestor|species)\s*:\s*\S+")

# A especiação AFIRMADA. Não basta a palavra "linhagem" — ela aparece na regra de
# vocabulário VOC-002, que entra no prompt como orientação de registro. O que
# caracteriza afirmação é dizer que a divisão ACONTECEU.
_SPECIATION_CLAIMS: tuple[str, ...] = (
    "se dividiu em duas",
    "dividiu-se em duas",
    "se separou em duas",
    "duas linhagens irmãs",
    "duas linhagens novas",
    "surgiram duas linhagens",
    "deu origem a duas",
    "uma nova espécie surgiu",
    "surgiu uma espécie nova",
    "houve uma especiação",
    "ocorreu uma especiação",
)

# Direção GENÉRICA: precisa de um assunto por perto para significar alguma coisa.
_RISE: tuple[str, ...] = ("subiu", "aumentou", "cresceu", "elevou")
_FALL: tuple[str, ...] = ("caiu", "diminuiu", "baixou", "reduziu", "despencou")

# Verbos que já CARREGAM o assunto: "o planeta esquentou" é uma afirmação sobre
# temperatura sem a palavra "temperatura" em lugar nenhum.
#
# Encontrado por teste, e é a família de falha que o docstring acima previa: a
# primeira versão exigia palavra de assunto E palavra de direção, e deixava
# passar exatamente a paráfrase mais natural que um modelo escreveria.
_THERMAL_RISE: tuple[str, ...] = ("esquentou", "aqueceu", "aquecendo", "esquentando")
_THERMAL_FALL: tuple[str, ...] = ("esfriou", "resfriou", "esfriando", "resfriando")

_TEMPERATURE_WORDS: tuple[str, ...] = ("temperatura", "calor", "clima")
_POPULATION_WORDS: tuple[str, ...] = ("população", "populacao", "biomassa", "quantidade de vida")

# O delta vem do `cause_detail`. `change` é o nome que o Climate Engine grava;
# `delta` aparece em trilhas sintéticas. Aceitar os dois é o que evita que a
# conferência dependa de qual caminho produziu o evento.
_TEMPERATURE_DELTA_KEYS = ("change", "delta")


def _sentences(text: str) -> list[str]:
    """Divide em orações, porque a direção só vale perto do assunto.

    Sem isto, "a temperatura mudou. a população caiu" acusaria a temperatura de
    ter caído — a proximidade é o que liga o assunto à direção.
    """
    return [part for part in re.split(r"[.;!?\n]+", text.lower()) if part.strip()]


# Um verbo de direção seguido de artigo rege um OBJETO, e a direção passa a valer
# para ele. "aumentou a sobrevivência" não diz que a população aumentou.
_TRANSITIVE = re.compile(r"^\s+(?:a|o|as|os|um|uma|sua|seu|essa|esse|aquela|aquele)\b(.{0,40})")


def _applies_to_subject(sentence: str, verb: str, subject_words: Iterable[str]) -> bool:
    """A direção é afirmada sobre o NOSSO assunto, ou sobre outra coisa?

    Distinção encontrada por teste, e num caso que não podia falhar: a
    formulação CORRETA do BIO-005 — "surgiu uma mutação aleatória na população, e
    a característica aumentou a sobrevivência" — era acusada de afirmar que a
    população cresceu. Ela é a frase que o sistema mais precisa saber dizer, e o
    verificador a reprovava por ter o assunto e o verbo na mesma oração.

    A regra é sintática, não lexical: se o verbo rege objeto, a direção é do
    objeto. Só conta como afirmação sobre o assunto se o assunto estiver DENTRO
    desse objeto ("diminuiu a população") ou se o verbo não reger objeto algum
    ("a população diminuiu").
    """
    for match in re.finditer(re.escape(verb), sentence):
        tail = sentence[match.end() :]
        governed = _TRANSITIVE.match(tail)
        if governed is None:
            return True  # intransitivo: a direção é do sujeito da oração
        if any(word in governed.group(1) for word in subject_words):
            return True  # o objeto regido É o assunto
    return False


def _direction_in(
    sentence: str,
    subject_words: Iterable[str],
    *,
    self_evident_rise: Iterable[str] = (),
    self_evident_fall: Iterable[str] = (),
) -> str | None:
    """ "sobe", "desce" ou None — a direção afirmada sobre aquele assunto.

    Três caminhos, e cada um dos dois últimos existe por causa de um falso
    resultado encontrado em teste. Um verbo como "esquentou" nomeia a grandeza
    sozinho, e exigir "temperatura" ao lado dele deixava passar a paráfrase mais
    natural; um verbo que rege objeto fala do objeto, e ignorar isso reprovava a
    formulação correta do BIO-005.
    """
    if any(word in sentence for word in self_evident_rise):
        return "sobe"
    if any(word in sentence for word in self_evident_fall):
        return "desce"
    if not any(word in sentence for word in subject_words):
        return None
    for verb in _RISE:
        if verb in sentence and _applies_to_subject(sentence, verb, subject_words):
            return "sobe"
    for verb in _FALL:
        if verb in sentence and _applies_to_subject(sentence, verb, subject_words):
            return "desce"
    return None


def _temperature_delta(context: FactualContext) -> float | None:
    for event in context.events:
        if event.event_type != TEMPERATURE_SHIFT:
            continue
        for key in _TEMPERATURE_DELTA_KEYS:
            value = event.cause_detail.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def _population_delta(context: FactualContext) -> float | None:
    for event in context.events:
        if event.event_type not in {POPULATION_DECLINED, MASS_MORTALITY}:
            continue
        now = event.cause_detail.get("biomass")
        before = event.cause_detail.get("biomass_before")
        if isinstance(now, (int, float)) and isinstance(before, (int, float)):
            return float(now) - float(before)
    return None


def speciation_problems_in(text: str, context: FactualContext) -> tuple[str, ...]:
    """Especiação inventada, identificador vazado, ou descendência linear.

    Os três modos de a prosa errar sobre o assunto que a Fase 0 mais protege.
    """
    problems: list[str] = []
    lowered = text.lower()
    has_speciation = any(event.event_type == SPECIATION_OCCURRED for event in context.events)

    for leaked in sorted(set(_IDENTIFIER.findall(lowered))):
        problems.append(
            f"a prosa cita o identificador {leaked!r}, e o modelo nunca recebe identificador "
            "de linhagem — o piso do M6.1 não tem slot para isso, logo foi inventado"
        )
    for leaked_role in sorted(set(_ROLE_PREFIX.findall(lowered))):
        problems.append(
            f"a prosa cita {leaked_role!r}, que é forma de participante do envelope §4 "
            "e não linguagem para o aluno"
        )

    if not has_speciation:
        for claim in _SPECIATION_CLAIMS:
            if claim in lowered:
                problems.append(
                    f"a prosa afirma {claim!r} e o dossiê deste planeta não tem "
                    f"{SPECIATION_OCCURRED} — o modelo inventou uma especiação (BIO-001)"
                )
    return tuple(problems)


def directional_problems_in(text: str, context: FactualContext) -> tuple[str, ...]:
    """Afirmações de direção sobre temperatura e população, conferidas no log."""
    problems: list[str] = []
    present = {event.event_type for event in context.events}
    temperature_delta = _temperature_delta(context)
    population_delta = _population_delta(context)

    for sentence in _sentences(text):
        claimed = _direction_in(
            sentence,
            _TEMPERATURE_WORDS,
            self_evident_rise=_THERMAL_RISE,
            self_evident_fall=_THERMAL_FALL,
        )
        if claimed is not None:
            if TEMPERATURE_SHIFT not in present:
                problems.append(
                    f"a prosa afirma que a temperatura {claimed} e o dossiê não tem "
                    f"{TEMPERATURE_SHIFT} — é a generalização que o M6.1 já corrigiu uma vez"
                )
            elif temperature_delta is not None:
                observed = "sobe" if temperature_delta > 0 else "desce"
                if claimed != observed:
                    problems.append(
                        f"a prosa afirma que a temperatura {claimed}, e o log registra "
                        f"variação de {temperature_delta:+.1f} — a direção contradiz o evento"
                    )

        claimed = _direction_in(sentence, _POPULATION_WORDS)
        if claimed is not None:
            if not ({POPULATION_DECLINED, MASS_MORTALITY} & present):
                problems.append(
                    "a prosa afirma variação de população e o dossiê não tem "
                    f"{POPULATION_DECLINED} nem {MASS_MORTALITY} — acontecimento inventado"
                )
            elif population_delta is not None:
                observed = "sobe" if population_delta > 0 else "desce"
                if claimed != observed:
                    problems.append(
                        f"a prosa afirma que a população {claimed}, e o log registra "
                        f"variação de {population_delta:+.1f} — a direção contradiz o evento"
                    )
    return tuple(problems)


__all__ = [
    "TEMPERATURE_SHIFT",
    "directional_problems_in",
    "speciation_problems_in",
]
