"""Variação de população inventada, ou contrária ao log, é detectada.

Terceiro dos tipos que o ADR 0028 declarou sem cobertura. Mesma forma do caso da
temperatura: não há termo exclusivo — "população" aparece no vocabulário legítimo
do M6.1 —, então o que se confere é o par (assunto, direção), contra a biomassa
registrada no `cause_detail`.

O modo de falha aqui é menos espetacular que uma especiação inventada e mais
provável: um modelo pequeno, resumindo uma extinção, escreve "a população foi
diminuindo aos poucos" num planeta onde a comunidade morreu de uma vez por causa
de um meteoro. Duas coisas erradas de uma vez — a direção pode até estar certa,
mas o gradual contradiz o abrupto, e é a distinção do ADR 0019.
"""

from __future__ import annotations

import pytest
from tests.support_explanation import explain
from tests.support_generation import spec

from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.generation.fact_claims import directional_problems_in
from ecosfera_ai.domain.generation.grounding import verify_grounding
from ecosfera_ai.engines.ecology.events import EcologyCauseCode
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter

MASS_MORTALITY = "MassMortality"
FLOOR = explain([])


def _emit(event_type: str, cause: object, tick: int, **extra: object) -> DomainEvent:
    emitter = EventEmitter(engine_id="ecology", seed=2027, tick=tick, era=1)
    return emitter.emit(event_type, cause, **extra)  # type: ignore[arg-type]


def _quiet_planet() -> FactualContext:
    """Um dossiê sem evento algum de população."""
    warming = _emit("TemperatureShift", EcologyCauseCode.RESOURCE_SCARCITY, 10)
    return FactualContext.of("planet-quiet", ContextSlice.of_era(1), (warming,))


def _population_fell() -> FactualContext:
    event = _emit(
        MASS_MORTALITY,
        EcologyCauseCode.RESOURCE_SCARCITY,
        20,
        participants=("species:community",),
        cause_detail={"biomass": 4.0, "biomass_before": 30.0},
    )
    return FactualContext.of("planet-fall", ContextSlice.of_era(1), (event,))


QUIET = _quiet_planet()
FELL = _population_fell()


def test_the_scenarios_are_what_they_claim_to_be() -> None:
    """Contraprova dos cenários, antes de afirmar qualquer coisa sobre eles."""
    assert MASS_MORTALITY not in {event.event_type for event in QUIET.events}
    assert MASS_MORTALITY in {event.event_type for event in FELL.events}


@pytest.mark.parametrize(
    "invented",
    [
        "A população caiu bastante naquele período.",
        "A quantidade de vida no planeta diminuiu.",
        "A biomassa despencou depois daquilo.",
    ],
)
def test_a_population_change_absent_from_the_log_is_caught(invented: str) -> None:
    problems = directional_problems_in(invented, QUIET)
    assert problems, f"passou sem detecção: {invented!r}"
    assert not verify_grounding(invented, floor=FLOOR, context=QUIET, spec=spec()).passed


def test_the_same_claim_is_accepted_where_the_log_records_it() -> None:
    """A detecção é sobre o log — o mesmo texto passa no planeta em que houve."""
    assert directional_problems_in("A população caiu bastante naquele período.", FELL) == ()


def test_claiming_growth_where_the_log_records_a_fall_is_caught() -> None:
    """Direção oposta à registrada: contradição, e não invenção."""
    problems = directional_problems_in("A população cresceu naquele ciclo.", FELL)
    assert problems
    assert any("contradiz" in problem for problem in problems)
    assert any("-26.0" in problem for problem in problems), "o motivo cita a variação real"


# --- A direção é do que o verbo rege ------------------------------------------


def test_the_correct_bio_005_sentence_is_not_accused_of_a_population_claim() -> None:
    """O falso positivo que quase entrou, na frase que MAIS importa.

    "a característica aumentou a sobrevivência" tem o assunto ("população") e um
    verbo de subida na mesma oração, e não afirma nada sobre o tamanho da
    população — o verbo rege "a sobrevivência". Esta é a formulação correta do
    BIO-005, a que o sistema inteiro existe para saber dizer; reprová-la seria
    pior que não detectar invenção alguma.
    """
    correct = (
        "Surgiu uma mutação aleatória na população, e a característica aumentou a "
        "sobrevivência porque o ambiente daquele momento era assim."
    )
    assert directional_problems_in(correct, QUIET) == ()


def test_a_transitive_verb_governing_the_subject_still_counts() -> None:
    """A regra é sintática, e não uma isenção: reger o ASSUNTO continua sendo afirmação."""
    problems = directional_problems_in("O evento diminuiu a população do planeta.", QUIET)
    assert problems, "reger o próprio assunto é afirmar a direção sobre ele"
