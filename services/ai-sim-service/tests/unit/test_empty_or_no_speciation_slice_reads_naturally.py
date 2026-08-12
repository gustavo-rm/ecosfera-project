"""Uma era tranquila lê-se como era tranquila — sem drama e sem pedir desculpas.

O caso comum deste modelo, e não a exceção. A especiação é praticamente
inalcançável até a Fase 2: o limiar exige ~6 σ de um passo de mutação, e uma
corrida de 200 ticks emite dezenas de eventos e **nenhuma** especiação nas
sementes 2027 e 99 (`docs/decisions/deferred.md`). Uma era inteira sem linhagem
nova é o comportamento ESPERADO.

Duas tentações, e as duas fazem mal ao aluno:

* **Drama fabricado.** "Nada aconteceu, mas o planeta estava à beira de uma
  transformação" — afirma um estado que o dossiê não contém, e ensina que só vale
  a pena olhar quando há catástrofe.
* **Pedido de desculpas.** "Infelizmente não há muito a explicar" — transforma o
  caso normal em falha, e faz quem for avaliar o Tutor caçar um defeito de prompt
  ou de RAG que não existe.

O correto é a frase curta e neutra: o planeta seguiu sem acontecimentos notáveis.
"""

from __future__ import annotations

from tests.support_context import branching_cascade, life_emerged
from tests.support_explanation import context_of, explain, renderer

from ecosfera_ai.domain.consumers.explanation import Register
from ecosfera_ai.domain.consumers.narration import QUIET_PERIOD

# Marcas de drama fabricado e de desculpa. Curtas de propósito.
DRAMA = ("à beira", "prestes a", "dramática", "catástrofe iminente", "surpreendente")
APOLOGY = (
    "infelizmente",
    "não há muito",
    "desculpe",
    "não foi possível",
    "faltam dados",
    "não temos informação",
)


def test_an_empty_slice_still_produces_one_sentence() -> None:
    """Silêncio total seria regressão pedagógica — a era continua sendo narrada."""
    explanation = explain([])
    assert explanation.facts
    assert explanation.summary.strip()
    assert explanation.facts[0].template_id == QUIET_PERIOD


def test_the_quiet_sentence_manufactures_no_drama() -> None:
    text = explain([]).summary.lower()
    for phrase in DRAMA:
        assert phrase not in text, f"a era tranquila ganhou drama inventado: {phrase!r}"


def test_the_quiet_sentence_does_not_apologize() -> None:
    text = explain([]).summary.lower()
    for phrase in APOLOGY:
        assert phrase not in text, f"a era tranquila virou uma falha: {phrase!r}"


def test_the_quiet_sentence_asserts_nothing_about_any_event() -> None:
    """Ela fala da FATIA, não de um acontecimento — e a ancoragem diz isso."""
    fact = explain([]).facts[0]
    assert fact.grounding.event_id is None
    assert fact.grounding.fields == ("events",)
    assert not fact.slots


def test_an_era_without_speciation_simply_omits_the_topic() -> None:
    """O caso COMUM: há o que narrar, e nada disso é especiação.

    A ausência não vira frase. Dizer "nenhuma espécie nova surgiu" a cada era
    ensinaria que a especiação é o padrão de que este planeta está desviando —
    quando é o contrário.
    """
    explanation = explain(branching_cascade())
    text = explanation.summary.lower()

    assert explanation.facts, "a era tem eventos e precisava ser narrada"
    assert "ancestral comum" not in text
    assert "linhagem" not in text
    assert "especiação" not in text
    for phrase in APOLOGY + DRAMA:
        assert phrase not in text


def test_a_slice_with_only_one_quiet_marker_reads_plainly() -> None:
    """Um marco só, sem cascata: continua sendo uma frase, não um relatório."""
    explanation = explain([life_emerged(era=1, tick=40)])
    assert len(explanation.facts) == 1
    assert "a vida surgiu" in explanation.summary.lower()


def test_the_quiet_sentence_exists_in_the_simple_register_too() -> None:
    explanation = renderer().render(context_of([]), Register.SIMPLE)
    fact = explanation.facts[0]

    assert fact.register is Register.SIMPLE
    for phrase in APOLOGY + DRAMA:
        assert phrase not in fact.text.lower()


def test_the_quiet_explanation_is_not_flagged_as_empty_prose() -> None:
    """`is_empty` é sobre fatos narrados, e a era tranquila tem um."""
    explanation = explain([])
    assert not explanation.is_empty
    assert len(explanation.facts) == 1


def test_the_quiet_sentence_is_short() -> None:
    """Brevidade é parte da correção: uma era sem nada não merece um parágrafo."""
    assert len(explain([]).summary) < 120
