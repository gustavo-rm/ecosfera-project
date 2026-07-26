"""Orquestrador do tick determinístico (RF-013/014/023).

Roda os subsistemas (estratégias) na ordem de acoplamento clima -> química ->
vida, aplicando cada delta ao estado de trabalho para que um subsistema enxergue
os efeitos do anterior dentro do mesmo tick. O RNG numpy é semeado por
(seed, tick) via `SeedSequence`: a mesma semente reproduz exatamente a trajetória
(RF-023), enquanto cada tick recebe ruído distinto porém determinístico.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecosfera_ai.domain.feedback.models import Observation
from ecosfera_ai.simulation_engine.state import PlanetState, StateBounds, StateDelta
from ecosfera_ai.simulation_engine.subsystems.base import Subsystem


@dataclass(frozen=True, slots=True)
class TickResult:
    """Resultado de um tick: novo estado, delta agregado e observações derivadas."""

    state: PlanetState
    delta: StateDelta
    observations: list[Observation]


class TickOrchestrator:
    """Compõe subsistemas plugáveis em um passo determinístico e reprodutível."""

    def __init__(self, subsystems: list[Subsystem], bounds: StateBounds) -> None:
        self._subsystems = subsystems
        self._bounds = bounds

    def tick(self, state: PlanetState) -> TickResult:
        rng = np.random.default_rng(np.random.SeedSequence([state.seed, state.tick]))
        working = state
        for subsystem in self._subsystems:
            delta = subsystem.step(working, rng)
            working = working.apply(delta, self._bounds)
        new_state = working.advanced()
        return TickResult(
            state=new_state,
            delta=new_state.delta_from(state),
            observations=new_state.observe(state),
        )
