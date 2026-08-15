"""BIO-005 vale para o modelo exatamente como valia para o template.

A regra atravessou o marco inteiro: Fase 0 a enunciou, o M6.1 a impôs aos
templates, e aqui ela passa a valer para prosa que ninguém escreveu à mão.

O que muda é só a natureza da garantia. No M6.1 o vocabulário era conferido nos
ARQUIVOS, uma vez, e a partir daí toda frase renderizada era segura por
construção. Aqui a conferência é por SAÍDA, porque não há construção que garanta
nada — cada geração é um objeto novo que precisa passar pelo portão.

## A lista é a mesma, e este arquivo é onde isso é afirmado

A consolidação do M6.3 moveu `TELEOLOGICAL` para o domínio justamente para que o
verificador em tempo de execução e os testes de arquivo leiam a MESMA lista. Se
alguém acrescentar uma formulação proibida, ela passa a valer para os templates,
para o código, para os ADRs e para o modelo ao mesmo tempo.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import ScriptedModel, cascade_context, spec, use_case

from ecosfera_ai.domain.consumers.wording import (
    ABSOLUTE_FITNESS,
    TELEOLOGICAL,
    teleological_phrases_in,
)
from ecosfera_ai.domain.generation.grounding import verify_grounding

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()


# --- Uma única lista, compartilhada -------------------------------------------


def test_the_runtime_verifier_uses_the_same_list_the_file_guards_use() -> None:
    """A consolidação, afirmada por identidade de objeto e não por parecença."""
    from tests.unit import test_no_teleological_language as file_guard

    assert file_guard.TELEOLOGICAL is TELEOLOGICAL
    assert len(TELEOLOGICAL) >= 20, "a lista encolheu — alguém a substituiu por outra"


def test_the_two_axes_stay_separate() -> None:
    """Teleologia e aptidão absoluta são regras distintas, com listas distintas.

    "era inferior" não atribui intenção a ninguém: afirma uma ordenação que não
    existe. Fundi-las faria a mensagem de erro citar a regra errada, e uma
    mensagem que aponta a regra errada é pior que nenhuma para quem vai corrigir.
    """
    assert "era inferior" in ABSOLUTE_FITNESS
    assert "era inferior" not in TELEOLOGICAL
    assert "evoluiu para" in TELEOLOGICAL
    assert "evoluiu para" not in ABSOLUTE_FITNESS


# --- Toda formulação da lista é pega numa saída gerada ------------------------


@pytest.mark.parametrize("phrase", TELEOLOGICAL)
def test_every_forbidden_phrase_is_caught_in_generated_prose(phrase: str) -> None:
    """Exaustivo de propósito: uma lista com um item quebrado passaria despercebida.

    O teste do M6.1 conferia arquivos, onde a ausência das frases é o esperado.
    Aqui cada frase é USADA, e o portão tem de reagir a todas — inclusive à que
    alguém acrescentar amanhã, já que o caso vem da própria lista.
    """
    verdict = verify_grounding(
        f"No ciclo 100, {phrase} alguma coisa.", floor=FLOOR, context=CONTEXT, spec=spec()
    )
    assert not verdict.passed
    assert any(phrase in reason for reason in verdict.reasons)


@pytest.mark.parametrize("phrase", ABSOLUTE_FITNESS)
def test_every_absolute_fitness_phrase_is_caught(phrase: str) -> None:
    verdict = verify_grounding(
        f"A comunidade {phrase} naquele momento.", floor=FLOOR, context=CONTEXT, spec=spec()
    )
    assert not verdict.passed


def test_correct_wording_is_not_accused() -> None:
    """Contraprova: sem ela, "pega tudo" e "reprova tudo" seriam indistinguíveis.

    Esta frase traz a formulação CERTA — variação antes e sem propósito, ambiente
    decidindo depois — e tem de passar limpa.
    """
    correct = (
        "Surgiu uma mutação aleatória na população, e a característica aumentou a "
        "sobrevivência porque o ambiente daquele momento era assim."
    )
    assert teleological_phrases_in(correct) == ()
    assert verify_grounding(correct, floor=FLOOR, context=CONTEXT, spec=spec()).passed


# --- O caminho inteiro, e não só o verificador --------------------------------


async def test_teleological_generation_never_reaches_the_student() -> None:
    offender = "A comunidade desenvolveu resistência ao calor para sobreviver."
    result = await use_case(ScriptedModel(offender)).execute(floor=FLOOR, context=CONTEXT)

    assert result.fell_back
    assert result.text == FLOOR.summary
    assert teleological_phrases_in(result.text) == ()


async def test_the_floor_itself_is_free_of_forbidden_wording() -> None:
    """O recuo só é seguro porque o piso já é seguro.

    Se o piso do M6.1 pudesse conter formulação proibida, o caminho de recuo
    entregaria ao aluno exatamente o que o portão acabou de recusar.
    """
    assert teleological_phrases_in(FLOOR.summary) == ()
    for fact in FLOOR.facts:
        assert teleological_phrases_in(fact.text) == ()
