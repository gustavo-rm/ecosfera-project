"""O portão anti-alucinação: uma saída que INVENTA é reprovada e não chega ao aluno.

O teste central do M6.3, e o equivalente não-determinístico do
`test_every_claim_is_grounded_in_context` do M6.1. Lá a fundamentação era
garantida POR CONSTRUÇÃO — a frase saía de um template e todo valor vinha de um
slot. Aqui não há construção que garanta nada, e por isso a conferência acontece
DEPOIS, contra a mesma fonte que o template usava.

Cada caso é uma saída maliciosa escrita à mão. Um modelo real produziria estas
falhas raramente e de modo imprevisível; roteirizá-las é o único jeito de afirmar
que o portão as pega TODA vez, e não na vez em que se teve sorte de observar.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import ScriptedModel, cascade_context, spec, use_case

from ecosfera_ai.domain.generation.grounding import verify_grounding

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()


def _verdict(generated: str) -> object:
    return verify_grounding(generated, floor=FLOOR, context=CONTEXT, spec=spec())


# --- Números inventados --------------------------------------------------------


def test_a_number_that_is_not_in_the_floor_is_refused() -> None:
    """A alucinação mais comum de um modelo pequeno: a quantidade plausível.

    "300 espécies" soa perfeitamente razoável numa explicação sobre extinção. O
    dossiê daquele planeta não contém esse número, e é só isso que importa.
    """
    verdict = _verdict("No ciclo 100, um meteoro caiu e 300 espécies desapareceram.")
    assert not verdict.passed
    assert any("300" in reason for reason in verdict.reasons)


def test_the_numbers_that_come_from_the_floor_are_accepted() -> None:
    """Contraprova: sem ela, "reprova números" poderia significar "reprova tudo"."""
    verdict = _verdict("No ciclo 100, a queda de um meteoro atingiu o planeta.")
    assert verdict.passed, verdict.reasons


# --- Acontecimentos inventados -------------------------------------------------


def test_an_event_absent_from_the_dossier_is_refused() -> None:
    """O pior caso: prosa fluente sobre algo que não aconteceu com aquele aluno.

    O dossiê da cascata não tem erupção supervulcânica. Uma frase que a cite está
    contando a história de outro planeta com a confiança de quem leu o log certo.
    """
    verdict = _verdict("Uma erupção supervulcânica cobriu o céu de cinzas naquele ciclo.")
    assert not verdict.passed
    assert any("supervulcânica" in reason for reason in verdict.reasons)


def test_an_event_that_is_in_the_dossier_is_accepted() -> None:
    """O meteoro ESTÁ na cascata — citá-lo é fidelidade, não invenção."""
    verdict = _verdict("A queda de um meteoro foi o que começou tudo.")
    assert verdict.passed, verdict.reasons


# --- Formulação proibida -------------------------------------------------------


@pytest.mark.parametrize(
    "offender",
    [
        "A comunidade desenvolveu resistência ao calor para sobreviver.",
        "A espécie evoluiu para tolerar o novo ambiente.",
        "A espécie desenvolveu uma casca mais grossa.",
    ],
)
def test_teleological_output_is_refused(offender: str) -> None:
    """BIO-005 vale para o modelo exatamente como valia para o template.

    O terceiro caso é o que a consolidação do M6.3 acrescentou: até então a lista
    de imposição não alcançava "a espécie desenvolveu" sozinho, embora a VOC-001
    já ensinasse ao Tutor que a formulação é proibida.
    """
    verdict = _verdict(offender)
    assert not verdict.passed
    assert any("BIO-005" in reason for reason in verdict.reasons)


def test_absolute_fitness_output_is_refused() -> None:
    """Q5: nega-se a aptidão ABSOLUTA, e o modelo não pode reintroduzi-la."""
    verdict = _verdict("A comunidade que desapareceu era inferior à que ficou.")
    assert not verdict.passed
    assert any("Q5" in reason for reason in verdict.reasons)


# --- O veredito reprovado não chega ao aluno -----------------------------------


async def test_a_refused_generation_never_reaches_the_student() -> None:
    """Reprovar não basta: o texto reprovado tem de sumir do caminho.

    A afirmação é sobre o CAMINHO, não sobre o verificador. Um portão que reprova
    e depois entrega assim mesmo é decoração.
    """
    invented = "No ciclo 100, um meteoro caiu e 300 espécies desapareceram."
    result = await use_case(ScriptedModel(invented)).execute(floor=FLOOR, context=CONTEXT)

    assert result.fell_back
    assert result.text == FLOOR.summary
    assert invented not in result.text
    assert "300" in result.fallback_reason, "o motivo tem de guardar o caso para o M6.4"


def test_every_reason_is_reported_and_not_just_the_first() -> None:
    """O M6.4 monta conjunto de avaliação a partir daqui.

    Saber que uma saída violou três regras é diferente de saber que violou
    alguma, e a diferença aparece justamente ao decidir o que consertar primeiro.
    """
    verdict = _verdict(
        "Uma erupção supervulcânica matou 300 espécies, e a que ficou desenvolveu resistência."
    )
    assert len(verdict.reasons) >= 3, verdict.reasons
