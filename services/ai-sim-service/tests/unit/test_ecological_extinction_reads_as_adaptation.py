"""A extinção ecológica FALA de ambiente e adaptação — com aptidão CONTEXTUAL.

A contraprova do arquivo vizinho. Sem ela, "não culpar a comunidade" seria
satisfeito por um Tutor que nunca explica nada: o defeito é uniformizar as duas
famílias, e ele tem duas direções.

Aqui a adaptação É parte da explicação, porque é isso que a extinção ecológica é.
O que a formulação não pode fazer é escorregar para aptidão ABSOLUTA (Q5): dizer
que a comunidade "era fraca" ou "não servia" reintroduz o número único que
ordenaria espécies fora de contexto. A formulação correta é a que o Tutor herda
da Fase 0 — a MESMA coorte é apta a um ambiente e inapta a outro, sem ter mudado
em nada, e é justamente isso que torna inteligível a extinção catastrófica.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import context_of, explain, renderer

from ecosfera_ai.domain.consumers.explanation import Register
from ecosfera_ai.engines.climate.events import ClimateCauseCode
from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT, EvolutionCauseCode
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter

CASCADE = branching_cascade()
_METEOR, _COOLING, _WILDFIRE, CATASTROPHIC, ECOLOGICAL = CASCADE

# Aptidão ABSOLUTA — o que a Q5 nega. Nega-se o número único fora de contexto,
# não a aptidão.
ABSOLUTE = (
    "era fraca",
    "era inferior",
    "não servia",
    "menos evoluída",
    "mais evoluída",
    "não era boa o suficiente",
    "perdeu a competição da evolução",
)


def _extinction(cause: EvolutionCauseCode, tick: int = 400) -> DomainEvent:
    return EventEmitter(engine_id="evolution", seed=2027, tick=tick, era=1).emit(
        SPECIES_EXTINCT,
        cause,
        participants=["species:community"],
        cause_detail={"biomass": 0.0, "biomass_before": 40.0},
    )


def _ecological_text() -> str:
    explanation = explain(CASCADE)
    fact = next(f for f in explanation.facts if f.grounding.event_id == ECOLOGICAL.event_id)
    return fact.text.lower()


def test_the_ecological_extinction_explains_through_the_environment() -> None:
    text = _ecological_text()
    assert "temperatura" in text, f"a extinção térmica não menciona o ambiente: {text!r}"
    assert "tolerava" in text


def test_it_does_not_read_as_a_catastrophe() -> None:
    """A direção oposta do defeito: narrar um declínio como azar apagaria a seleção."""
    text = _ecological_text()
    assert "evento extremo" not in text
    assert "meteoro" not in text


def test_the_fitness_is_contextual_and_never_absolute() -> None:
    """A formulação da Q5: a MESMA comunidade seguiria adiante em outro ambiente."""
    text = _ecological_text()
    assert "em outro ambiente" in text
    assert "sem mudar nada nela" in text, (
        "a frase não diz que a comunidade não precisaria ter mudado — sem isso "
        "a aptidão volta a parecer uma propriedade dela, e não da relação"
    )
    for phrase in ABSOLUTE:
        assert phrase not in text, f"a explicação usa aptidão ABSOLUTA: {phrase!r}"


@pytest.mark.parametrize(
    "cause",
    [
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        EvolutionCauseCode.RESOURCE_SCARCITY,
        EvolutionCauseCode.PREDATION_PRESSURE,
    ],
)
def test_every_ecological_cause_gets_its_own_mechanism(cause: EvolutionCauseCode) -> None:
    """Três mecanismos, três frases. Colapsá-los seria perder o "por quê"."""
    explanation = explain([_extinction(cause)])
    fact = explanation.facts[0]

    assert fact.template_id == "T-EXTINCTION-ECOLOGICAL"
    assert "evento extremo" not in fact.text.lower()
    for phrase in ABSOLUTE:
        assert phrase not in fact.text.lower()


def test_the_three_mechanisms_produce_three_different_sentences() -> None:
    """A prova de que o `cause_code` chega mesmo à prosa, e não só ao template."""
    texts = {
        explain([_extinction(cause, tick=tick)]).facts[0].text
        for tick, cause in enumerate(
            (
                EvolutionCauseCode.THERMAL_INTOLERANCE,
                EvolutionCauseCode.RESOURCE_SCARCITY,
                EvolutionCauseCode.PREDATION_PRESSURE,
            ),
            start=400,
        )
    }
    assert len(texts) == 3, "mecanismos diferentes produziram a mesma frase"


def test_the_simple_register_keeps_the_contextual_framing() -> None:
    explanation = renderer().render(context_of(CASCADE), Register.SIMPLE)
    fact = next(f for f in explanation.facts if f.grounding.event_id == ECOLOGICAL.event_id)
    text = fact.text.lower()

    assert fact.register is Register.SIMPLE
    assert "em outro lugar" in text, "a versão simples perdeu o enquadramento contextual"
    for phrase in ABSOLUTE:
        assert phrase not in text


def test_a_decline_is_not_narrated_as_an_extinction() -> None:
    """Mortandade em massa NÃO é extinção — a comunidade seguiu existindo.

    Confundir as duas ensinaria que toda perda é terminal, e o caso comum deste
    modelo é justamente a perda parcial (ADR 0016).
    """
    mortality = EventEmitter(engine_id="evolution", seed=2027, tick=410, era=1).emit(
        "MassMortality",
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        participants=["species:community"],
        cause_detail={"lost_fraction": 0.3},
    )
    fact = explain([mortality]).facts[0]

    assert fact.template_id == "T-MASS-MORTALITY"
    assert "não desapareceu" in fact.text.lower()


def test_a_climate_shift_alone_is_not_narrated_as_a_biological_loss() -> None:
    """Guarda de fronteira: um evento de clima não pode virar frase de extinção."""
    shift = EventEmitter(engine_id="climate", seed=2027, tick=420, era=1).emit(
        "TemperatureShift",
        ClimateCauseCode.RADIATIVE_FORCING,
        cause_detail={"change": -3.0, "temperature": 280.0},
    )
    fact = explain([shift]).facts[0]

    assert "comunidade" not in fact.text.lower()
    assert fact.template_id.startswith("T-CHAIN")
