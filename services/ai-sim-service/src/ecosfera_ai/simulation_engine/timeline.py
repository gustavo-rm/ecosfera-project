"""Linha do tempo do planeta: eras, checkpoints append-only e replay (Dossiê §9).

Este é o núcleo do *event-sourcing-lite* do serviço (ADR 0004). A ideia central é
que o motor já é **determinístico por semente** (RF-023): dada a mesma semente e o
mesmo estado de partida, a sequência de ticks é sempre idêntica. Não é preciso,
portanto, gravar o estado de cada tick — bastam:

  - um **checkpoint** ao fim de cada era (estado imutável, append-only), e
  - o **log de eventos** com o que NÃO é derivável do motor: as intervenções do
    aluno e os marcos observados.

Com esses dois é possível reconstruir qualquer era reexecutando o motor a partir
do último checkpoint e reaplicando os eventos (RF-016 — rebobinar/replay).

Convenção de ordenação (única e explícita, para que gravação e replay concordem):
**os eventos registrados no tick T são aplicados ao estado em T, imediatamente
antes do passo que leva de T para T+1.**
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Protocol

from ecosfera_ai.simulation_engine.state import PlanetState, StateBounds, StateDelta

# Tipos de evento. Só INTERVENTION altera o estado no replay; os demais são
# anotações observacionais (marcos narrativos) e são no-ops na reconstrução.
EVENT_INTERVENTION = "intervention"
EVENT_LIFE_EMERGED = "life_emerged"
EVENT_SNOWBALL = "snowball"
EVENT_ICE_FREE = "ice_free"

_DELTA_FIELDS: frozenset[str] = frozenset(f.name for f in fields(StateDelta))


@dataclass(frozen=True, slots=True)
class EventLogEntry:
    """Entrada append-only do log de eventos de um planeta."""

    planet_id: str
    tick: int
    event_type: str
    payload: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class EraCheckpoint:
    """Estado imutável ao FIM de uma era (Dossiê §9).

    Guardar a semente junto do estado torna o checkpoint autossuficiente para o
    replay: não é preciso consultar o planeta para reexecutar o motor.
    """

    planet_id: str
    era: int
    seed: int
    start_tick: int
    end_tick: int
    state: PlanetState


@dataclass(frozen=True, slots=True)
class EraSummary:
    """Metadados de uma era para listagem da linha do tempo (sem o estado inteiro)."""

    era: int
    start_tick: int
    end_tick: int
    event_count: int


class StepOutcome(Protocol):
    """O que o replay precisa do resultado de um tick: o estado resultante."""

    @property
    def state(self) -> PlanetState: ...


class Stepper(Protocol):
    """Capacidade mínima exigida do motor pelo replay: avançar um tick.

    Depender do Protocol (e não do `TickOrchestrator` concreto) mantém o replay
    testável com um motor falso e coerente com a fronteira hexagonal.
    """

    def tick(self, state: PlanetState) -> StepOutcome: ...


def intervention_delta(payload: Mapping[str, float]) -> StateDelta:
    """Converte o payload de uma intervenção em `StateDelta`.

    O payload usa a linguagem ubíqua ('co2', 'temperature'); chaves desconhecidas
    são ignoradas para que um cliente novo não quebre a reconstrução de um log
    antigo (tolerância a versões — o log é append-only e imutável).
    """
    kwargs = {
        f"d_{variable}": float(value)
        for variable, value in payload.items()
        if f"d_{variable}" in _DELTA_FIELDS
    }
    return StateDelta(**kwargs)


def apply_event(state: PlanetState, entry: EventLogEntry, bounds: StateBounds) -> PlanetState:
    """Aplica um evento ao estado. Só intervenções mutam; marcos são no-ops."""
    if entry.event_type != EVENT_INTERVENTION:
        return state
    return state.apply(intervention_delta(entry.payload), bounds)


def detect_milestones(
    planet_id: str, previous: PlanetState, current: PlanetState
) -> list[EventLogEntry]:
    """Deriva marcos narrativos da transição entre dois estados.

    São anotações (não mutam o estado): dão à linha do tempo os momentos que o
    aluno reconhece — o surgimento da vida, a Terra bola de neve, o degelo total.
    """
    milestones: list[EventLogEntry] = []
    if previous.biomass <= 0.0 < current.biomass:
        milestones.append(
            EventLogEntry(planet_id, current.tick, EVENT_LIFE_EMERGED, {"biomass": current.biomass})
        )
    if previous.ice_cover < 1.0 <= current.ice_cover:
        milestones.append(
            EventLogEntry(planet_id, current.tick, EVENT_SNOWBALL, {"ice_cover": current.ice_cover})
        )
    if previous.ice_cover > 0.0 >= current.ice_cover:
        milestones.append(
            EventLogEntry(planet_id, current.tick, EVENT_ICE_FREE, {"ice_cover": current.ice_cover})
        )
    return milestones


def replay(
    base: PlanetState,
    events: Iterable[EventLogEntry],
    until_tick: int,
    stepper: Stepper,
    bounds: StateBounds,
) -> PlanetState:
    """Reconstrói o estado em `until_tick` a partir de um checkpoint + eventos.

    Função pura: não faz I/O e não consome relógio nem RNG próprio — toda a
    estocasticidade vem do motor, semeada por (seed, tick). Por isso o resultado
    é idêntico ao da execução original (RF-023), o que o `ReplayStateUseCase`
    verifica explicitamente.
    """
    if until_tick < base.tick:
        raise ValueError(
            f"não é possível reconstruir o tick {until_tick} a partir de um "
            f"checkpoint mais adiantado (tick {base.tick})"
        )

    by_tick: dict[int, list[EventLogEntry]] = {}
    for entry in events:
        by_tick.setdefault(entry.tick, []).append(entry)

    state = base
    while state.tick < until_tick:
        for entry in by_tick.get(state.tick, ()):
            state = apply_event(state, entry, bounds)
        state = stepper.tick(state).state
    return state


def summarize(
    checkpoints: Sequence[EraCheckpoint], event_counts: Mapping[int, int]
) -> list[EraSummary]:
    """Monta a listagem da linha do tempo a partir dos checkpoints persistidos."""
    return [
        EraSummary(
            era=cp.era,
            start_tick=cp.start_tick,
            end_tick=cp.end_tick,
            event_count=event_counts.get(cp.era, 0),
        )
        for cp in checkpoints
    ]
