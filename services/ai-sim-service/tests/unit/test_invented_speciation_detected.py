"""Especiação inventada é detectada — o caso de maior risco do M6.4, Task 0.

O ADR 0028 declarou que `SpeciationOccurred` passava sem verificação, e é o pior
lugar possível para uma lacuna: é exatamente o que a Fase 0 (BIO-001) existe para
proteger, e as duas garantias que o projeto já tem NÃO alcançam prosa livre.

  * `SpeciationFact` recusa "A deu origem a B" no TIPO — mas o tipo não escreve a
    frase que o aluno lê;
  * o template do M6.1 não tem slot de linhagem — mas o modelo não é obrigado a
    usar template algum.

Um modelo escreve a escada de progresso em português sem tocar em nenhuma das
duas. É esse buraco que este arquivo fecha.

## A alavanca estrutural

O modelo **nunca recebe identificador de linhagem**. O prompt leva o resumo do
piso e as passagens; o piso não tem slot de linhagem. Logo, um identificador na
prosa não veio do material — foi inventado, inclusive se coincidir com um real.
"""

from __future__ import annotations

import pytest
from tests.support import speciation_event
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import cascade_context, spec

from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.generation.fact_claims import speciation_problems_in
from ecosfera_ai.domain.generation.grounding import verify_grounding

# A cascata do meteoro NÃO tem especiação — é o cenário em que toda afirmação de
# divisão de linhagem é invenção.
NO_SPECIATION = cascade_context()
FLOOR = explain(list(branching_cascade()))


def _with_speciation() -> FactualContext:
    event = speciation_event()
    return FactualContext.of("planet-spec", ContextSlice.of_era(event.occurred_at.era), (event,))


def _verdict(text: str, context: FactualContext = NO_SPECIATION) -> object:
    return verify_grounding(text, floor=FLOOR, context=context, spec=spec())


# --- O cenário é o que se pensa que é -----------------------------------------


def test_the_cascade_really_has_no_speciation() -> None:
    """Contraprova do cenário: sem isto o arquivo afirmaria sobre o log errado."""
    assert not NO_SPECIATION.speciations
    assert _with_speciation().speciations, "o cenário de controle precisa ter uma"


# --- Especiação afirmada onde não houve ---------------------------------------


@pytest.mark.parametrize(
    "invented",
    [
        "Naquele período, a população se dividiu em duas linhagens irmãs.",
        "Surgiram duas linhagens a partir da população que vivia ali.",
        "Houve uma especiação logo depois da queda do meteoro.",
        "Uma nova espécie surgiu no planeta naquele ciclo.",
    ],
)
def test_asserting_a_speciation_that_did_not_happen_is_caught(invented: str) -> None:
    """A pior alucinação deste sistema: fluente, plausível, e falsa sobre o planeta."""
    problems = speciation_problems_in(invented, NO_SPECIATION)
    assert problems, f"passou sem detecção: {invented!r}"
    assert any("BIO-001" in problem for problem in problems)

    assert not _verdict(invented).passed


def test_the_same_sentence_is_accepted_when_the_speciation_really_happened() -> None:
    """Contraprova: a detecção é sobre o LOG, e não sobre a palavra.

    Sem isto, "detecta especiação inventada" poderia significar "proíbe falar de
    especiação" — e o Tutor emudeceria justamente sobre o tema que a Fase 0 quer
    que ele saiba contar.
    """
    faithful = "Naquele período, a população se dividiu em duas linhagens irmãs."
    assert speciation_problems_in(faithful, _with_speciation()) == ()


def test_the_vocabulary_rule_itself_is_not_mistaken_for_an_assertion() -> None:
    """VOC-002 entra no prompt como registro; ecoá-la não é afirmar um evento.

    A regra fala de "ancestral comum" e "linhagens" no abstrato. Se a detecção
    disparasse com a palavra solta, toda orientação de registro sobre especiação
    reprovaria a saída — e o corpus do M6.2 deixaria de poder ensinar o assunto.
    """
    echoed = (
        "É importante lembrar que espécies irmãs compartilham um ancestral comum, "
        "e que nenhuma é a versão antiga da outra."
    )
    assert speciation_problems_in(echoed, NO_SPECIATION) == ()


# --- Identificadores vazados ---------------------------------------------------


def test_a_leaked_lineage_identifier_is_caught() -> None:
    """O modelo nunca recebe id de linhagem; um id na prosa é invenção pura."""
    leaked = (
        "A linhagem 3f2a9c1e-4b5d-5e6f-8a9b-0c1d2e3f4a5b seguiu caminho próprio depois da divisão."
    )
    problems = speciation_problems_in(leaked, _with_speciation())
    assert problems
    assert any("identificador" in problem for problem in problems)


def test_a_leaked_envelope_role_is_caught() -> None:
    """`lineage:` e `ancestor:` são forma do envelope §4, não língua para o aluno."""
    leaked = "O ancestor:pop-antiga se dividiu naquele ciclo."
    problems = speciation_problems_in(leaked, _with_speciation())
    assert problems
    assert any("envelope" in problem for problem in problems)


# --- Descendência linear na prosa (BIO-001) -----------------------------------


@pytest.mark.parametrize(
    "ladder",
    [
        "A espécie antiga deu origem a uma espécie nova e mais adaptada.",
        "A primeira linhagem se transformou em outra ao longo do tempo.",
        "A linhagem atual descende de uma que existia antes.",
        "A comunidade nova é a versão moderna da antiga.",
    ],
)
def test_linear_descent_wording_is_caught_even_where_speciation_happened(ladder: str) -> None:
    """A escada de progresso é erro de FORMA, e vale mesmo com o log a favor.

    Este é o ponto que separa esta verificação da anterior: mesmo num planeta em
    que a divisão realmente ocorreu, contá-la como "a antiga virou a nova" ensina
    exatamente a concepção que a plataforma existe para desfazer.
    """
    verdict = verify_grounding(ladder, floor=FLOOR, context=_with_speciation(), spec=spec())
    assert not verdict.passed
    assert any("BIO-001" in reason for reason in verdict.reasons)


def test_the_correct_sibling_framing_is_not_accused() -> None:
    """Contraprova do eixo: a formulação CERTA passa limpa."""
    correct = (
        "As duas linhagens compartilham um ancestral comum e seguem caminhos "
        "separados a partir dele: são irmãs."
    )
    assert verify_grounding(correct, floor=FLOOR, context=_with_speciation(), spec=spec()).passed
