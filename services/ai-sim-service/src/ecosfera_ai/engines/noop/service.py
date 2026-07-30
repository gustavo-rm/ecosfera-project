"""Engine trivial que prova a moldura (critério de conclusão do M0 — Spec §8).

Não modela ciência nenhuma, de propósito: existe para demonstrar que o Planet
Engine registra, ordena, injeta RNG semeado, compõe delta e faz replay — sem que
a prova dependa de nenhuma física estar correta. Se um teste da moldura falha
com este Engine, o defeito é da moldura.

Lê uma fatia (`RESOURCE`), escreve a mesma fatia e emite um evento a cada
`heartbeat_every` ticks, o suficiente para exercitar os dois canais.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import CoreCauseCode, DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta

NOOP_ENGINE_ID = "noop"


@dataclass(slots=True)
class NoOpEngine:
    """Engine sem física: delta vazio e um batimento periódico no Canal B."""

    engine_id: str = NOOP_ENGINE_ID
    heartbeat_every: int = 1
    reads: frozenset[SliceRef] = frozenset({SliceRef.RESOURCE})
    lagged_reads: frozenset[SliceRef] = frozenset()
    writes: SliceRef = SliceRef.RESOURCE

    def tick(self, ctx: TickContext) -> TickResult:
        events: tuple[DomainEvent, ...] = ()
        if self.heartbeat_every > 0 and ctx.tick % self.heartbeat_every == 0:
            emitter = EventEmitter(
                engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era
            )
            events = (
                emitter.emit(
                    "EngineHeartbeat",
                    CoreCauseCode.ENGINE_HEARTBEAT,
                    cause_detail={"tick": ctx.tick},
                ),
            )
        return TickResult(
            delta=StateDelta(engine_id=self.engine_id, tick=ctx.tick, writes=self.writes),
            events=events,
        )
