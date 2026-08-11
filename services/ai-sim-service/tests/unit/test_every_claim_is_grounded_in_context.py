"""TODA afirmação da prosa é rastreável a um campo do dossiê — exaustivamente.

Este é o teste central do M6.1, e o equivalente, no mundo dos templates, do
"derivável do event log" que define correção para o M6 inteiro.

## Por que ele precisa existir mesmo sem LLM

Não ter modelo generativo não é imunidade. Um template que diga "a espécie não
conseguiu se adaptar" numa extinção catastrófica afirma algo que o dossiê **não
contém**, e a criança que o lê fica com a concepção equivocada exatamente como
ficaria se um modelo o tivesse escrito. A diferença entre template e LLM é a
facilidade de auditar, não a existência do risco — e é essa facilidade que este
arquivo cobra.

## O critério, e por que ele é mecânico

Três verificações, e nenhuma delas depende de alguém achar que a frase está boa:

1. **Origem.** Todo fato aponta para um evento que está no dossiê.
2. **Campos.** Todo caminho declarado no `Grounding` resolve contra aquele
   evento ou contra o fato derivado dele — nada de campo decorativo, que é a
   família de defeito que o `planet_id` fantasma do M5 já custou a esta base.
3. **Valores.** Todo número que aparece na frase está entre os slots
   substituídos, e todo slot vem de um valor derivável do dossiê. Um número na
   prosa que não venha do log é, por definição, inventado.

E uma quarta, que fecha a porta mais provável: o `summary` é EXATAMENTE a junção
dos fatos. Um resumo que sintetizasse teria de afirmar algo que nenhum fato
isolado afirma.
"""

from __future__ import annotations

import re

from tests.support import speciation_event
from tests.support_context import branching_cascade, life_emerged, spans_two_eras
from tests.support_explanation import context_of, explain, renderer, templates

from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import FactualContext
from ecosfera_ai.domain.consumers.narration import QUIET_PERIOD

TRAIL = [life_emerged(era=1, tick=99), *branching_cascade(), *spans_two_eras()[:1]]
NUMBER = re.compile(r"\d+")


def _every_case() -> list[tuple[str, Explanation, FactualContext]]:
    """Os cenários que cobrem todas as famílias de template de uma vez."""
    speciation = speciation_event()
    cases = [
        ("cascata", explain(TRAIL), context_of(TRAIL)),
        (
            "especiação",
            explain([speciation], era=speciation.occurred_at.era),
            context_of([speciation], era=speciation.occurred_at.era),
        ),
        ("vazio", explain([]), context_of([])),
    ]
    simple = renderer().render(context_of(TRAIL), Register.SIMPLE)
    cases.append(("registro simples", simple, context_of(TRAIL)))
    return cases


def _derivable_values(context: FactualContext, event_id: str) -> set[str]:
    """Tudo o que o dossiê autoriza a frase a dizer sobre aquele evento.

    Deliberadamente reconstruído a partir do dossiê e do arquivo de vocabulário —
    e não copiado do que o renderizador produziu. Comparar a saída consigo mesma
    não verificaria nada.
    """
    event = context.event(event_id)
    assert event is not None
    table = templates()

    allowed = {
        str(event.occurred_at.tick),
        str(event.occurred_at.era),
        str(len([e for e in context.events if e.event_type == event.event_type])),
    }
    # Contagem por (tipo, causa): é o grão em que o narrador agrupa recorrências.
    allowed.add(
        str(
            len(
                [
                    e
                    for e in context.events
                    if (e.event_type, e.cause_code) == (event.event_type, event.cause_code)
                ]
            )
        )
    )
    noun = table.noun_for(event.event_type)
    if noun is not None:
        allowed.add(noun)
    mechanism = table.mechanism_for(str(event.cause_code.value))
    if mechanism is not None:
        allowed.add(mechanism)
    cause = context.cause_of(event.event_id)
    if cause is not None:
        cause_noun = table.noun_for(cause.event_type)
        if cause_noun is not None:
            allowed.add(cause_noun)
    return allowed


# --- 1. Origem ----------------------------------------------------------------


def test_every_fact_points_at_an_event_that_is_in_the_dossier() -> None:
    for name, explanation, context in _every_case():
        known = {event.event_id for event in context.events}
        for fact in explanation.facts:
            if fact.grounding.event_id is None:
                assert fact.template_id == QUIET_PERIOD, (
                    f"[{name}] só a frase de período tranquilo pode não ter evento"
                )
                continue
            assert fact.grounding.event_id in known, (
                f"[{name}] o fato {fact.template_id} cita um evento fora do dossiê"
            )


# --- 2. Campos ----------------------------------------------------------------


def test_every_declared_field_resolves_against_the_dossier() -> None:
    """Nenhum caminho declarado é decorativo — a varredura do ADR 0023, na prosa."""
    for name, explanation, context in _every_case():
        for fact in explanation.facts:
            if fact.grounding.event_id is None:
                assert fact.grounding.fields == ("events",)
                continue
            event = context.event(fact.grounding.event_id)
            assert event is not None
            for path in fact.grounding.fields:
                assert _resolves(path, event, context, fact.grounding.event_id), (
                    f"[{name}] {fact.template_id} declara o campo {path!r}, "
                    "que não existe no dossiê"
                )


def _resolves(path: str, event: object, context: FactualContext, event_id: str) -> bool:
    if path == "occurred_at.tick":
        return event.occurred_at.tick is not None  # type: ignore[attr-defined]
    if path == "cause_code":
        return event.cause_code is not None  # type: ignore[attr-defined]
    if path == "event_type":
        return bool(event.event_type)  # type: ignore[attr-defined]
    if path == "causation_id":
        return context.cause_of(event_id) is not None
    if path == "occurrences":
        return True
    if path in {"ancestor", "lineages"}:
        fact = next((f for f in context.speciations if f.event_id == event_id), None)
        return fact is not None and bool(getattr(fact, path))
    return False


# --- 3. Valores ---------------------------------------------------------------


def test_every_number_in_the_prose_came_from_a_substituted_slot() -> None:
    """Nenhum número aparece na frase sem ter passado por um slot."""
    for name, explanation, _ in _every_case():
        for fact in explanation.facts:
            for number in NUMBER.findall(fact.text):
                assert number in set(fact.slots.values()), (
                    f"[{name}] o número {number!r} aparece em {fact.template_id} "
                    f"sem vir de slot algum: {fact.text!r}"
                )


def test_every_substituted_slot_is_derivable_from_the_dossier() -> None:
    """E o caminho de volta: nenhum slot carrega valor que o dossiê não sustente."""
    for name, explanation, context in _every_case():
        for fact in explanation.facts:
            if fact.grounding.event_id is None:
                assert not fact.slots
                continue
            allowed = _derivable_values(context, fact.grounding.event_id)
            for slot, value in fact.slots.items():
                assert value in allowed, (
                    f"[{name}] {fact.template_id} preencheu {slot!r} com {value!r}, "
                    "que não é derivável do dossiê"
                )


# --- 4. O resumo não acrescenta nada -----------------------------------------


def test_the_summary_is_exactly_the_join_of_the_facts() -> None:
    """A alucinação mais provável de um renderizador é o resumo que sintetiza."""
    for name, explanation, _ in _every_case():
        assert explanation.summary == " ".join(f.text for f in explanation.facts), (
            f"[{name}] o resumo diverge dos fatos — há prosa sem origem"
        )


def test_the_summary_adds_no_sentence_of_its_own() -> None:
    for _, explanation, _ in _every_case():
        sentences = [s for s in explanation.summary.split(". ") if s.strip()]
        assert len(sentences) >= len(explanation.facts) or not explanation.facts


# --- A contraprova do próprio critério ---------------------------------------


def test_the_grounding_check_would_catch_an_invented_number() -> None:
    """Sem contraprova, o teste acima poderia estar simplesmente vazio."""
    from dataclasses import replace

    explanation = explain(TRAIL)
    honest = explanation.facts[0]
    tampered = replace(honest, text=f"{honest.text} A biomassa caiu 42 por cento.")

    leaked = [n for n in NUMBER.findall(tampered.text) if n not in set(tampered.slots.values())]
    assert leaked == ["42"], "o filtro não pegaria um número inventado na frase"


def test_the_field_check_would_catch_a_decorative_path() -> None:
    context = context_of(TRAIL)
    event = context.events[0]
    assert not _resolves("campo_inexistente", event, context, event.event_id)
