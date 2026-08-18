"""A forma muda; os FATOS não (M6.5).

A promessa deste turno, dita como invariante verificável: varia a redação, e nada
mais. Mesmos eventos narrados, mesmos `cause_code`, mesma ordem, mesmos slots,
mesma ancoragem — só o campo `text` difere.

## Por que isto precisa ser um teste, e não uma intenção

Porque o modo de errar é fácil e silencioso. Uma forma alternativa que largasse
`{cause_subject}` continuaria renderizando, continuaria passando na fundamentação
(afirmar MENOS nunca é invenção) e teria apagado da narração o elo causal do
dossiê — o elo mais pedagógico da fatia vertical, e o que o `_representative` do
M6.1 já custou a esta base uma vez.

O teste gira as formas e compara fato a fato. Se algum campo além do texto se
mexer, a variação deixou de ser variação de forma.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade, life_emerged, spans_two_eras
from tests.support_explanation import context_of, rotated_templates

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.domain.consumers.explanation import ExplainedFact, Register

TRAIL = [life_emerged(era=1, tick=99), *branching_cascade(), *spans_two_eras()[:1]]
ROTATIONS = (0, 1, 2, 3)


def _skeleton(fact: ExplainedFact) -> tuple[object, ...]:
    """Tudo o que um fato afirma, MENOS as palavras com que ele o afirma."""
    return (
        fact.template_id,
        fact.register,
        fact.occurred_at,
        fact.grounding.event_id,
        fact.grounding.fields,
        tuple(sorted(fact.slots.items())),
    )


def _facts(offset: int, register: Register = Register.STANDARD) -> tuple[ExplainedFact, ...]:
    return ExplanationRenderer(rotated_templates(offset)).render(context_of(TRAIL), register).facts


# --- O esqueleto é o mesmo em todo giro ---------------------------------------


@pytest.mark.parametrize("offset", ROTATIONS)
def test_the_same_events_are_narrated_in_the_same_order(offset: int) -> None:
    reference = [fact.grounding.event_id for fact in _facts(0)]
    assert [fact.grounding.event_id for fact in _facts(offset)] == reference


@pytest.mark.parametrize("offset", ROTATIONS)
def test_every_fact_keeps_its_template_slots_and_grounding(offset: int) -> None:
    assert [_skeleton(fact) for fact in _facts(offset)] == [_skeleton(fact) for fact in _facts(0)]


@pytest.mark.parametrize("offset", ROTATIONS)
def test_the_simple_register_is_equally_unmoved(offset: int) -> None:
    """A costura de faixa etária não pode virar um segundo eixo de variação."""
    reference = [_skeleton(fact) for fact in _facts(0, Register.SIMPLE)]
    assert [_skeleton(fact) for fact in _facts(offset, Register.SIMPLE)] == reference


@pytest.mark.parametrize("offset", ROTATIONS)
def test_the_causal_link_survives_every_form(offset: int) -> None:
    """O elo do dossiê continua NOMEADO, e não apenas declarado no `Grounding`.

    Um fato encadeado tem `causation_id` entre seus campos e o substantivo da
    causa entre seus slots. Uma forma que perdesse o slot narraria "a temperatura
    mudou" sem o que veio antes — verdadeiro e mudo sobre a causa, que é o
    defeito que o M6.1 corrigiu ao escolher o representante do grupo.
    """
    chained = [fact for fact in _facts(offset) if fact.template_id == "T-CHAIN-CAUSED"]
    assert chained, "o cenário precisa ter cadeia para o teste dizer algo"
    for fact in chained:
        assert "causation_id" in fact.grounding.fields
        assert fact.slots["cause_subject"] in fact.text


@pytest.mark.parametrize("offset", ROTATIONS)
def test_every_slot_value_actually_appears_in_the_sentence(offset: int) -> None:
    """Um slot preenchido e não usado seria ancoragem decorativa.

    É a família do filtro fantasma de `planet_id`: o `Grounding` diria que a
    frase se apoia num campo que a frase não menciona, e a auditoria passaria a
    afirmar mais do que o texto contém.
    """
    for fact in _facts(offset):
        for slot, value in fact.slots.items():
            assert value in fact.text, f"{fact.template_id}: {slot!r} preenchido e não usado"


# --- E a contraprova: o texto, esse, muda -------------------------------------


def test_the_text_does_change_across_rotations() -> None:
    """Sem isto, tudo acima passaria com as formas nunca tendo girado."""
    summaries = {
        ExplanationRenderer(rotated_templates(offset)).render(context_of(TRAIL)).summary
        for offset in ROTATIONS
    }
    assert len(summaries) >= 3, "os giros produziram a mesma prosa — nada foi variado"
