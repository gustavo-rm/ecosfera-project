"""Porta comum de Engine de simulação (Spec §5.2) e o contexto de um tick.

Um Engine é uma função pura disfarçada de objeto: recebe um snapshot read-only
e um RNG semeado, devolve o delta da sua fatia e os eventos que julgou notáveis.
Não persiste, não loga, não mede tempo, não conhece outro Engine.

## Por que `tick` é SÍNCRONO

O loop determinístico não pode ser `async`. Corrotinas introduzem ordem de
escalonamento como variável oculta; sob `asyncio` a mesma semente poderia
produzir intercalações distintas e o replay bit-a-bit deixaria de valer. A
fronteira síncrono/assíncrono é, deliberadamente, a mesma fronteira
determinístico/observável: o loop é síncrono e puro, a borda de I/O (FastAPI,
persistência, fila, Event Store) é assíncrona e orquestra o loop por fora
(ADR 0008).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta, WorldStateSnapshot


class EngineGraphError(Exception):
    """Registro de Engines inconsistente — falha no boot, nunca em produção."""


@dataclass(frozen=True, slots=True)
class TickBudget:
    """Teto declarado por tick (Spec §6): tempo, eventos e entidades.

    Estourar o teto emite um `DiagnosticEvent` e **nada mais**. Pular um Engine
    lento mudaria o resultado da simulação em função da carga da máquina —
    exatamente o acoplamento que o ADR-ARCH-0002 proíbe.
    """

    max_duration_s: float = 1.0
    max_events: int = 1_000
    max_entities: int = 100_000


@dataclass(frozen=True, slots=True)
class PerfSample:
    """Medida lateral de um tick de um Engine (Pilar 3 — métricas).

    Nunca entra no world-state nem no envelope científico: é observação sobre a
    execução, não sobre o planeta. Por isso o relógio é do Planet Engine, e não
    do Engine medido — ver `engines/planet/service.py`.
    """

    engine_id: str
    tick: int
    era: int
    duration_s: float
    events_emitted: int
    entities_processed: int

    def exceeded(self, budget: TickBudget) -> tuple[str, ...]:
        """Quais tetos do orçamento este tick estourou (vazio = dentro)."""
        breaches: list[str] = []
        if self.duration_s > budget.max_duration_s:
            breaches.append("duration_s")
        if self.events_emitted > budget.max_events:
            breaches.append("events")
        if self.entities_processed > budget.max_entities:
            breaches.append("entities")
        return tuple(breaches)


@dataclass(frozen=True, slots=True)
class TickContext:
    """Tudo o que um Engine pode ver do mundo durante um tick — e nada além."""

    snapshot: WorldStateSnapshot
    rng: np.random.Generator
    tick: int
    era: int
    budget: TickBudget

    @property
    def seed(self) -> int:
        return self.snapshot.seed


@dataclass(frozen=True, slots=True)
class TickResult:
    """Saída de um Engine: delta (Canal A), eventos (Canal B) e custo medido.

    `perf` sai `None` do Engine e é preenchido pelo Planet Engine, que é quem
    detém o relógio. Se o Engine se cronometrasse, o tempo de parede estaria
    dentro do valor de retorno do cálculo determinístico.
    """

    delta: StateDelta
    events: tuple[DomainEvent, ...] = ()
    entities_processed: int = 0
    perf: PerfSample | None = None


class Engine(Protocol):
    """Contrato que todo Engine da camada de Simulação implementa (Spec §5.2)."""

    engine_id: str
    reads: frozenset[SliceRef]
    lagged_reads: frozenset[SliceRef]
    writes: SliceRef

    def tick(self, ctx: TickContext) -> TickResult: ...


def validate_graph(engines: Sequence[Engine]) -> None:
    """Valida o grafo de dependências no boot; falha rápido e explicando.

    Três defeitos são detectáveis só pelas declarações `reads`/`writes`:

    1. **Identificador duplicado** — dois Engines com o mesmo `engine_id`
       colidiriam nos ids determinísticos de evento e no fluxo de RNG.
    2. **Fatia com dois donos** — quebra a regra de propriedade do Canal A.
    3. **Leitura para trás não declarada** — o Engine lê uma fatia que só será
       escrita mais adiante no mesmo tick, ou seja, enxerga o valor do tick
       ANTERIOR. Isso é legítimo (é como se resolve um acoplamento circular sem
       ciclo — a defasagem deliberada da geologia), mas precisa ser DECLARADO em
       `lagged_reads`. Não declarado, é ordem inconsistente e vira erro.
    """
    seen: set[str] = set()
    for engine in engines:
        if engine.engine_id in seen:
            raise EngineGraphError(f"engine_id duplicado no registro: {engine.engine_id!r}")
        seen.add(engine.engine_id)

    owner: dict[SliceRef, str] = {}
    for engine in engines:
        existing = owner.get(engine.writes)
        if existing is not None:
            raise EngineGraphError(
                f"a fatia {engine.writes} teria dois donos: "
                f"{existing!r} e {engine.engine_id!r}; cada fatia tem um único escritor"
            )
        owner[engine.writes] = engine.engine_id

    position = {engine.engine_id: index for index, engine in enumerate(engines)}
    for engine in engines:
        for ref in engine.reads:
            writer = owner.get(ref)
            if writer is None or writer == engine.engine_id:
                # Fatia sem dono é entrada externa constante; ler a própria é trivial.
                continue
            if position[writer] > position[engine.engine_id]:
                raise EngineGraphError(
                    f"{engine.engine_id!r} lê {ref}, escrita depois por {writer!r}: "
                    "ciclo não resolvido. Declare a fatia em `lagged_reads` se a "
                    "defasagem de um tick for intencional, ou reordene o registro."
                )
