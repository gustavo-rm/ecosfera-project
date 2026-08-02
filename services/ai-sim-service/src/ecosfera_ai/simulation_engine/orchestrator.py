"""Contrato de resultado de um tick (RF-013/014/023).

Este módulo já foi o `TickOrchestrator` monolítico, que rodava seis subsistemas
em sequência sobre um `PlanetState`. Ele foi desmontado no M2: cada processo
planetário virou um Engine com fatia própria, e quem orquestra é o Planet Engine
(`engines/planet/service.py`). A ordem de acoplamento, que aqui era a constante
`SUBSYSTEM_ORDER`, agora é `ENGINE_ORDER` em `engines/composition.py` — e passou
a ser VERIFICADA no boot por `validate_graph`, em vez de apenas documentada
(ADR 0014).

O que sobrou é o contrato de saída, que os casos de uso consomem e que o
`FrameworkTickOrchestrator` preenche.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.domain.feedback.models import Observation
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


@dataclass(frozen=True, slots=True)
class TickResult:
    """Resultado de um tick: novo estado, delta agregado e observações derivadas.

    `events` é o Canal B do tick: os domain events que os Engines emitiram,
    repassados ao consumidor. É por este campo que o feedback causal chega ao
    Tutor sem que ele precise vasculhar o Event Store por planeta — os eventos
    vêm da execução daquele planeta (ADR 0011).
    """

    state: PlanetState
    delta: StateDelta
    observations: list[Observation]
    events: tuple[DomainEvent, ...] = ()
