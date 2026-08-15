"""A contraprova do portão: uma reescrita FIEL passa, e chega ao aluno.

Sem este arquivo, tudo o que o M6.3 promete poderia ser cumprido por um
verificador que reprovasse tudo. O recuo seria universal, o aluno leria sempre o
piso do M6.1, e todo teste de "não deixa passar invenção" continuaria verde — a
camada inteira seria um custo sem benefício, e nada apontaria isso.

É o mesmo cuidado que o M6.1 tomou com cada filtro do teste de fundamentação: uma
regra que nunca aceita nada não está verificando, está bloqueando.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import (
    ScriptedModel,
    cascade_context,
    sibling_passages,
    spec,
    use_case,
)

from ecosfera_ai.domain.generation.grounding import verify_grounding

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()

# Reescritas legítimas: mesmo conteúdo factual, registro mais simples. Nenhuma
# acrescenta acontecimento, número ou causa.
FAITHFUL = (
    "No ciclo 100, a queda de um meteoro atingiu o planeta.",
    "Um meteoro caiu e, logo depois, um grande incêndio começou.",
    "A queda de um meteoro veio primeiro; a mudança de temperatura veio depois dela.",
    "No ciclo 100 caiu um meteoro. A comunidade que vivia ali desapareceu de uma vez, "
    "por mais bem adaptada que estivesse ao ambiente em que vivia.",
    "Depois da queda do meteoro, a temperatura do planeta mudou.",
)


@pytest.mark.parametrize("generation", FAITHFUL)
def test_a_faithful_rewrite_passes(generation: str) -> None:
    verdict = verify_grounding(generation, floor=FLOOR, context=CONTEXT, spec=spec())
    assert verdict.passed, f"{generation!r} foi reprovada: {verdict.reasons}"
    assert verdict.reasons == ()


@pytest.mark.parametrize("generation", FAITHFUL)
async def test_a_faithful_rewrite_is_what_the_student_reads(generation: str) -> None:
    """Passar não basta: o texto do modelo tem de ser o entregue, e não o piso."""
    result = await use_case(ScriptedModel(generation)).execute(floor=FLOOR, context=CONTEXT)

    assert not result.fell_back
    assert result.text == generation
    assert result.text != result.floor_text
    assert result.is_model_authored
    assert result.model_name == "modelo-de-teste"


async def test_the_provenance_survives_a_successful_generation() -> None:
    """Sucesso não pode apagar a trilha: o M6.4 audita as saídas boas também."""
    rule, correction = sibling_passages()
    result = await use_case(ScriptedModel(FAITHFUL[0])).execute(
        floor=FLOOR, context=CONTEXT, passages=[rule, correction]
    )

    assert not result.fell_back
    assert result.floor_text == FLOOR.summary, "o piso reescrito continua registrado"
    assert [source.entry_id for source in result.register_sources] == ["VOC-006", "VAL-Q8"]
    assert result.fallback_reason == ""
    assert result.to_dict()["verdict"]["passed"] is True


def test_omitting_a_number_is_allowed_because_only_adding_is_invention() -> None:
    """Assimetria deliberada, e o que torna a regra de números sem falso positivo.

    Uma reescrita mais simples pode legitimamente não citar o ciclo. O que ela
    não pode é citar um ciclo que não houve.
    """
    without_numbers = "A queda de um meteoro atingiu o planeta e a comunidade desapareceu."
    assert verify_grounding(without_numbers, floor=FLOOR, context=CONTEXT, spec=spec()).passed


def test_the_gate_is_not_vacuously_permissive() -> None:
    """A contraprova da contraprova: o portão que aceita as de cima recusa uma ruim.

    Sem isto, este arquivo poderia estar medindo um verificador que aceita tudo.
    """
    verdict = verify_grounding(
        "Uma erupção supervulcânica matou 400 espécies.",
        floor=FLOOR,
        context=CONTEXT,
        spec=spec(),
    )
    assert not verdict.passed
