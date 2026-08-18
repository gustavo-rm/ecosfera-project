"""Trocar a FORMA não pode mexer na FUNDAMENTAÇÃO (M6.5).

O turno que varia o piso é o turno em que a fundamentação corre mais risco, e o
risco não é hipotético: uma forma nova é prosa nova chegando ao aluno, escrita
depois de todos os testes que guardam a prosa antiga. O modo de errar é banal —
uma frase alternativa que acrescente uma palavra de quantidade, ou que afirme uma
relação que o dossiê não contém — e ele produz exatamente a alucinação por
template que o M6.1 abriu declarando possível.

## Como isto é verificado sem escrever o critério de novo

O critério do M6.1 vive em `test_every_claim_is_grounded_in_context`, e é de lá
que ele é IMPORTADO. Copiá-lo para cá criaria a segunda cópia que envelheceria
sozinha — a mesma razão pela qual a lista do BIO-005 mora num lugar só. O que
este arquivo acrescenta é o eixo novo: rodar aquele critério contra CADA giro do
conjunto de formas, e não só contra o que a posição escolheu.

## E o portão do M6.3, no mesmo movimento

O piso é o que o verificador do M6.3 usa como fonte de verdade. Se uma forma nova
introduzisse formulação proibida ou afirmação sem lastro, o próprio piso
reprovaria no portão que ele deveria ancorar — e o sistema recuaria para um texto
que ele mesmo considera inválido. `verify_grounding(piso, contra o próprio piso)`
é a checagem mais barata que existe contra isso, e ela vale para toda forma.
"""

from __future__ import annotations

import pytest
from tests.support import speciation_event
from tests.support_context import branching_cascade, life_emerged, spans_two_eras
from tests.support_explanation import context_of, rotated_templates
from tests.support_generation import spec
from tests.unit.test_every_claim_is_grounded_in_context import (
    NUMBER,
    _derivable_values,
    _resolves,
)

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import FactualContext
from ecosfera_ai.domain.consumers.narration import QUIET_PERIOD
from ecosfera_ai.domain.generation.grounding import verify_grounding

TRAIL = [life_emerged(era=1, tick=99), *branching_cascade(), *spans_two_eras()[:1]]

# Três giros bastam para percorrer todas as formas da família da cascata, e um
# quarto confirma que o giro volta ao começo em vez de sair da tabela.
ROTATIONS = (0, 1, 2, 3)


def _cases(offset: int) -> list[tuple[str, Explanation, FactualContext]]:
    renderer = ExplanationRenderer(rotated_templates(offset))
    speciation = speciation_event()
    speciation_context = context_of([speciation], era=speciation.occurred_at.era)
    return [
        ("cascata", renderer.render(context_of(TRAIL)), context_of(TRAIL)),
        ("especiação", renderer.render(speciation_context), speciation_context),
        ("vazio", renderer.render(context_of([])), context_of([])),
        (
            "registro simples",
            renderer.render(context_of(TRAIL), Register.SIMPLE),
            context_of(TRAIL),
        ),
    ]


# --- O critério do M6.1, para toda forma --------------------------------------


@pytest.mark.parametrize("offset", ROTATIONS)
def test_every_fact_still_points_at_an_event_in_the_dossier(offset: int) -> None:
    for name, explanation, context in _cases(offset):
        known = {event.event_id for event in context.events}
        for fact in explanation.facts:
            if fact.grounding.event_id is None:
                assert fact.template_id == QUIET_PERIOD, f"[{name}/{offset}]"
                continue
            assert fact.grounding.event_id in known, f"[{name}/{offset}] {fact.template_id}"


@pytest.mark.parametrize("offset", ROTATIONS)
def test_every_declared_field_still_resolves(offset: int) -> None:
    for name, explanation, context in _cases(offset):
        for fact in explanation.facts:
            if fact.grounding.event_id is None:
                assert fact.grounding.fields == ("events",)
                continue
            event = context.event(fact.grounding.event_id)
            assert event is not None
            for path in fact.grounding.fields:
                assert _resolves(path, event, context, fact.grounding.event_id), (
                    f"[{name}/{offset}] {fact.template_id} declara {path!r} sem lastro"
                )


@pytest.mark.parametrize("offset", ROTATIONS)
def test_no_form_smuggles_a_number_of_its_own(offset: int) -> None:
    """O modo de errar mais provável ao escrever uma frase alternativa.

    "Em poucos ciclos", "as duas linhagens", "de uma só vez" — a prosa natural
    convida a quantificar, e um numeral que não venha de slot é, por definição,
    invenção. Que o dossiê tenha um número parecido não salva a frase.
    """
    for name, explanation, _ in _cases(offset):
        for fact in explanation.facts:
            for number in NUMBER.findall(fact.text):
                assert number in set(fact.slots.values()), (
                    f"[{name}/{offset}] {fact.template_id} traz o número {number!r} "
                    f"sem slot: {fact.text!r}"
                )


@pytest.mark.parametrize("offset", ROTATIONS)
def test_every_substituted_slot_is_still_derivable(offset: int) -> None:
    for name, explanation, context in _cases(offset):
        for fact in explanation.facts:
            if fact.grounding.event_id is None:
                assert not fact.slots
                continue
            allowed = _derivable_values(context, fact.grounding.event_id)
            for slot, value in fact.slots.items():
                assert value in allowed, (
                    f"[{name}/{offset}] {fact.template_id} preencheu {slot!r} com {value!r}"
                )


@pytest.mark.parametrize("offset", ROTATIONS)
def test_the_summary_is_still_exactly_the_join_of_the_facts(offset: int) -> None:
    for name, explanation, _ in _cases(offset):
        assert explanation.summary == " ".join(f.text for f in explanation.facts), (
            f"[{name}/{offset}] o resumo diverge dos fatos"
        )


# --- E o portão do M6.3 aprova o próprio piso ---------------------------------


@pytest.mark.parametrize("offset", ROTATIONS)
def test_the_floor_passes_the_generation_gate_it_anchors(offset: int) -> None:
    """Um piso que reprovasse no próprio portão seria recuo para texto inválido."""
    context = context_of(TRAIL)
    floor = ExplanationRenderer(rotated_templates(offset)).render(context)
    verdict = verify_grounding(floor.summary, floor=floor, context=context, spec=spec())
    assert verdict.passed, f"giro {offset}: {verdict.reasons}"


def test_the_rotation_really_changes_the_text() -> None:
    """Contraprova: sem isto, os testes acima poderiam estar girando nada.

    Se `rotated_templates` devolvesse o conjunto original, tudo passaria e nada
    teria sido verificado — a família de falha do teste que confere a saída
    consigo mesma.
    """
    texts = {
        ExplanationRenderer(rotated_templates(k)).render(context_of(TRAIL)).summary
        for k in ROTATIONS
    }
    assert len(texts) >= 3, "girar as formas não mudou a prosa: o giro não está girando"
