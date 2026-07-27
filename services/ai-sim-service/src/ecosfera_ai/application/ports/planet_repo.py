"""Porta de saída para persistir o planeta: estado corrente e linha do tempo.

Checkpoints são append-only por era (Dossiê §9): cada era fecha com um estado
imutável, e o log de eventos guarda o que não é derivável do motor determinístico
(intervenções do aluno e marcos narrativos). Juntos permitem reconstruir qualquer
era (RF-016) sem gravar o estado de cada tick.

O adaptador in-memory serve ao MVP/testes; o adaptador Postgres o substitui sem
tocar nas camadas superiores (ADR 0001/0005).
"""

from __future__ import annotations

from typing import Protocol

from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.timeline import EraCheckpoint, EraSummary, EventLogEntry


class PlanetRepository(Protocol):
    # --- Estado corrente (usado pelo tick fino) --------------------------------
    async def save_checkpoint(self, state: PlanetState) -> None: ...
    async def load_latest(self, planet_id: str) -> PlanetState | None: ...

    # --- Linha do tempo append-only (eras + eventos) ---------------------------
    async def append_checkpoint(self, checkpoint: EraCheckpoint) -> None: ...
    async def append_event(self, entry: EventLogEntry) -> None: ...
    async def load_checkpoint(self, planet_id: str, era: int) -> EraCheckpoint | None: ...
    async def load_events(
        self, planet_id: str, from_tick: int, to_tick: int
    ) -> list[EventLogEntry]: ...
    async def get_timeline(self, planet_id: str) -> list[EraSummary]: ...
