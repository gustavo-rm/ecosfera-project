"""Mesmo dossiê, mesma prosa — palavra por palavra, sempre.

É o que separa esta subetapa da seguinte, e é por isso que ela vem antes. O M6.3
coloca um LLM neste caminho, e a partir daí "a saída mudou" deixa de ser sinal de
defeito: modelos variam por temperatura, por versão, por lua. A avaliação
adversarial do M6.4 só consegue atribuir uma diferença ao modelo se a ENTRADA e o
PISO forem estáveis.

Aqui eles são. O renderizador é função pura do dossiê: sem relógio, sem
aleatoriedade, sem ordem de chegada. Um teste de igualdade literal de texto é
possível — e daqui a duas subetapas ele não será mais.
"""

from __future__ import annotations

from tests.support import speciation_event
from tests.support_context import branching_cascade, life_emerged
from tests.support_explanation import context_of, explain, renderer

from ecosfera_ai.domain.consumers.explanation import Register

TRAIL = [life_emerged(era=1, tick=99), *branching_cascade()]


def test_the_same_dossier_produces_the_same_text() -> None:
    assert explain(TRAIL).summary == explain(TRAIL).summary


def test_the_text_does_not_depend_on_the_arrival_order() -> None:
    """Reordenar a trilha não muda uma vírgula — o dossiê já ordena por tempo."""
    assert explain(TRAIL).summary == explain(list(reversed(TRAIL))).summary


def test_the_facts_compare_equal_field_by_field() -> None:
    """Igualdade estrutural, e não só de texto: slots e ancoragem também."""
    assert explain(TRAIL).facts == explain(list(reversed(TRAIL))).facts


def test_two_renderers_built_from_the_same_file_agree() -> None:
    """Determinismo de PROCESSO: nada depende de estado acumulado no objeto."""
    context = context_of(TRAIL)
    assert renderer().render(context).to_dict() == renderer().render(context).to_dict()


def test_rendering_twice_from_the_same_renderer_agrees() -> None:
    """E o renderizador é reentrante: narrar não o deixa diferente de si mesmo."""
    shared = renderer()
    context = context_of(TRAIL)
    assert shared.render(context).summary == shared.render(context).summary


def test_the_two_registers_are_each_stable_on_their_own() -> None:
    context = context_of(TRAIL)
    for register in (Register.STANDARD, Register.SIMPLE):
        first = renderer().render(context, register)
        second = renderer().render(context, register)
        assert first.summary == second.summary


def test_the_registers_differ_from_each_other() -> None:
    """A contraprova: estabilidade não pode ser o renderizador ignorando o registro."""
    context = context_of(TRAIL)
    standard = renderer().render(context, Register.STANDARD)
    simple = renderer().render(context, Register.SIMPLE)
    assert standard.summary != simple.summary


def test_a_speciation_renders_identically_across_runs() -> None:
    """O fato mais raro também é estável — é o que o M6.4 vai querer comparar."""
    event = speciation_event()
    first = explain([event], era=event.occurred_at.era)
    second = explain([event], era=event.occurred_at.era)
    assert first.to_dict() == second.to_dict()


def test_the_serialized_explanation_is_stable() -> None:
    """Inclusive a forma portável — é ela que uma avaliação futura vai guardar."""
    import json

    dumped = json.dumps(explain(TRAIL).to_dict(), sort_keys=True, ensure_ascii=False)
    again = json.dumps(explain(TRAIL).to_dict(), sort_keys=True, ensure_ascii=False)
    assert dumped == again
