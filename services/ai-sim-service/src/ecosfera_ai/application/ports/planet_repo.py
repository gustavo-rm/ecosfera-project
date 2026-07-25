"""Porta de saída para persistir checkpoints do planeta (Repository).

Checkpoints são append-only por era (Dossiê §9): cada tick grava um novo estado,
base para replay determinístico (RF-016) e auditoria da trajetória. O adaptador
in-memory serve ao MVP/testes; um adaptador Mongo/Postgres o substitui sem tocar
nas camadas superiores (ADR 0001).
"""

from __future__ import annotations

from typing import Protocol

from ecosfera_ai.simulation_engine.state import PlanetState


class PlanetRepository(Protocol):
    async def save_checkpoint(self, state: PlanetState) -> None: ...
    async def load_latest(self, planet_id: str) -> PlanetState | None: ...
