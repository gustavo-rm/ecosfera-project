"""O conjunto de avaliação vem do que o sistema PRODUZIU, e não do que se imaginou.

O Task A do M6.4 pede que a avaliação parta de falhas reais, porque elas têm sinal
maior que casos inventados: descrevem o que o modelo de fato erra, e não o que
alguém supôs que ele erraria.

## A lacuna que precisou ser fechada antes

O ADR 0028 prometeu ao M6.4 "os motivos de reprovação em forma utilizável". A
FORMA existia — `describe_failure` monta a linha, `fallback_reason` a carrega —
mas **nada guardava nada**: sem logger na camada de geração, sem escrita, sem
arquivo. O objeto vivia uma chamada e sumia. Utilizável em formato, inexistente
como dado.

Este arquivo afirma o caminho inteiro depois da correção: gerar → registrar →
reler → agregar. É o que separa "avaliação a partir de dados reais" de "avaliação
a partir de dados que alguém digitou".
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import ScriptedModel, cascade_context, spec

from ecosfera_ai.application.generation.evaluation import evaluate
from ecosfera_ai.application.generation.generate_explanation import (
    GenerateAnchoredExplanationUseCase,
)
from ecosfera_ai.application.generation.rejection_log import (
    GenerationAttempt,
    InMemoryAttemptRecorder,
    JsonlAttemptRecorder,
)

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()

FAITHFUL = "No ciclo 100, a queda de um meteoro atingiu o planeta."
INVENTED = "Uma erupção supervulcânica matou 300 espécies naquele ciclo."


# --- O caminho inteiro: gerar, registrar, reler --------------------------------


async def test_a_real_rejection_is_recorded_with_everything_the_analysis_needs() -> None:
    """O motivo, o texto reprovado e o piso — os três, ou o caso é irreconstruível."""
    recorder = InMemoryAttemptRecorder()
    case = GenerateAnchoredExplanationUseCase(
        ScriptedModel(INVENTED), spec(), recorder=recorder, scenario="cascata"
    )

    await case.execute(floor=FLOOR, context=CONTEXT)
    recorded = recorder.read_all()

    assert len(recorded) == 1
    attempt = recorded[0]
    assert attempt.scenario == "cascata"
    assert attempt.was_evaluated, "houve texto para verificar"
    assert not attempt.passed
    assert attempt.reasons, "sem motivo, o caso não vira exemplo de nada"
    assert INVENTED in attempt.fallback_reason, "o texto reprovado tem de sobreviver"
    assert attempt.floor_text == FLOOR.summary


async def test_approvals_are_recorded_too_because_a_rate_needs_a_denominator() -> None:
    """Um arquivo só de falhas não mede nada — a tentação seguinte seria estimar."""
    recorder = InMemoryAttemptRecorder()
    case = GenerateAnchoredExplanationUseCase(
        ScriptedModel(FAITHFUL, INVENTED), spec(), recorder=recorder, scenario="cascata"
    )

    await case.execute(floor=FLOOR, context=CONTEXT)
    await case.execute(floor=FLOOR, context=CONTEXT)

    recorded = recorder.read_all()
    assert len(recorded) == 2
    assert [attempt.passed for attempt in recorded] == [True, False]


async def test_an_infrastructure_failure_is_recorded_as_not_evaluated() -> None:
    """O terceiro estado sobrevive à ida ao registro e à volta.

    Se ele se perdesse aqui, a taxa de aprovação voltaria a somar queda de rede
    com alucinação — exatamente o que o M6.3 corrigiu.
    """
    recorder = InMemoryAttemptRecorder()
    case = GenerateAnchoredExplanationUseCase(
        ScriptedModel(None), spec(), recorder=recorder, scenario="cascata"
    )

    await case.execute(floor=FLOOR, context=CONTEXT)
    attempt = recorder.read_all()[0]

    assert not attempt.was_evaluated
    assert attempt.fell_back
    assert attempt.reasons == ()


# --- E o conjunto agregado sai desse registro ---------------------------------


async def test_the_report_is_computed_from_recorded_attempts() -> None:
    """A avaliação lê o registro; ela não recebe números de ninguém."""
    recorder = InMemoryAttemptRecorder()
    case = GenerateAnchoredExplanationUseCase(
        ScriptedModel(FAITHFUL, INVENTED, None), spec(), recorder=recorder, scenario="cascata"
    )
    for _ in range(3):
        await case.execute(floor=FLOOR, context=CONTEXT)

    report = evaluate(recorder.read_all())
    scenario = report.scenarios[0]

    assert scenario.attempts == 3
    assert scenario.evaluated == 2, "a falha de infra não entra no denominador"
    assert scenario.approved == 1
    assert scenario.approval_rate == 0.5
    assert report.reason_counts, "os motivos reais viraram famílias"


# --- O registro em arquivo sobrevive ao processo ------------------------------


async def test_the_jsonl_log_round_trips_and_appends(tmp_path: Path) -> None:
    """Append, e não reescrita: o conjunto CRESCE entre rodadas.

    Reescrever daria sempre a fotografia da última execução, que é a menos
    interessante das disponíveis — e apagaria justamente as falhas raras, que são
    as que vale a pena estudar.
    """
    log = tmp_path / "attempts.jsonl"
    recorder = JsonlAttemptRecorder(log)
    case = GenerateAnchoredExplanationUseCase(
        ScriptedModel(INVENTED), spec(), recorder=recorder, scenario="cascata"
    )

    await case.execute(floor=FLOOR, context=CONTEXT)
    await case.execute(floor=FLOOR, context=CONTEXT)

    assert len(log.read_text(encoding="utf-8").strip().splitlines()) == 2
    reread = JsonlAttemptRecorder(log).read_all()
    assert len(reread) == 2
    assert all(not attempt.passed for attempt in reread)
    assert reread[0].reasons, "o motivo atravessou o disco"


def test_reading_a_log_that_does_not_exist_yet_is_empty_and_not_an_error(
    tmp_path: Path,
) -> None:
    """A primeira rodada não pode estourar por não haver rodada anterior."""
    assert JsonlAttemptRecorder(tmp_path / "ainda-nao-existe.jsonl").read_all() == ()


def test_the_recorded_form_is_plain_json_a_human_can_read(tmp_path: Path) -> None:
    """O consumidor é uma pessoa abrindo o arquivo, e o formato respeita isso."""
    log = tmp_path / "attempts.jsonl"
    JsonlAttemptRecorder(log).record(
        GenerationAttempt(
            recorded_at="2026-08-15T00:00:00+00:00",
            planet_id="planet-x",
            scenario="cascata",
            model_name="llama3.2:1b",
            generated="prosa gerada",
            floor_text="piso",
            fell_back=False,
            fallback_reason="",
            verdict={"passed": True, "evaluated": True, "reasons": [], "coverage": {}},
        )
    )

    payload = json.loads(log.read_text(encoding="utf-8").strip())
    assert payload["scenario"] == "cascata"
    assert payload["verdict"]["passed"] is True
    # Sem escape de acentuação: o arquivo é para ser lido em português.
    assert "\\u" not in log.read_text(encoding="utf-8")
