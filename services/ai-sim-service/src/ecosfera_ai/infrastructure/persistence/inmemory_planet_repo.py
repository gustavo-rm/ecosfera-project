"""Adaptador de persistência de planetas em memória (MVP/testes).

Guarda o histórico append-only de checkpoints por planeta (base para replay,
RF-016). Substituível por Mongo/Postgres via a porta `PlanetRepository` sem tocar
no domínio (ADR 0001).
"""

from __future__ import annotations

from ecosfera_ai.simulation_engine.state import PlanetState


class InMemoryPlanetRepository:
    def __init__(self) -> None:
        self._history: dict[str, list[PlanetState]] = {}

    async def save_checkpoint(self, state: PlanetState) -> None:
        self._history.setdefault(state.planet_id, []).append(state)

    async def load_latest(self, planet_id: str) -> PlanetState | None:
        history = self._history.get(planet_id)
        return history[-1] if history else None

    async def count_checkpoints(self, planet_id: str) -> int:
        """Nº de eras persistidas (append-only) — apoia testes e replay futuro."""
        return len(self._history.get(planet_id, []))
