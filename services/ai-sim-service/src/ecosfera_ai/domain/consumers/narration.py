"""Seleciona e preenche os templates a partir do dossiê — o núcleo do M6.1.

Puro e total: `FactualContext` entra, `ExplainedFact`s saem. Sem I/O, sem
relógio, sem aleatoriedade. Mesma fatia, mesma prosa, palavra por palavra — o
que torna esta camada testável como os marcos físicos foram, e o que dá ao M6.4
uma linha de base estável contra a qual medir o que o LLM fizer.

## O que é narrado, e por que não é tudo

Uma era real produz centenas de eventos: 543 numa corrida de 400 ticks com
meteoro, dos quais 257 mortandades em massa. Enfileirar 543 frases não é
explicação — é despejo. Mas resumir "houve muita atividade vulcânica" seria
afirmar uma avaliação que o dossiê não contém. Com o agrupamento abaixo, a mesma
corrida rende 37 frases.

A saída é contar o que o dossiê SABE contar:

* **Marcos biológicos** (extinção, especiação, surgimento da vida) são narrados
  UM A UM. São raros e cada um é individualmente significativo — colapsá-los
  apagaria justamente o que o aluno precisa ver.
* **Processos recorrentes** (temperatura, vulcanismo, química, capacidade, o
  deslocamento de traço e as perdas PARCIAIS de população) são narrados numa
  ocorrência só, com a contagem de repetições. A contagem é derivada do dossiê,
  então "isso se repetiu 80 vezes" é tão ancorado quanto a primeira frase — e é
  informação que o aluno não teria lendo oitenta parágrafos iguais. No caso da
  adaptação, "de pouco em pouco, dez vezes" é inclusive a descrição mais correta
  do fenômeno.

A ocorrência escolhida para falar pelo grupo não é a primeira por acaso — ver
`_representative`, onde a escolha errada custaria a cadeia causal da fatia.

## Por que a prosa não nomeia identificadores

Nenhuma frase carrega UUID de linhagem ou de evento. Não é economia: um
identificador no meio da frase não ensina nada, e o lugar dele é o `Grounding`,
onde serve à auditoria. O modelo é de COMUNIDADE — identidade de espécie é
camada pós-M6 (ADR 0024), e inventar nomes ("a espécie Alpha") anteciparia por
baixo do pano uma camada que a simulação não sustenta.

## O que acontece com o que não se sabe dizer

Um tipo de evento sem substantivo no vocabulário é PULADO, em silêncio. É a
mesma regra que `EventTranslation.observations` aplica desde o M1, e pela mesma
razão: o Event Store cresce com Engines novos, e o Tutor não pode quebrar porque
apareceu um tipo que ele ainda não sabe narrar. O que ele NÃO pode fazer é
narrá-lo com um nome inventado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ecosfera_ai.domain.consumers.explanation import (
    ExplainedFact,
    Grounding,
    Register,
)
from ecosfera_ai.domain.consumers.factual_context import (
    ExtinctionNature,
    FactualContext,
)
from ecosfera_ai.domain.consumers.templates import TemplateSet
from ecosfera_ai.domain.consumers.vocabulary import (
    LIFE_EMERGED,
    MASS_MORTALITY,
    SPECIATION_OCCURRED,
    SPECIES_EXTINCT,
    TROPHIC_COLLAPSE,
)
from ecosfera_ai.shared_kernel.events import DomainEvent, SimulationTime

TRAIT_SHIFT = "TraitShift"

# Narrados UM A UM: marcos raros, em que cada ocorrência muda o estado
# qualitativo do planeta e agrupá-las apagaria o que o aluno precisa ver.
#
# A lista é curta por medição, não por intuição. Numa corrida de 400 ticks com
# meteoro: 9 extinções, 7 especiações, 10 surgimentos de vida — todos narráveis
# individualmente. No mesmo dossiê, 257 mortandades em massa e 130
# deslocamentos de traço, que são PROCESSOS e caem no agrupamento abaixo.
#
# Mortandade em massa parece marco e não é: ela ocorre em ticks consecutivos
# enquanto o ambiente aperta. Narrá-la uma vez por ocorrência produzia 257
# parágrafos quase idênticos — o "despejo" que este módulo existe para evitar, e
# que só apareceu quando o roteiro de fumaça rodou contra uma corrida real.
INDIVIDUAL_TYPES: frozenset[str] = frozenset({SPECIES_EXTINCT, SPECIATION_OCCURRED, LIFE_EMERGED})

QUIET_PERIOD = "T-QUIET-PERIOD"


@dataclass(frozen=True, slots=True)
class _Draft:
    """Um fato antes de virar texto — o que o seletor decidiu."""

    template_id: str
    slots: dict[str, str]
    fields: tuple[str, ...]
    event: DomainEvent


def _order_key(event: DomainEvent) -> tuple[int, int, str]:
    return (event.occurred_at.era, event.occurred_at.tick, event.event_id)


def _trigger_noun(
    context: FactualContext, event: DomainEvent, templates: TemplateSet
) -> str | None:
    """O substantivo do evento que DISPAROU este, se o dossiê o contém.

    "Se o dossiê o contém" é a cláusula inteira. Uma extinção catastrófica cuja
    causa ficou fora da fatia não pode ganhar um meteoro emprestado da
    plausibilidade: o template sem gatilho existe exatamente para esse caso.
    """
    if event.causation_id is None:
        return None
    cause = context.event(event.causation_id)
    if cause is None:
        return None
    return templates.noun_for(cause.event_type)


def _extinction_draft(
    context: FactualContext, event: DomainEvent, templates: TemplateSet
) -> _Draft | None:
    """Extinção — e a fronteira do ADR 0019 decidindo qual família narra."""
    fact = next((f for f in context.extinctions if f.event_id == event.event_id), None)
    if fact is None:
        return None
    tick = str(event.occurred_at.tick)

    if fact.nature is ExtinctionNature.CATASTROPHIC:
        trigger = _trigger_noun(context, event, templates)
        if trigger is None:
            return _Draft(
                template_id="T-EXTINCTION-CATASTROPHIC-UNTRACED",
                slots={"tick": tick},
                fields=("occurred_at.tick", "cause_code"),
                event=event,
            )
        return _Draft(
            template_id="T-EXTINCTION-CATASTROPHIC",
            slots={"tick": tick, "trigger": trigger},
            fields=("occurred_at.tick", "cause_code", "causation_id"),
            event=event,
        )

    mechanism = templates.mechanism_for(fact.cause_code)
    if mechanism is None:
        return None
    return _Draft(
        template_id="T-EXTINCTION-ECOLOGICAL",
        slots={"tick": tick, "mechanism": mechanism},
        fields=("occurred_at.tick", "cause_code"),
        event=event,
    )


def _speciation_draft(
    context: FactualContext, event: DomainEvent, templates: TemplateSet
) -> _Draft | None:
    """Especiação — ancestral comum, com os três ids indo para o `Grounding`.

    O template não recebe linhagem alguma como slot, e é isso que torna a frase
    ESTRUTURALMENTE incapaz de dizer "A deu origem a B": não há onde encaixar um
    sujeito e um objeto de ancestralidade. A garantia do `SpeciationFact` (um
    ancestral, duas irmãs) chega até a prosa sem depender de quem a escreveu.
    """
    fact = next((f for f in context.speciations if f.event_id == event.event_id), None)
    if fact is None:
        return None
    mechanism = templates.mechanism_for(fact.cause_code)
    if mechanism is None:
        return None
    return _Draft(
        template_id="T-SPECIATION-COMMON-ANCESTOR",
        slots={"tick": str(event.occurred_at.tick), "mechanism": mechanism},
        fields=("occurred_at.tick", "cause_code", "ancestor", "lineages"),
        event=event,
    )


def _life_emerged_draft(event: DomainEvent, templates: TemplateSet) -> _Draft | None:
    """O surgimento da vida — marco, e narrado a cada vez que acontece."""
    mechanism = templates.mechanism_for(str(event.cause_code.value))
    if mechanism is None:
        return None
    return _Draft(
        template_id="T-LIFE-EMERGED",
        slots={"tick": str(event.occurred_at.tick), "mechanism": mechanism},
        fields=("occurred_at.tick", "cause_code"),
        event=event,
    )


def _mortality_draft(
    context: FactualContext, event: DomainEvent, templates: TemplateSet, occurrences: int
) -> _Draft | None:
    """Mortandade em massa e colapso trófico — perdas PARCIAIS, e recorrentes.

    A distinção que a frase precisa carregar: a comunidade perdeu população e
    **não desapareceu**. Confundir isto com extinção ensinaria que toda perda é
    terminal, quando a perda parcial é justamente o caso comum deste modelo
    (ADR 0016).

    O agrupamento por (tipo, causa) separa sozinho a mortandade catastrófica da
    ecológica: são `cause_code` diferentes, então nunca caem no mesmo grupo e
    nunca são narradas pela mesma frase.
    """
    tick = str(event.occurred_at.tick)
    code = str(event.cause_code.value)
    slots = {"tick": tick}
    fields = ["occurred_at.tick", "cause_code"]

    if event.event_type == MASS_MORTALITY:
        trigger = _trigger_noun(context, event, templates)
        if code == "CATASTROPHIC_EVENT" and trigger is not None:
            slots["trigger"] = trigger
            fields.append("causation_id")
            template_id = "T-MASS-MORTALITY-CATASTROPHIC"
        else:
            mechanism = templates.mechanism_for(code)
            if mechanism is None:
                return None
            slots["mechanism"] = mechanism
            template_id = "T-MASS-MORTALITY"
    else:
        mechanism = templates.mechanism_for(code)
        if mechanism is None:
            return None
        slots["mechanism"] = mechanism
        template_id = "T-TROPHIC-COLLAPSE"

    if occurrences > 1:
        slots["occurrences"] = str(occurrences)
        fields.append("occurrences")
        template_id = f"{template_id}-REPEATED"

    return _Draft(template_id=template_id, slots=slots, fields=tuple(fields), event=event)


def _adaptation_draft(
    event: DomainEvent, templates: TemplateSet, occurrences: int
) -> _Draft | None:
    """Adaptação — e a negação explícita de que ela seja especiação (PED-003).

    Colapsada como os fatos ambientais, e pela mesma razão: o deslocamento de
    traço é um processo CONTÍNUO, não um marco. Uma era emite dez `TraitShift`, e
    dez parágrafos quase idênticos ensinariam menos que um só dizendo que o
    deslocamento se repetiu dez vezes de pouco em pouco — que é, aliás, a forma
    correta de descrever adaptação gradual.
    """
    mechanism = templates.mechanism_for(str(event.cause_code.value))
    if mechanism is None:
        return None
    slots = {"tick": str(event.occurred_at.tick), "mechanism": mechanism}
    fields = ["occurred_at.tick", "cause_code"]
    template_id = "T-TRAIT-ADAPTATION"
    if occurrences > 1:
        slots["occurrences"] = str(occurrences)
        fields.append("occurrences")
        template_id = "T-TRAIT-ADAPTATION-REPEATED"
    return _Draft(template_id=template_id, slots=slots, fields=tuple(fields), event=event)


def _environmental_draft(
    context: FactualContext,
    event: DomainEvent,
    templates: TemplateSet,
    occurrences: int,
) -> _Draft | None:
    """Cadeia ambiental — CAUSAL, e não apenas descritiva.

    "A temperatura mudou" é descrição. "A temperatura mudou logo depois do
    acúmulo de gás carbônico, e é dele que decorre" é explicação — e a diferença
    é o `causation_id`, que vem do log e não de uma regra geral projetada para a
    frente. Quando o dossiê não traz a causa, a frase não a inventa: usa o
    template de raiz e narra o mecanismo do próprio evento.
    """
    subject = templates.noun_for(event.event_type)
    if subject is None:
        return None
    mechanism = templates.mechanism_for(str(event.cause_code.value))
    if mechanism is None:
        return None

    slots = {"tick": str(event.occurred_at.tick), "subject": subject, "mechanism": mechanism}
    fields = ["occurred_at.tick", "event_type", "cause_code"]

    cause_subject: str | None = None
    if event.causation_id is not None:
        cause = context.event(event.causation_id)
        if cause is not None:
            cause_subject = templates.noun_for(cause.event_type)

    if cause_subject is not None:
        slots["cause_subject"] = cause_subject
        fields.append("causation_id")
        template_id = "T-CHAIN-CAUSED"
    else:
        template_id = "T-CHAIN-ROOT"

    if occurrences > 1:
        slots["occurrences"] = str(occurrences)
        fields.append("occurrences")
        template_id = f"{template_id}-REPEATED"

    return _Draft(template_id=template_id, slots=slots, fields=tuple(fields), event=event)


def _representative(context: FactualContext, group: Sequence[DomainEvent]) -> DomainEvent:
    """Qual ocorrência do grupo fala pelas outras.

    A PRIMEIRA que tem causa registrada no dossiê, e só depois a primeira de
    todas. A preferência não é detalhe: numa corrida vulcânica a primeira
    `TemperatureShift` costuma ser raiz (não houve evento de atmosfera naquele
    tick), enquanto as seguintes decorrem do acúmulo de gás carbônico. Escolher
    cegamente a primeira apagaria a cadeia vulcanismo → carbono → temperatura da
    narração — o elo mais pedagógico da fatia vertical — e o aluno leria "a
    temperatura mudou" sem o que veio antes.

    Continua determinístico: o grupo já chega ordenado por tempo de simulação.
    """
    return next((e for e in group if context.cause_of(e.event_id) is not None), group[0])


def _drafts(context: FactualContext, templates: TemplateSet) -> list[_Draft]:
    """Escolhe o que narrar, uma vez por fato biológico e por tipo recorrente."""
    drafts: list[_Draft] = []
    recurring: dict[tuple[str, str], list[DomainEvent]] = {}

    for event in sorted(context.events, key=_order_key):
        if event.event_type in INDIVIDUAL_TYPES:
            if event.event_type == SPECIES_EXTINCT:
                draft = _extinction_draft(context, event, templates)
            elif event.event_type == SPECIATION_OCCURRED:
                draft = _speciation_draft(context, event, templates)
            else:
                draft = _life_emerged_draft(event, templates)
            if draft is not None:
                drafts.append(draft)
            continue

        recurring.setdefault((event.event_type, str(event.cause_code.value)), []).append(event)

    for group in recurring.values():
        chosen = _representative(context, group)
        drafts.append(_recurring_draft(context, chosen, templates, len(group)))  # type: ignore[arg-type]

    return sorted([d for d in drafts if d is not None], key=lambda d: _order_key(d.event))


def _recurring_draft(
    context: FactualContext, event: DomainEvent, templates: TemplateSet, occurrences: int
) -> _Draft | None:
    """Despacha o processo recorrente para a família de frase que lhe cabe."""
    if event.event_type == TRAIT_SHIFT:
        return _adaptation_draft(event, templates, occurrences)
    if event.event_type in {MASS_MORTALITY, TROPHIC_COLLAPSE}:
        return _mortality_draft(context, event, templates, occurrences)
    return _environmental_draft(context, event, templates, occurrences)


def narrate(
    context: FactualContext,
    templates: TemplateSet,
    register: Register = Register.STANDARD,
) -> tuple[ExplainedFact, ...]:
    """Renderiza a fatia inteira, em ordem cronológica.

    A saída é uma LISTA de frases autocontidas, e não um texto corrido com
    conectivos. É uma escolha honesta sobre o que um renderizador por template
    consegue afirmar: encadear "enquanto isso" ou "como resultado" entre dois
    fatos seria afirmar uma relação que o dossiê pode não conter. A relação
    causal que existe já está DENTRO de cada frase, vinda do `causation_id`.

    A fatia sem nada a narrar recebe a frase de período tranquilo — sem drama
    fabricado e sem pedido de desculpas. Uma era tranquila é resultado legítimo
    do planeta, e a ausência de especiação, em particular, é o caso COMUM deste
    modelo (~6 σ; `docs/decisions/deferred.md`), não uma lacuna a lamentar.

    ## A escolha da FORMA, e por que ela é a posição (M6.5)

    Um template pode ter mais de uma forma para a mesma afirmação, e a que sai é
    `posição % número de formas`. Duas propriedades vêm juntas:

    * duas ocorrências SEGUIDAS do mesmo template saem diferentes — que era o
      defeito medido: na cascata ramificada, duas frases de `T-CHAIN-CAUSED`
      repetiam palavra por palavra o mesmo prefixo de onze palavras;
    * a saída continua função pura do dossiê. A ordem dos rascunhos já é
      determinística, então a forma escolhida também é. Nada de aleatório entra
      aqui, e não pode entrar: o M6.4 mede a variação do LLM contra este piso, e
      um piso que variasse sozinho tiraria o chão da medição.

    A posição, e não o `event_id`: o que se quer quebrar é a repetição VIZINHA,
    e só a posição sabe quem é vizinho de quem. Um índice derivado do evento
    daria formas estáveis por evento e não impediria dois vizinhos de caírem na
    mesma — que é justamente o caso a evitar.
    """
    drafts = _drafts(context, templates)
    if not drafts:
        template = templates.get(QUIET_PERIOD, register)
        return (
            ExplainedFact(
                template_id=QUIET_PERIOD,
                register=template.register,
                text=template.render({}),
                occurred_at=SimulationTime(tick=0, era=context.slice.era or 0),
                grounding=Grounding(event_id=None, fields=("events",)),
            ),
        )

    facts: list[ExplainedFact] = []
    for position, draft in enumerate(drafts):
        template = templates.get(draft.template_id, register, variant=position)
        facts.append(
            ExplainedFact(
                template_id=draft.template_id,
                register=template.register,
                text=template.render(draft.slots),
                occurred_at=draft.event.occurred_at,
                grounding=Grounding(event_id=draft.event.event_id, fields=draft.fields),
                slots=dict(draft.slots),
            )
        )
    return tuple(facts)


def summarize(facts: Sequence[ExplainedFact]) -> str:
    """Junta as frases — e nada além disso.

    Deliberadamente burro. Um resumo que SINTETIZASSE teria de afirmar algo que
    nenhum fato isolado afirma ("a era foi turbulenta"), e esse algo não teria
    origem no dossiê. É a alucinação mais provável de um renderizador, e a junção
    literal é o que a torna impossível.
    """
    return " ".join(fact.text for fact in facts)


__all__ = ["INDIVIDUAL_TYPES", "QUIET_PERIOD", "narrate", "summarize"]
