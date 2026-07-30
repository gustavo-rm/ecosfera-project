"""Contrato de replay (Spec §7): reconstruir uma era bit-a-bit a partir da semente.

Entrada: a semente, o checkpoint da era anterior e o log append-only de eventos.
Saída: o `WorldStateSnapshot` daquele ponto da trajetória, idêntico ao gravado.

A reconstrução é por **reexecução**, não por reaplicação de deltas gravados. É
uma escolha deliberada: reaplicar deltas só prova que a serialização funciona,
enquanto reexecutar prova a propriedade que interessa — que a semente basta.
Divergência entre o reconstruído e o gravado é bug de determinismo e bloqueia
merge (Spec §7), então o teste precisa ser capaz de acusá-la.

`events` entra como evidência a conferir: `verify_replay` compara a sequência
regenerada com a gravada, que é o segundo critério do §7 ("reexecutar a era
reproduz a MESMA sequência de eventos").
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot


@dataclass(frozen=True, slots=True)
class StepOutcome:
    """Um passo de reexecução: novo snapshot e os eventos que ele produziu."""

    snapshot: WorldStateSnapshot
    events: tuple[DomainEvent, ...] = ()


# O `stepper` é a função pura de avanço — na prática, `PlanetEngine.tick`. Ele é
# INJETADO em vez de importado para que `replay` continue puro e testável sem
# montar um registro de Engines (mesmo padrão de `simulation_engine/timeline.py`).
Stepper = Callable[[WorldStateSnapshot], StepOutcome]


class ReplayMismatchError(Exception):
    """A reconstrução divergiu do gravado — determinismo quebrado."""


@dataclass(frozen=True, slots=True)
class ReplayReport:
    """Resultado auditável de uma reconstrução."""

    snapshot: WorldStateSnapshot
    events: tuple[DomainEvent, ...]
    matches_events: bool
    matches_snapshot: bool | None = None

    @property
    def deterministic(self) -> bool:
        """Verdadeiro só se TUDO o que se pôde comparar bateu."""
        return self.matches_events and self.matches_snapshot is not False


def replay(
    seed: int,
    checkpoint: WorldStateSnapshot,
    events: Sequence[DomainEvent],
    *,
    stepper: Stepper,
    until_tick: int,
) -> WorldStateSnapshot:
    """Reconstrói o estado em `until_tick` a partir do checkpoint (Spec §7)."""
    return verify_replay(seed, checkpoint, events, stepper=stepper, until_tick=until_tick).snapshot


def verify_replay(
    seed: int,
    checkpoint: WorldStateSnapshot,
    events: Sequence[DomainEvent],
    *,
    stepper: Stepper,
    until_tick: int,
    expected: WorldStateSnapshot | None = None,
) -> ReplayReport:
    """Reconstrói e confere: mesma sequência de eventos e mesmo estado final."""
    if checkpoint.seed != seed:
        raise ReplayMismatchError(
            f"checkpoint da semente {checkpoint.seed} não pode ser reproduzido sob {seed}"
        )
    if until_tick < checkpoint.tick:
        raise ReplayMismatchError(
            f"until_tick={until_tick} é anterior ao checkpoint (tick={checkpoint.tick})"
        )

    snapshot = checkpoint
    regenerated: list[DomainEvent] = []
    while snapshot.tick < until_tick:
        outcome = stepper(snapshot)
        if outcome.snapshot.tick <= snapshot.tick:
            raise ReplayMismatchError(
                "o stepper não avançou o tick; replay entraria em laço infinito"
            )
        snapshot = outcome.snapshot
        regenerated.extend(outcome.events)

    recorded_ids = tuple(event.event_id for event in events)
    matches_events = not recorded_ids or recorded_ids == tuple(e.event_id for e in regenerated)
    matches_snapshot = None if expected is None else expected == snapshot
    return ReplayReport(
        snapshot=snapshot,
        events=tuple(regenerated),
        matches_events=matches_events,
        matches_snapshot=matches_snapshot,
    )
