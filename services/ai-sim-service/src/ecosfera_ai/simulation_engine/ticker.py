"""Capacidade de "avançar um tick", isolada do orquestrador concreto.

Existem hoje duas implementações: o `TickOrchestrator` original e o
`FrameworkTickOrchestrator`, que roda o mesmo tick através da moldura de Engines
(ADR 0008). Os casos de uso dependem deste Protocol, não de um dos dois — trocar
a implementação é decisão da raiz de composição, atrás da flag
`ECOSFERA_ENGINES_FRAMEWORK`, e nenhuma camada acima percebe.
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
