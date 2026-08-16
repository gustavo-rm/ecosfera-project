"""Nenhum APROVADO afirma mais conferência do que houve.

A disciplina que o M6.3 aplicou ao eixo da disponibilidade, agora aplicada ao
eixo da cobertura. Lá, um veredito de dois estados obrigava "não avaliado" a se
disfarçar de "reprovado", e a correção foi um terceiro estado. Aqui o problema é
o simétrico: um APROVADO se passava por conferência completa quando três tipos de
evento não eram conferidos de forma alguma.

O sintoma era invisível por construção. Uma prosa inventando um `TemperatureShift`
recebia exatamente o mesmo "passou" de uma prosa impecável, e nada no objeto
distinguia as duas — que é como uma lacuna declarada em ADR volta a ser esquecida.

`DetectionCoverage` torna a lacuna parte da resposta. O M6.4 mede taxa de
aprovação com ela: um "passou" de cobertura parcial não vale o mesmo que um
"passou" completo, e a diferença tem de estar no dado, não na memória de quem
leu o ADR.
"""

from __future__ import annotations

from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import cascade_context, spec

from ecosfera_ai.domain.generation.anchoring import DetectionCoverage, GroundingVerdict
from ecosfera_ai.domain.generation.grounding import UNCHECKED_EVENT_TYPES, verify_grounding

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()
FAITHFUL = "No ciclo 100, a queda de um meteoro atingiu o planeta."


# --- A cobertura viaja com todo veredito --------------------------------------


def test_a_passing_verdict_declares_what_was_checked() -> None:
    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec())

    assert verdict.passed
    assert verdict.coverage.checked, "um aprovado sem cobertura declarada não diz nada"
    assert "MeteorImpact" in verdict.coverage.checked
    assert "SpeciationOccurred" in verdict.coverage.checked, "fechado no M6.4"
    assert "TemperatureShift" in verdict.coverage.checked, "fechado no M6.4"
    assert "PopulationDeclined" in verdict.coverage.checked, "fechado no M6.4"


def test_the_types_that_remain_unchecked_are_named_not_hidden() -> None:
    """A honestidade exige nomear o que falta, e não apenas contar."""
    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec())

    assert verdict.coverage.unchecked == UNCHECKED_EVENT_TYPES
    assert not verdict.coverage.is_complete
    assert "TrophicCollapse" in verdict.coverage.unchecked


def test_the_summary_of_a_partial_pass_says_so_out_loud() -> None:
    """Quem lê o resumo de uma linha não pode ficar com a impressão errada.

    É a mesma correção do roteiro de fumaça do M6.3, no outro eixo: o resumo é o
    que a pessoa lê, e ele não pode dizer "passou" quando passou parcialmente.
    """
    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec())

    assert "cobertura parcial" in verdict.summary
    assert verdict.summary != "passou"


def test_a_complete_coverage_pass_reads_plainly() -> None:
    """Contraprova: quando não falta nada, o resumo não inventa ressalva.

    Sem isto, "o resumo avisa" poderia significar "o resumo sempre avisa", e o
    aviso perderia o sentido por nunca distinguir caso nenhum.
    """
    complete = GroundingVerdict(passed=True, coverage=DetectionCoverage(checked=frozenset({"X"})))
    assert complete.coverage.is_complete
    assert complete.summary == "passou"


# --- A cobertura não maquia reprovação nem ausência ---------------------------


def test_a_rejected_verdict_still_reads_as_rejected() -> None:
    """Cobertura parcial não abranda uma reprovação — são eixos distintos."""
    verdict = verify_grounding(
        "Uma erupção supervulcânica matou 300 espécies.",
        floor=FLOOR,
        context=CONTEXT,
        spec=spec(),
    )
    assert not verdict.passed
    assert verdict.summary == "reprovado"


def test_the_no_attempt_state_survives_the_new_field() -> None:
    """O terceiro estado do M6.3 continua distinguível depois do quarto eixo."""
    absent = GroundingVerdict.not_evaluated()

    assert not absent.evaluated
    assert "não avaliado" in absent.summary
    assert absent.to_dict()["coverage"]["checked"] == []


def test_the_serialised_form_carries_the_coverage_for_the_evaluation_set() -> None:
    """O conjunto de avaliação do M6.4 lê isto; se não serializar, não mede."""
    payload = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec()).to_dict()

    assert payload["passed"] is True
    assert payload["coverage"]["complete"] is False
    assert "TrophicCollapse" in payload["coverage"]["unchecked"]
