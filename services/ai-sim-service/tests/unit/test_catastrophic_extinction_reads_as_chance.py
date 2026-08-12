"""A extinção catastrófica NUNCA é narrada como falha de adaptação (ADR 0019).

É a lição pedagógica central deste marco, e a concepção equivocada que a
plataforma existe para desfazer é justamente a oposta: *"quem se extingue era
inferior"*. Até o M3 toda extinção do simulador tinha causa ecológica — cada peça
correta, e o conjunto ensinando a coisa errada, porque se toda morte é explicada
por um traço, morrer vira prova de inferioridade.

O M4 separou as famílias no motor. O M6.0 preservou a distinção como dado. Aqui
ela finalmente vira FRASE, e é aqui que ela pode se perder pela última vez: um
template descuidado desfaz, numa oração, o que três marcos construíram.

Duas coisas são verificadas, e a segunda é a que costuma faltar:

  1. a frase não culpa a comunidade;
  2. a frase NOMEIA o evento extremo que a matou — e o nomeia a partir do
     `causation_id` real, não de plausibilidade. Omitir a causa seria menos
     errado e ainda assim insuficiente: o aluno que não ouve o que aconteceu
     preenche o silêncio com a intuição espontânea, que é a concepção equivocada.
"""

from __future__ import annotations

from tests.support_context import branching_cascade
from tests.support_explanation import context_of, explain, renderer

from ecosfera_ai.domain.consumers.explanation import Register

CASCADE = branching_cascade()
METEOR, COOLING, _WILDFIRE, CATASTROPHIC, ECOLOGICAL = CASCADE

# Formulações que atribuem a morte a um defeito da comunidade. Curta de
# propósito: uma lista longa vira ruído e ninguém a mantém.
BLAMING = (
    "não conseguiu se adaptar",
    "nao conseguiu se adaptar",
    "não se adaptou",
    "falhou em se adaptar",
    "não era apta",
    "era inferior",
    "não aguentou o ambiente",
    "não tolerou",
)


def _catastrophic_text() -> str:
    explanation = explain(CASCADE)
    fact = next(f for f in explanation.facts if f.grounding.event_id == CATASTROPHIC.event_id)
    return fact.text.lower()


def test_the_catastrophic_extinction_is_narrated_at_all() -> None:
    """Sem isto, tudo o que segue passaria com o Tutor mudo."""
    explanation = explain(CASCADE)
    assert any(f.grounding.event_id == CATASTROPHIC.event_id for f in explanation.facts)


def test_it_never_blames_the_community_for_its_own_death() -> None:
    text = _catastrophic_text()
    for phrase in BLAMING:
        assert phrase not in text, (
            f"a extinção CATASTRÓFICA foi narrada como falha da comunidade ({phrase!r}): {text!r}"
        )


def test_it_says_adaptation_would_not_have_saved_it() -> None:
    """A lição inteira cabe nesta oração, e é ela que inverte a intuição.

    Note que a palavra "adaptada" APARECE na frase, e é o contrário de culpar: a
    oração existe para dizer que a adaptação não teria mudado o desfecho. Uma
    busca literal por "adaptada" acusaria justamente a frase certa — por isso o
    que se verifica é a formulação completa.
    """
    assert "por mais bem adaptada" in _catastrophic_text()


def test_it_names_the_extreme_event_that_caused_it() -> None:
    """E o nome sai do `causation_id` REAL, não da plausibilidade."""
    text = _catastrophic_text()
    assert "meteoro" in text, f"a extinção catastrófica não nomeia o gatilho: {text!r}"


def test_the_named_trigger_is_the_event_the_chain_points_to() -> None:
    """O elo é o que o M4 quase perdeu: apontava para o clima do mesmo tick.

    Aqui se afirma que a frase nomeia o METEORO, e não o resfriamento que ocorreu
    entre ele e a extinção. Nomear o resfriamento produziria "morreu porque
    esfriou" — verdadeiro no tempo, falso na causa, e indistinguível de uma
    extinção ecológica para quem só lesse a explicação.
    """
    text = _catastrophic_text()
    assert "temperatura" not in text, (
        f"a catástrofe foi atribuída ao clima, e não ao evento que a causou: {text!r}"
    )
    fact = next(f for f in explain(CASCADE).facts if f.grounding.event_id == CATASTROPHIC.event_id)
    assert fact.template_id == "T-EXTINCTION-CATASTROPHIC"
    assert "causation_id" in fact.grounding.fields


def test_a_catastrophe_whose_trigger_left_the_slice_does_not_invent_one() -> None:
    """Sem o gatilho no dossiê, a frase diz "veio de fora" — e não "um meteoro".

    É a diferença entre não saber e inventar. O template sem gatilho existe
    exatamente para este caso, e a asserção é que ele seja usado em vez de
    emprestar da plausibilidade um meteoro que o log não tem.
    """
    only_extinction = explain([CATASTROPHIC])
    fact = only_extinction.facts[0]

    assert fact.template_id == "T-EXTINCTION-CATASTROPHIC-UNTRACED"
    assert "meteoro" not in fact.text.lower()
    assert "de fora" in fact.text.lower()
    for phrase in BLAMING:
        assert phrase not in fact.text.lower()


def test_the_simple_register_keeps_the_lesson() -> None:
    """Encurtar a frase não pode custar a lição — é o risco de simplificar."""
    explanation = renderer().render(context_of(CASCADE), Register.SIMPLE)
    fact = next(f for f in explanation.facts if f.grounding.event_id == CATASTROPHIC.event_id)
    text = fact.text.lower()

    assert fact.register is Register.SIMPLE
    assert "não foi culpa dela" in text
    for phrase in BLAMING:
        assert phrase not in text


def test_the_two_extinctions_of_the_same_era_read_differently() -> None:
    """A contraprova: uniformizar as duas em QUALQUER direção é o defeito."""
    explanation = explain(CASCADE)
    catastrophic = next(
        f for f in explanation.facts if f.grounding.event_id == CATASTROPHIC.event_id
    )
    ecological = next(f for f in explanation.facts if f.grounding.event_id == ECOLOGICAL.event_id)
    assert catastrophic.text != ecological.text
    assert catastrophic.template_id != ecological.template_id
