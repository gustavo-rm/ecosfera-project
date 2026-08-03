"""As duas famílias de extinção são DISTINTAS e corretamente atribuídas (ADR 0019).

  ECOLÓGICA  — gradual, mediada por adaptação: THERMAL_INTOLERANCE,
               RESOURCE_SCARCITY, PREDATION_PRESSURE.
  CATASTRÓFICA — abrupta, independente de aptidão: CATASTROPHIC_EVENT.

Se as duas colapsassem numa só, o Tutor narraria toda extinção como falha de
adaptação — a concepção equivocada que o marco existe para desfazer.
"""

from __future__ import annotations

import pytest
from tests.support import test_params as _production_params

from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.events import EvolutionCauseCode
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    BiotaSlice,
    ClimateSlice,
    EcologySlice,
    EventSlice,
    ResourceSlice,
    WorldStateSnapshot,
)
from ecosfera_ai.simulation_engine.biology.genome import Genome

EVOLUTION = evolution_params()
PARAMS = _production_params()
TRAITS = ("temp_optimum", "temp_tolerance", "water_need", "size", "metabolism", "trophic_level")

ECOLOGICAL = {
    EvolutionCauseCode.THERMAL_INTOLERANCE,
    EvolutionCauseCode.RESOURCE_SCARCITY,
    EvolutionCauseCode.PREDATION_PRESSURE,
}


def _extinction_cause(
    genome: Genome,
    *,
    temperature: float = 20.0,
    capacity: float = 500.0,
    water: float = 0.9,
    predation: float = 0.0,
    catastrophe: float = 0.0,
) -> EvolutionCauseCode | None:
    """Leva uma comunidade minúscula ao piso e devolve a causa registrada."""
    snapshot = WorldStateSnapshot(
        planet_id="taxonomy",
        seed=2027,
        tick=7,
        era=0,
        climate=ClimateSlice(temperature=temperature),
        resource=ResourceSlice(
            water_available=water,
            nutrients_available=1.0,
            energy_available=0.2,
            carrying_capacity=capacity,
        ),
        biota=BiotaSlice(
            biomass=EVOLUTION.extinction_population * 1.05,
            species_richness=1.0,
            **{f"mean_{n}": float(getattr(genome, n)) for n in TRAITS},
        ),
        ecology=EcologySlice(predation_pressure=predation),
        event=EventSlice(catastrophic_mortality=catastrophe),
    )
    engine = EvolutionEngine()
    result = engine.tick(
        TickContext(
            snapshot=snapshot,
            rng=rng_for(snapshot.seed, engine.engine_id, snapshot.tick),
            tick=snapshot.tick,
            era=0,
            budget=PARAMS.engine_budget,
        )
    )
    extinct = [e for e in result.events if e.event_type == "SpeciesExtinct"]
    return extinct[0].cause_code if extinct else None  # type: ignore[return-value]


def _genome(**over: float) -> Genome:
    base = {
        "temp_optimum": 20.0,
        "temp_tolerance": 15.0,
        "water_need": 0.2,
        "size": 1.0,
        "metabolism": 1.0,
        "trophic_level": 1.0,
    }
    return Genome(**{**base, **over}).clamped()


def test_heat_beyond_tolerance_is_ecological() -> None:
    cause = _extinction_cause(_genome(temp_tolerance=2.0), temperature=70.0)
    assert cause is EvolutionCauseCode.THERMAL_INTOLERANCE


def test_an_exhausted_environment_is_ecological() -> None:
    cause = _extinction_cause(_genome(), capacity=0.0)
    assert cause in ECOLOGICAL
    assert cause is not EvolutionCauseCode.CATASTROPHIC_EVENT


def test_a_catastrophe_is_not_ecological() -> None:
    """Mesma comunidade, mundo perfeito — só a catástrofe muda a atribuição."""
    cause = _extinction_cause(_genome(), catastrophe=0.9)
    assert cause is EvolutionCauseCode.CATASTROPHIC_EVENT
    assert cause not in ECOLOGICAL


def test_the_catastrophe_wins_over_a_coexisting_ecological_stress() -> None:
    """Calor E meteoro juntos: a catástrofe é a causa.

    Sem esta precedência, uma comunidade que sofria calor moderado e foi morta
    por um meteoro seria narrada como intolerância térmica — culpando o traço por
    uma morte que veio de fora.
    """
    cause = _extinction_cause(_genome(temp_tolerance=3.0), temperature=55.0, catastrophe=0.9)
    assert cause is EvolutionCauseCode.CATASTROPHIC_EVENT


def test_without_a_catastrophe_the_same_world_gives_an_ecological_cause() -> None:
    """A contraprova do teste acima: tire o meteoro e a causa volta a ser o calor."""
    cause = _extinction_cause(_genome(temp_tolerance=3.0), temperature=55.0, catastrophe=0.0)
    assert cause in ECOLOGICAL


def test_the_two_families_are_disjoint() -> None:
    assert EvolutionCauseCode.CATASTROPHIC_EVENT not in ECOLOGICAL
    assert len(ECOLOGICAL) == 3


@pytest.mark.parametrize("severity", [0.5, 0.9, 1.0])
def test_whenever_a_catastrophe_kills_it_is_attributed_to_the_catastrophe(
    severity: float,
) -> None:
    """Não há limiar escondido na ATRIBUIÇÃO: se matou com catástrofe ativa, é ela."""
    assert _extinction_cause(_genome(), catastrophe=severity) is (
        EvolutionCauseCode.CATASTROPHIC_EVENT
    )


def test_a_mild_catastrophe_does_not_extinguish_a_thriving_community() -> None:
    """E o outro lado: catástrofe pequena não é sentença de morte.

    Uma comunidade folgada num mundo generoso absorve 5% de perda e segue. Sem
    esta afirmação, o teste acima poderia estar medindo "toda catástrofe mata",
    que seria uma dinâmica diferente — e pior — da que se quer ensinar.
    """
    assert _extinction_cause(_genome(), catastrophe=0.05) is None
