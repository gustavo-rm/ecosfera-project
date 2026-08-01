"""Capacidade de "avançar um tick", isolada do orquestrador concreto.

Desde o M2 há uma única implementação — `FrameworkTickOrchestrator`, que roda o
tick pela moldura de Engines (ADR 0014). O Protocol permanece, e não por
simetria: é ele que mantém os casos de uso independentes do motor, e é o que
permitiu ao M0/M1 trocarem o orquestrador inteiro sem que nenhuma camada acima
mudasse de assinatura. A mesma porta serve ao replay, que injeta a variante que
não publica no Canal B.
"""

from __future__ import annotations

from typing import Protocol

from ecosfera_ai.simulation_engine.orchestrator import TickResult
from ecosfera_ai.simulation_engine.state import PlanetState, StateBounds


class Ticker(Protocol):
    """Motor capaz de evoluir um `PlanetState` em um passo determinístico."""

    @property
    def bounds(self) -> StateBounds:
        """Faixas físicas aplicadas ao estado (reusadas pelo replay)."""
        ...

    @property
    def subsystem_names(self) -> tuple[str, ...]:
        """Ordem de acoplamento em execução — torna a ordem testável."""
        ...

    def tick(self, state: PlanetState) -> TickResult: ...
