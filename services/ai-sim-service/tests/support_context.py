"""Trilhas sintéticas para o dossiê factual do M6.0.

Sintéticas de propósito. O que estes testes precisam afirmar é a FORMA da cadeia
reconstruída — quem é filho de quem, quantos ramos saem de um mesmo evento, o que
acontece quando a causa fica fora da fatia. Uma corrida real produz cascatas
verdadeiras, mas não produz sob demanda a árvore RAMIFICADA de que a travessia
descendente depende, nem o ciclo corrompido que a guarda precisa encontrar.

A cascata real (meteoro numa corrida completa dos nove Engines) tem lugar próprio
— `test_causal_chain_reconstruction.py` a exercita de ponta a ponta, para que a
forma afirmada aqui não seja uma forma que só existe nestes fixtures.
"""

from __future__ import annotations

from ecosfera_ai.engines.climate.events import TEMPERATURE_SHIFT, ClimateCauseCode
from ecosfera_ai.engines.ecology.events import TROPHIC_COLLAPSE, EcologyCauseCode
from ecosfera_ai.engines.event.events import (
    METEOR_IMPACT,
    WILDFIRE_IGNITED,
    EventCauseCode,
)
from ecosfera_ai.engines.evolution.events import (
    LIFE_EMERGED,
    SPECIES_EXTINCT,
    EvolutionCauseCode,
)
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter

SEED = 2027


def _emit(
    engine_id: str,
    event_type: str,
    cause_code: EvolutionCauseCode | ClimateCauseCode | EventCauseCode | EcologyCauseCode,
    tick: int,
    *,
    era: int = 1,
    seed: int = SEED,
    causation_id: str | None = None,
    participants: tuple[str, ...] = (),
    cause_detail: dict[str, float | int | str] | None = None,
) -> DomainEvent:
    return EventEmitter(engine_id=engine_id, seed=seed, tick=tick, era=era).emit(
        event_type,
        cause_code,
        participants=participants,
        cause_detail=cause_detail or {},
        causation_id=causation_id,
    )


def branching_cascade(era: int = 1, base_tick: int = 100) -> list[DomainEvent]:
    """Meteoro com TRÊS efeitos diretos, um deles com efeito próprio.

    ```
    MeteorImpact
      ├── TemperatureShift ── SpeciesExtinct (THERMAL_INTOLERANCE, ecológica)
      ├── WildfireIgnited
      └── SpeciesExtinct   (CATASTROPHIC_EVENT, encadeada ao EVENTO)
    ```

    A ramificação é o ponto. Uma travessia descendente que devolvesse só a lista
    invertida da subida entregaria UM ramo, e o Tutor narraria a cascata do
    meteoro citando um efeito como se fosse todo o resultado. E as duas extinções
    coexistem no mesmo cenário porque é assim que a distinção do ADR 0019 se
    verifica: as duas famílias juntas, distinguíveis pela causa e pelo elo.
    """
    meteor = _emit(
        "event",
        METEOR_IMPACT,
        EventCauseCode.EVENT_ONSET,
        base_tick,
        era=era,
        participants=("event:meteor",),
        cause_detail={"impact_energy": 0.9},
    )
    cooling = _emit(
        "climate",
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        base_tick + 1,
        era=era,
        causation_id=meteor.event_id,
        cause_detail={"delta": -14.0},
    )
    wildfire = _emit(
        "event",
        WILDFIRE_IGNITED,
        EventCauseCode.EVENT_ONSET,
        base_tick + 1,
        era=era,
        causation_id=meteor.event_id,
    )
    catastrophic = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.CATASTROPHIC_EVENT,
        base_tick + 2,
        era=era,
        causation_id=meteor.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 40.0, "removed_fraction": 1.0},
    )
    ecological = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        base_tick + 3,
        era=era,
        causation_id=cooling.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 12.0},
    )
    return [meteor, cooling, wildfire, catastrophic, ecological]


def spans_two_eras() -> list[DomainEvent]:
    """Causa na era 1, consequência na era 2 — a fatia por era corta o elo.

    O caso que decide se uma fatia por era continua navegável: o evento da era 2
    aponta para uma causa que a fatia não contém. Ele tem de virar RAIZ local, e
    não sumir nem virar filho de coisa nenhuma.
    """
    collapse = _emit(
        "ecology",
        TROPHIC_COLLAPSE,
        EcologyCauseCode.PREY_COLLAPSE,
        base_tick_first := 90,
        era=1,
    )
    aftermath = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.RESOURCE_SCARCITY,
        base_tick_first + 30,
        era=2,
        causation_id=collapse.event_id,
        participants=("species:community",),
    )
    return [collapse, aftermath]


def life_emerged(tick: int = 10, era: int = 0) -> DomainEvent:
    """O marcador canônico: a vida surgiu."""
    return _emit(
        "evolution",
        LIFE_EMERGED,
        EvolutionCauseCode.HABITABILITY_THRESHOLD,
        tick,
        era=era,
        participants=("species:community",),
        cause_detail={"habitability": 0.71},
    )


def cyclic_trail() -> list[DomainEvent]:
    """Trilha CORROMPIDA: dois eventos que se causam mutuamente.

    Não sai de corrida alguma — `causation_id` aponta sempre para um evento
    anterior. Sai de um import malfeito, e uma trilha importada não pode travar o
    consumidor nem apagar eventos do dossiê em silêncio.
    """
    first = _emit("climate", TEMPERATURE_SHIFT, ClimateCauseCode.RADIATIVE_FORCING, 200)
    second = _emit(
        "climate",
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        201,
        causation_id=first.event_id,
    )
    looped = DomainEvent(
        event_id=first.event_id,
        event_type=first.event_type,
        engine_id=first.engine_id,
        occurred_at=first.occurred_at,
        seed=first.seed,
        cause_code=first.cause_code,
        correlation_id=first.correlation_id,
        causation_id=second.event_id,
    )
    return [looped, second]
