"""O bug do M6.1, agora na camada de geração — e ele não passa mais.

O motor de regras antigo concluía `co2↑ ⇒ temperatura↑` propagando variáveis, sem
conferir se um `TemperatureShift` ocorreu naquele planeta. O M6.1 diagnosticou a
falha e a corrigiu no caminho de template:

> Correta como ciência geral; **não derivável daquela trilha** — que é exatamente
> a definição de alucinação que o M6 adota.

O M6.3 reintroduziu o risco sem perceber. A detecção de acontecimento inventado
dependia de um termo concreto por tipo, e `TemperatureShift` não tem nenhum:
"temperatura" aparece legitimamente no vocabulário de mecanismo do M6.1. Um
modelo que recebesse um dossiê com aumento de gás carbônico e escrevesse "e por
isso a temperatura subiu" produzia a MESMA alucinação, com a mesma aparência de
ciência correta — e passava.

Este arquivo é a prova de que ela não passa mais, montado sobre o cenário exato
que a produz: gás carbônico no log, e nenhum `TemperatureShift`.
"""

from __future__ import annotations

import pytest
from tests.support_explanation import explain
from tests.support_generation import spec

from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.generation.fact_claims import directional_problems_in
from ecosfera_ai.domain.generation.grounding import verify_grounding
from ecosfera_ai.engines.climate.events import TEMPERATURE_SHIFT, ClimateCauseCode
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter

GREENHOUSE_FORCING_CHANGED = "GreenhouseForcingChanged"


def _emit(engine: str, event_type: str, cause: object, tick: int, **extra: object) -> DomainEvent:
    emitter = EventEmitter(engine_id=engine, seed=2027, tick=tick, era=1)
    return emitter.emit(event_type, cause, **extra)  # type: ignore[arg-type]


def _co2_only() -> FactualContext:
    """Gás carbônico sobe e NADA mais — o cenário que tenta a generalização.

    É o dossiê mais perigoso que este sistema admite, porque a conclusão que falta
    é verdadeira em geral e falsa aqui.
    """
    carbon = _emit(
        "atmosphere",
        GREENHOUSE_FORCING_CHANGED,
        ClimateCauseCode.RADIATIVE_FORCING,
        50,
        cause_detail={"co2_ppm": 480.0, "forcing": 2.1},
    )
    return FactualContext.of("planet-co2", ContextSlice.of_era(1), (carbon,))


def _co2_then_cooling() -> FactualContext:
    """O mesmo gás carbônico, mas o log registra RESFRIAMENTO.

    Existe para separar "inventou" de "contradisse": aqui o evento está no log, e
    o erro possível é afirmar a direção errada.
    """
    carbon = _emit(
        "atmosphere",
        GREENHOUSE_FORCING_CHANGED,
        ClimateCauseCode.RADIATIVE_FORCING,
        50,
        cause_detail={"co2_ppm": 480.0},
    )
    cooling = _emit(
        "climate",
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        51,
        causation_id=carbon.event_id,
        cause_detail={"change": -6.0, "temperature": 9.0},
    )
    return FactualContext.of("planet-co2", ContextSlice.of_era(1), (carbon, cooling))


CO2_ONLY = _co2_only()
CO2_THEN_COOLING = _co2_then_cooling()
FLOOR = explain([])


# --- O cenário é o que se pensa que é -----------------------------------------


def test_the_dossier_really_has_carbon_and_no_temperature_shift() -> None:
    """Contraprova do cenário — sem ela o arquivo mediria outra coisa."""
    types = {event.event_type for event in CO2_ONLY.events}
    assert GREENHOUSE_FORCING_CHANGED in types
    assert TEMPERATURE_SHIFT not in types


# --- A generalização do M6.1, barrada -----------------------------------------


@pytest.mark.parametrize(
    "generalization",
    [
        "O gás carbônico aumentou, e por isso a temperatura subiu.",
        "Com mais gás carbônico no ar, o planeta esquentou.",
        "O gás carbônico cresceu e o clima mudou: a temperatura aumentou naquele ciclo.",
    ],
)
def test_inferring_a_temperature_rise_that_is_not_in_the_log_is_caught(
    generalization: str,
) -> None:
    """A frase é ciência correta e mentira sobre ESTE planeta.

    É a distinção inteira do M6: derivável do event log, ou não derivável.
    """
    problems = directional_problems_in(generalization, CO2_ONLY)
    assert problems, f"a generalização do M6.1 passou de novo: {generalization!r}"
    assert any(TEMPERATURE_SHIFT in problem for problem in problems)

    assert not verify_grounding(generalization, floor=FLOOR, context=CO2_ONLY, spec=spec()).passed


def test_reporting_the_carbon_alone_is_accepted() -> None:
    """Contraprova: o que o log CONTÉM continua podendo ser dito.

    Sem isto, "barra a generalização" poderia significar "barra falar de gás
    carbônico" — e o Tutor emudeceria sobre o que de fato aconteceu.
    """
    faithful = "Naquele ciclo, a quantidade de gás carbônico do ar mudou."
    assert directional_problems_in(faithful, CO2_ONLY) == ()


# --- Contradizer o log é diferente de inventá-lo ------------------------------


def test_claiming_a_rise_when_the_log_recorded_cooling_is_caught() -> None:
    """O evento existe; a direção afirmada é a oposta da registrada."""
    problems = directional_problems_in(
        "Com mais gás carbônico, a temperatura subiu naquele período.", CO2_THEN_COOLING
    )
    assert problems
    assert any("contradiz" in problem for problem in problems)
    assert any("-6.0" in problem for problem in problems), "o motivo tem de citar o delta real"


def test_claiming_the_direction_the_log_recorded_is_accepted() -> None:
    """A mesma frase, com a direção certa, passa — a checagem é sobre o sinal."""
    assert directional_problems_in("A temperatura caiu naquele período.", CO2_THEN_COOLING) == ()


# --- A direção pertence à oração, e não ao texto inteiro ----------------------


def test_a_direction_in_another_sentence_is_not_attributed_to_temperature() -> None:
    """ "A temperatura mudou. A população caiu." não acusa a temperatura de cair.

    Sem a divisão em orações, qualquer palavra de direção no texto contaminaria
    todos os assuntos citados — e o verificador reprovaria prosa correta por
    proximidade acidental.
    """
    mixed = "A temperatura ficou fora da faixa tolerada. A comunidade desapareceu."
    assert directional_problems_in(mixed, CO2_ONLY) == ()
