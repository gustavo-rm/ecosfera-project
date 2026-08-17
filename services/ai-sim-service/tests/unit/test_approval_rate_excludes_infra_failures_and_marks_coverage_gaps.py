"""A taxa de aprovação mede o MODELO, e não a infraestrutura nem a própria fé.

Três coisas que uma taxa ingênua esconderia, e que este arquivo cobra uma a uma.

**Indisponibilidade não é alucinação.** Um recuo por rede caída não diz nada sobre
o modelo. Somá-lo às reprovações faria a taxa PIORAR quando o Ollama cai — a
leitura exatamente invertida, e a mesma confusão que o terceiro estado do veredito
já corrigiu uma vez no M6.3.

**Aprovação com cobertura parcial não vale o mesmo.** Cinco tipos de evento seguem
sem checagem de invenção. Uma saída pode passar sem que ninguém tenha conferido se
ela inventou um `TrophicCollapse`, e reportar isso no mesmo número de uma
aprovação completa é afirmar mais verificação do que houve.

**A forma do piso confunde a comparação.** O ADR 0028 registrou que o piso da
cascata é um parágrafo repetitivo de cinco frases. Numa média única, ninguém
distingue queda de qualidade do modelo de efeito da forma do texto que ele
recebeu.
"""

from __future__ import annotations

from ecosfera_ai.application.generation.evaluation import evaluate
from ecosfera_ai.application.generation.rejection_log import (
    GenerationAttempt,
    InMemoryAttemptRecorder,
)

COMPLETE = {"passed": True, "evaluated": True, "reasons": [], "coverage": {"complete": True}}
PARTIAL = {"passed": True, "evaluated": True, "reasons": [], "coverage": {"complete": False}}
NOT_EVALUATED = {"passed": False, "evaluated": False, "reasons": [], "coverage": {}}


def _attempt(
    scenario: str, verdict: dict[str, object], reasons: list[str] | None = None
) -> GenerationAttempt:
    payload = dict(verdict)
    if reasons is not None:
        payload = {**payload, "reasons": reasons, "passed": False, "evaluated": True}
    return GenerationAttempt(
        recorded_at="2026-08-15T00:00:00+00:00",
        planet_id="planet-eval",
        scenario=scenario,
        model_name="llama3.2:1b",
        generated="prosa",
        floor_text="piso",
        fell_back=not bool(payload.get("passed")),
        fallback_reason="",
        verdict=payload,
    )


# --- Indisponibilidade fica FORA do denominador -------------------------------


def test_an_infrastructure_failure_is_not_counted_as_a_rejection() -> None:
    """Duas aprovações e uma queda de rede dão 100%, e não 66%."""
    report = evaluate(
        [
            _attempt("cascata", COMPLETE),
            _attempt("cascata", COMPLETE),
            _attempt("cascata", NOT_EVALUATED),
        ]
    )
    scenario = report.scenarios[0]

    assert scenario.attempts == 3
    assert scenario.evaluated == 2, "a tentativa sem geração não entra no denominador"
    assert scenario.infrastructure_failures == 1
    assert scenario.approval_rate == 1.0
    assert report.overall_approval_rate == 1.0


def test_nothing_evaluated_is_not_the_same_as_zero_percent() -> None:
    """`None` e 0.0 dizem coisas diferentes, e confundi-las já custou uma vez."""
    report = evaluate([_attempt("cascata", NOT_EVALUATED)])

    assert report.scenarios[0].approval_rate is None
    assert report.overall_approval_rate is None


def test_a_real_rejection_does_lower_the_rate() -> None:
    """Contraprova: sem ela, "exclui falhas de infra" poderia excluir tudo."""
    report = evaluate(
        [_attempt("cascata", COMPLETE), _attempt("cascata", {}, reasons=["número inventado"])]
    )
    assert report.scenarios[0].approval_rate == 0.5
    assert report.scenarios[0].rejected == 1


# --- A cobertura parcial é contada à parte ------------------------------------


def test_a_partial_coverage_pass_is_reported_separately() -> None:
    """Passou, mas com menos verificação — e o relatório diz isso.

    Sem esta separação, fechar os três tipos do Task 0 seria indistinguível de
    não os ter fechado: os dois estados produziriam o mesmo número.
    """
    report = evaluate([_attempt("cascata", COMPLETE), _attempt("cascata", PARTIAL)])
    scenario = report.scenarios[0]

    assert scenario.approved == 2
    assert scenario.approval_rate == 1.0
    assert scenario.approved_with_full_coverage == 1
    assert scenario.full_coverage_rate == 0.5


def test_full_coverage_rate_is_none_when_nothing_was_approved() -> None:
    report = evaluate([_attempt("cascata", {}, reasons=["motivo"])])
    assert report.scenarios[0].full_coverage_rate is None


# --- O confundidor da forma do piso -------------------------------------------


def test_scenarios_are_reported_before_being_aggregated() -> None:
    """A cascata aparece sozinha, porque o ADR 0028 a marcou como confundidor."""
    report = evaluate(
        [
            _attempt("cascata", {}, reasons=["motivo"]),
            _attempt("extinção ecológica", COMPLETE),
            _attempt("extinção ecológica", COMPLETE),
        ]
    )

    assert [scenario.scenario for scenario in report.scenarios] == [
        "cascata",
        "extinção ecológica",
    ]
    assert report.scenarios[0].approval_rate == 0.0
    assert report.scenarios[1].approval_rate == 1.0
    # A agregada existe, e só faz sentido depois de olhar as duas de cima.
    assert report.overall_approval_rate is not None
    assert 0.0 < report.overall_approval_rate < 1.0


# --- Os motivos viram padrão, e não lista de casos ----------------------------


def test_reasons_are_grouped_into_families() -> None:
    """Cada motivo cita o número ou termo achado; sem agrupar, não há padrão.

    O que o M6.4 precisa saber não é que houve dezessete motivos distintos — é
    que doze deles eram a mesma família, porque é a família que se conserta.
    """
    report = evaluate(
        [
            _attempt("a", {}, reasons=["formulação teleológica 'evoluiu para' (BIO-005)"]),
            _attempt("b", {}, reasons=["formulação teleológica 'a espécie quis' (BIO-005)"]),
            _attempt("c", {}, reasons=["o número '300' aparece na prosa gerada"]),
        ]
    )
    families = dict(report.reason_counts)

    assert families["teleologia (BIO-005)"] == 2
    assert families["número sem origem no piso"] == 1
    assert report.reason_counts[0][0] == "teleologia (BIO-005)", "ordenado por frequência"


def test_the_models_that_produced_the_data_are_recorded() -> None:
    """Comparar dois modelos exige saber qual escreveu o quê."""
    report = evaluate([_attempt("a", COMPLETE)])
    assert report.models == frozenset({"llama3.2:1b"})


# --- O registro em memória satisfaz a porta -----------------------------------


def test_the_recorder_keeps_what_it_is_given() -> None:
    recorder = InMemoryAttemptRecorder()
    recorder.record(_attempt("cascata", COMPLETE))

    assert len(recorder.read_all()) == 1
    assert recorder.read_all()[0].scenario == "cascata"
