"""As regras da Fase 0 valem para TODA forma, e não só para a primeira (M6.5).

Uma forma alternativa é prosa nova que chega ao aluno, e ela entra no arquivo
depois de todos os testes que guardam a prosa antiga. Se a verificação continuasse
olhando só a frase que a posição escolheu, acrescentar uma forma seria acrescentar
texto sem revisão — e o lugar mais fácil de errar é justamente aqui: reescrever
"por mais bem adaptada que ela estivesse" com outras palavras é, uma vez em duas,
escrever que a comunidade não deu conta.

Três eixos, e cada um com sua lista canônica, pela razão de sempre: a mensagem de
erro precisa apontar a regra certa.

  * **BIO-005** — intenção. Nenhuma forma diz que alguém quis, buscou ou criou.
  * **Q5** — aptidão absoluta. Nenhuma forma ordena comunidades por valor.
  * **BIO-001** — descendência linear, com UMA exceção declarada abaixo.

## A exceção do BIO-001, e por que ela é derivada e não escrita à mão

O template da especiação contém "versão antiga da" — e o contém para NEGAR: "…
são irmãs, e nenhuma das duas é a versão antiga da outra". É menção, não uso, e é
a frase que mais serve à Fase 0 no arquivo inteiro. O teste não a lista como
exceção pontual: ele afirma que a única forma com marca de descendência linear é
uma que também traz a negação. Uma exceção escrita à mão envelheceria; esta
descreve a propriedade que torna a frase legítima.
"""

from __future__ import annotations

import re

import pytest
from tests.support_explanation import templates

from ecosfera_ai.domain.consumers.explanation import Register
from ecosfera_ai.domain.consumers.templates import ExplanationTemplate
from ecosfera_ai.domain.consumers.wording import (
    absolute_fitness_phrases_in,
    linear_descent_phrases_in,
    teleological_phrases_in,
)

SLOT = re.compile(r"\{(\w+)\}")

# Formulações que culpam a comunidade pela própria morte. A lista é a mesma de
# `test_catastrophic_extinction_reads_as_chance`, e o eixo é o do ADR 0019: um
# evento extremo não seleciona, ele elimina.
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

CATASTROPHIC = "T-EXTINCTION-CATASTROPHIC"


def _every_form() -> list[ExplanationTemplate]:
    table = templates()
    return [form for forms in table.templates.values() for form in forms]


def _rendered(form: ExplanationTemplate) -> str:
    """A forma com os slots preenchidos por valores REAIS do vocabulário.

    Conferir o template cru deixaria passar o erro que só aparece montado: um
    substantivo entra com artigo e gênero próprios, e é depois da substituição que
    a frase existe como o aluno a lê.
    """
    table = templates()
    noun = table.nouns["SpeciesExtinct"]
    mechanism = table.mechanisms["THERMAL_INTOLERANCE"]
    values = {
        "tick": "100",
        "occurrences": "3",
        "subject": table.nouns["TemperatureShift"],
        "cause_subject": table.nouns["MeteorImpact"],
        "trigger": table.nouns["MeteorImpact"],
        "mechanism": mechanism,
    }
    return form.render({slot: values.get(slot, noun) for slot in SLOT.findall(form.text)}).lower()


# --- Os dois eixos que valem para o arquivo inteiro ---------------------------


def test_no_form_anywhere_attributes_intent() -> None:
    for form in _every_form():
        found = teleological_phrases_in(_rendered(form))
        assert not found, f"{form.template_id} ({form.register.value}): BIO-005 {found}"


def test_no_form_anywhere_ranks_communities_by_worth() -> None:
    for form in _every_form():
        found = absolute_fitness_phrases_in(_rendered(form))
        assert not found, f"{form.template_id} ({form.register.value}): Q5 {found}"


# --- O eixo com uma exceção, e a exceção descrita em vez de listada -----------


def test_the_only_form_with_a_descent_phrase_is_the_one_that_denies_it() -> None:
    """Menção, e não uso — e a propriedade que separa as duas está no texto."""
    for form in _every_form():
        found = linear_descent_phrases_in(_rendered(form))
        if not found:
            continue
        assert "nenhuma" in form.text.lower(), (
            f"{form.template_id} afirma descendência linear sem negá-la: {found}"
        )


# --- E a lição do ADR 0019 sobrevive a cada forma da catástrofe ---------------


@pytest.mark.parametrize("register", [Register.STANDARD, Register.SIMPLE])
def test_no_catastrophic_form_blames_the_community(register: Register) -> None:
    for form in templates().variants_of(CATASTROPHIC, register):
        text = _rendered(form)
        for phrase in BLAMING:
            assert phrase not in text, f"{form.template_id} forma {text!r} culpa a comunidade"


def test_every_standard_catastrophic_form_says_adaptation_would_not_have_saved_it() -> None:
    """A oração que inverte a intuição do aluno está em TODAS as formas.

    É a razão pela qual as formas alternativas variam a ABERTURA e conservam esta
    oração intacta: reescrevê-la de três jeitos seria arriscar, em nome da forma,
    a única frase do arquivo que desfaz "quem se extingue era inferior".
    """
    forms = templates().variants_of(CATASTROPHIC, Register.STANDARD)
    assert len(forms) >= 3
    for form in forms:
        text = _rendered(form)
        assert "por mais bem adaptada" in text, f"a forma {text!r} perdeu a lição do ADR 0019"
        assert "não escolhe quem sobrevive" in text


def test_every_standard_catastrophic_form_still_names_the_trigger() -> None:
    """Omitir a causa seria menos errado e ainda assim insuficiente.

    O aluno que não ouve o que aconteceu preenche o silêncio com a intuição
    espontânea, que é a concepção equivocada. Vale para toda forma.
    """
    for form in templates().variants_of(CATASTROPHIC, Register.STANDARD):
        assert "{trigger}" in form.text
