"""Trilhas sintéticas para os testes de escopo de planeta.

Sintéticas, e não de uma corrida real, porque o cenário sob teste é justamente o
que uma corrida não produz sozinha: DOIS planetas com a MESMA semente. É a
situação de uma turma a que se disse "usem a semente 2027" — e a que revela que
`event_id` não distingue planeta.
"""

from __future__ import annotations

from ecosfera_ai.engines.climate.events import TEMPERATURE_SHIFT, ClimateCauseCode
from ecosfera_ai.engines.event.events import METEOR_IMPACT, EventCauseCode
from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT, EvolutionCauseCode
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter

SHARED_SEED = 2027


OWNER = "owner"


def cascade(
    seed: int = SHARED_SEED, era: int = 1, base_tick: int = 100, owner: str = "anonimo"
) -> list[DomainEvent]:
    """Meteoro → resfriamento → extinção, com `causation_id` real.

    A MESMA função serve aos dois planetas de propósito: com a mesma semente ela
    produz `event_id` byte a byte idênticos, que é a condição adversarial.

    `owner` é a marca que permite DETECTAR o vazamento, e não apenas contá-lo. A
    derivação do id usa (semente, era, tick, engine, tipo, sequência) e NÃO o
    `cause_detail` — então dois eventos podem ter o mesmo id e conteúdos
    distintos. É o que torna possível afirmar que a consulta devolveu o evento do
    planeta CERTO, e não apenas a quantidade certa: sem a marca, duas trilhas
    idênticas tornariam o vazamento indistinguível do acerto.
    """
    impact = EventEmitter(engine_id="event", seed=seed, tick=base_tick, era=era).emit(
        METEOR_IMPACT,
        EventCauseCode.EVENT_ONSET,
        participants=["event:meteor"],
        cause_detail={"impact_energy": 0.8, OWNER: owner},
    )
    cooling = EventEmitter(engine_id="climate", seed=seed, tick=base_tick + 1, era=era).emit(
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        participants=["engine:climate"],
        cause_detail={"delta": -12.0, OWNER: owner},
        causation_id=impact.event_id,
    )
    extinct = EventEmitter(engine_id="evolution", seed=seed, tick=base_tick + 2, era=era).emit(
        SPECIES_EXTINCT,
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        participants=["species:community"],
        environmental_factors=["climate:cold"],
        resources=["water"],
        genes=["gene:therm_tol"],
        cause_detail={"biomass_before": 40.0, OWNER: owner},
        causation_id=cooling.event_id,
    )
    return [impact, cooling, extinct]
