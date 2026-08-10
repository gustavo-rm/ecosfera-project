"""Event Store persistente do envelope §4 — escrita e leitura escopadas por planeta.

O M5 criou as colunas do envelope (migration 0004) e testou-as por SQL cru, mas
não deixou nem escritor nem porta de leitura: `append_event` continuava gravando
as quatro colunas do M2 (`planet_id, tick, event_type, payload`), e as oito do
envelope ficavam NULL em toda linha que o serviço escrevia. A afirmação "Event
Store persistente com o envelope §4" era verdadeira do teste, não do serviço.

Este módulo fecha as duas pontas:

* `PostgresEventStore.append` grava o envelope §4 inteiro, coluna a coluna;
* `PostgresEventQuery` implementa `EventStoreQuery` reconstruindo `DomainEvent`
  das colunas — não devolve o `EventLogEntry` do M2, que é outro formato e não
  serve ao consumidor.

## O planeta é escopo, não predicado

`WHERE planet_id = :planet_id` é a PRIMEIRA coisa que toda consulta faz, no SQL,
antes de qualquer filtro de campo. É a decisão do ADR 0023: planeta é dimensão de
armazenamento. Um evento "erupção no tick 1200" é o mesmo fato em qualquer
planeta; em qual planeta ele está é onde está guardado.

## Um único lugar decide o que casa

Os filtros de campo NÃO são reescritos em SQL. A consulta traz a trilha já
escopada no planeta e aplica `EventQuery.matches()` — o mesmo predicado que a
implementação em memória usa.

É deliberado, e o motivo é a dívida que este módulo corrige: o M5 tinha a regra
de filtro escrita num lugar e um campo declarado noutro, e os dois divergiram sem
que nada acusasse. Duas cópias do predicado — uma em SQL, uma em Python —
divergiriam do mesmo jeito, e a divergência apareceria como o Tutor citando um
evento que o filtro dizia ter excluído.

O custo é ler a trilha do planeta inteira: algumas centenas de eventos numa
corrida de 500 ticks. Se um dia doer, o caminho SEM reintroduzir a divergência é
GERAR o WHERE a partir do próprio `EventQuery`, nunca escrevê-lo à mão em
paralelo.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ecosfera_ai.application.platform.event_query import (
    EventQuery,
    EventStoreQuery,
    walk_causal_chain,
)
from ecosfera_ai.shared_kernel.events import (
    DomainEvent,
    Granularity,
    SimulationTime,
    event_from_dict,
    event_to_dict,
)

# As colunas do envelope §4 que a 0004 criou, mais as quatro do M2.
_INSERT = text(
    """
    INSERT INTO simulation.event_log (
        planet_id, tick, era, event_type, payload,
        event_id, engine_id, seed, cause_code,
        correlation_id, causation_id, granularity
    ) VALUES (
        :planet_id, :tick, :era, :event_type, CAST(:payload AS jsonb),
        :event_id, :engine_id, :seed, :cause_code,
        :correlation_id, :causation_id, :granularity
    )
    ON CONFLICT (planet_id, event_id) WHERE event_id IS NOT NULL DO NOTHING
    """
)

_SELECT_SCOPED = text(
    """
    SELECT event_id, event_type, engine_id, tick, era, seed, cause_code,
           correlation_id, causation_id, granularity, payload
      FROM simulation.event_log
     WHERE planet_id = :planet_id
       AND event_id IS NOT NULL
     ORDER BY era, tick, event_id
    """
)


def _row_to_event(row: Any) -> DomainEvent:
    """Reconstrói o `DomainEvent` do envelope §4 gravado.

    O `payload` guarda o que não virou coluna — participantes, fatores
    ambientais, genes, recursos, `cause_detail`, `location`, `consequences`. As
    colunas existem para poder INDEXAR e consultar; o payload existe para não
    perder o resto do envelope. Reconstruir usa as duas.
    """
    payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload or "{}")
    data = dict(payload)
    data.update(
        {
            "event_id": row.event_id,
            "event_type": row.event_type,
            "engine_id": row.engine_id,
            "tick": row.tick,
            "era": row.era,
            "seed": row.seed,
            "cause_code": row.cause_code,
            "correlation_id": row.correlation_id,
            "causation_id": row.causation_id,
            "granularity": row.granularity or Granularity.AGGREGATE.value,
        }
    )
    return event_from_dict(data)


def _event_to_params(planet_id: str, event: DomainEvent) -> dict[str, Any]:
    """Separa o envelope entre colunas indexáveis e payload — sem perder nada.

    O que sai do payload é exatamente o que virou coluna. Manter a duplicata
    convidaria a que as duas cópias discordassem depois de um import, e a
    reconstrução teria de escolher uma sem critério.
    """
    body = event_to_dict(event)
    for promoted in (
        "event_id",
        "event_type",
        "engine_id",
        "tick",
        "era",
        "seed",
        "cause_code",
        "correlation_id",
        "causation_id",
        "granularity",
    ):
        body.pop(promoted, None)
    return {
        "planet_id": planet_id,
        "tick": event.occurred_at.tick,
        "era": event.occurred_at.era,
        "event_type": event.event_type,
        "payload": json.dumps(body, sort_keys=True),
        "event_id": event.event_id,
        "engine_id": event.engine_id,
        "seed": event.seed,
        "cause_code": str(event.cause_code.value),
        "correlation_id": event.correlation_id,
        "causation_id": event.causation_id,
        "granularity": event.granularity.value,
    }


class PostgresEventStore:
    """Escrita append-only do envelope §4, escopada por planeta."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def append(self, planet_id: str, event: DomainEvent) -> None:
        await self.append_many(planet_id, (event,))

    async def append_many(self, planet_id: str, events: Iterable[DomainEvent]) -> None:
        """Grava a trilha.

        `ON CONFLICT (planet_id, event_id) DO NOTHING` faz a idempotência ser
        propriedade do BANCO e não da disciplina de quem escreve: como o
        `event_id` é determinístico, reprocessar a corrida do mesmo planeta não
        pode duplicar a trilha. O grão é POR PLANETA (migration 0005) — dois
        planetas de mesma semente produzem `event_id` idênticos, e globalmente o
        segundo seria recusado como se fosse reprocessamento do primeiro.
        """
        rows = [_event_to_params(planet_id, event) for event in events]
        if not rows:
            return
        async with self._engine.begin() as conn:
            await conn.execute(_INSERT, rows)


class PostgresEventQuery:
    """Porta de leitura `EventStoreQuery` sobre o Event Store persistente."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _scoped(self, planet_id: str) -> tuple[DomainEvent, ...]:
        """A trilha de UM planeta, já ordenada por tempo de simulação."""
        async with self._engine.connect() as conn:
            result = await conn.execute(_SELECT_SCOPED, {"planet_id": planet_id})
            return tuple(_row_to_event(row) for row in result)

    async def query(self, planet_id: str, spec: EventQuery) -> Sequence[DomainEvent]:
        return tuple(e for e in await self._scoped(planet_id) if spec.matches(e))

    async def causal_chain(self, planet_id: str, event_id: str) -> Sequence[DomainEvent]:
        """Sobe a cadeia DENTRO do planeta.

        O escopo aqui não é otimização: `event_id` só é único por planeta, então
        subir a cadeia sem escopar poderia sair da corrida do aluno no meio do
        caminho e devolver a causa de outro planeta.
        """
        return walk_causal_chain(await self._scoped(planet_id), event_id)


def _port_conformance(engine: AsyncEngine) -> EventStoreQuery:
    """Prova, em tempo de checagem de tipo, que o adaptador satisfaz a porta.

    Sem esta linha, `PostgresEventQuery` poderia divergir da assinatura de
    `EventStoreQuery` — trocar a ordem dos parâmetros, perder o `planet_id` — e
    o mypy nada diria, porque ninguém a atribui à porta em lugar nenhum do
    código de produção. O teste de paridade cobre o COMPORTAMENTO; isto cobre a
    forma, que é onde a divergência começa.
    """
    return PostgresEventQuery(engine)


__all__ = [
    "PostgresEventQuery",
    "PostgresEventStore",
    "SimulationTime",
]
