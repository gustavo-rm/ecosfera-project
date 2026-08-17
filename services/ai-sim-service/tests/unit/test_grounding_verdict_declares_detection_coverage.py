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
from ecosfera_ai.domain.generation.grounding import verify_grounding

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()
FAITHFUL = "No ciclo 100, a queda de um meteoro atingiu o planeta."


# --- A cobertura viaja com todo veredito --------------------------------------


def test_a_passing_verdict_declares_what_was_checked() -> None:
    """A cobertura nomeia os tipos DESTE dossiê que foram conferidos.

    **Reescrito no encerramento do M6.4.** A versão anterior cobrava aqui a
    presença de `SpeciationOccurred` e `PopulationDeclined`, que o Task 0 fechou —
    mas a cascata não tem nenhum dos dois, e cobrá-los de um veredito sobre ela
    era confundir "o que o sistema sabe conferir" com "o que foi conferido nesta
    tentativa". A primeira pergunta é de `checkable_event_types`, e vive em
    `test_detection_coverage_is_scoped_to_the_dossier`.
    """
    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec())
    present = {event.event_type for event in CONTEXT.events}

    assert verdict.passed
    assert verdict.coverage.checked, "um aprovado sem cobertura declarada não diz nada"
    assert verdict.coverage.checked == present, "a cascata é inteiramente verificável"
    assert "MeteorImpact" in verdict.coverage.checked
    assert "TemperatureShift" in verdict.coverage.checked, "fechado no M6.4"
    assert "SpeciesExtinct" in verdict.coverage.checked, "fechado no encerramento"


def test_the_types_that_remain_unchecked_are_named_not_hidden() -> None:
    """A honestidade exige nomear o que falta, e não apenas contar.

    **Reescrito no encerramento do M6.4.** A versão anterior comparava contra a
    lista de TODOS os tipos sem checagem, e por isso afirmava que a cascata tinha
    cobertura parcial. Depois de a métrica passar a falar do dossiê, a cascata é
    inteiramente verificável — o que o teste cobra agora é que, quando falta
    algo, o que falta seja NOMEADO. Ver
    `test_detection_coverage_is_scoped_to_the_dossier` para os dois lados.
    """
    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec())

    assert verdict.coverage.checked, "um aprovado sem cobertura declarada não diz nada"
    assert verdict.coverage.unchecked == frozenset(), "a cascata é toda verificável"
    assert verdict.coverage.to_dict()["checked"] == sorted(verdict.coverage.checked)


def test_the_summary_of_a_partial_pass_says_so_out_loud() -> None:
    """Quem lê o resumo de uma linha não pode ficar com a impressão errada.

    É a mesma correção do roteiro de fumaça do M6.3, no outro eixo: o resumo é o
    que a pessoa lê, e ele não pode dizer "passou" quando passou parcialmente.
    """
    partial = GroundingVerdict(
        passed=True,
        coverage=DetectionCoverage(
            checked=frozenset({"MeteorImpact"}), unchecked=frozenset({"TrophicCollapse"})
        ),
    )

    assert "cobertura parcial" in partial.summary
    assert partial.summary != "passou"


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
    """O conjunto de avaliação do M6.4 lê isto; se não serializar, não mede.

    **Reescrito no encerramento do M6.4:** a cascata agora serializa cobertura
    COMPLETA, porque todos os seus tipos são verificáveis. O que este teste cobra
    é que os três campos atravessem a serialização — não um valor em particular.
    """
    payload = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec()).to_dict()

    assert payload["passed"] is True
    assert payload["coverage"]["complete"] is True
    assert payload["coverage"]["unchecked"] == []
    assert "MeteorImpact" in payload["coverage"]["checked"]
