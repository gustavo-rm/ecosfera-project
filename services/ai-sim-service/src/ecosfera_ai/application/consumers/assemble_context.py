"""Monta o dossiê factual a partir do Event Store — o caso de uso do M6.0.

Consome o contrato de leitura do M5 (`EventStoreQuery`), escopado por planeta
segundo o ADR 0023. Não recalcula ciência, não toca no world-state, não chama
Engine algum, não escreve no Event Store — e não conhece LLM, que é a subetapa
M6.3 e não esta.

## O que este caso de uso acrescenta ao lado de leitura

Nada de LEITURA nova: a porta é a do M5, sem uma segunda consulta paralela. O que
entra é a RECONSTRUÇÃO — a floresta causa→consequências (`build_causal_forest`),
que o contrato de query não tinha porque ele só sabia subir.

Esta é a lógica que mais precisa de teste, e a razão é o espelho exato do defeito
que o M4 encontrou do lado da escrita: lá, uma extinção catastrófica encadeava ao
`TemperatureShift` do mesmo tick em vez de ao meteoro. Uma cadeia mal
reconstruída AQUI produz o mesmo erro do lado da leitura — o Tutor conta a
história causal errada com toda a autoridade de estar "ancorado no Event Store".
Por isso os testes ANDAM a cadeia pelo `causation_id` e afirmam a ÁRVORE; a
coocorrência num mesmo tick não prova elo nenhum.

## Determinismo

Mesma trilha, mesmo dossiê, sempre. Nenhuma ordenação depende da ordem de
chegada, nenhum identificador é sorteado, nenhum relógio é lido. É o que permite
ao M6.4 comparar saídas entre execuções sem que a diferença seja ruído desta
camada.
"""

from __future__ import annotations

from ecosfera_ai.application.platform.event_query import EventQuery, EventStoreQuery
from ecosfera_ai.domain.consumers.causal_tree import descendants_of
from ecosfera_ai.domain.consumers.factual_context import (
    ContextSlice,
    FactualContext,
    SliceKind,
)
from ecosfera_ai.shared_kernel.events import DomainEvent


def _spec_for(context_slice: ContextSlice) -> EventQuery:
    """Traduz o recorte para o predicado do contrato de query do M5.

    O planeta NÃO entra aqui: ele é escopo da porta, não predicado sobre o evento
    (ADR 0023). Um `planet_id` dentro do `EventQuery` foi exatamente o filtro
    fantasma que aquele ADR removeu.
    """
    if context_slice.kind is SliceKind.ERA:
        return EventQuery(era=context_slice.era)
    if context_slice.kind is SliceKind.TICKS:
        return EventQuery(from_tick=context_slice.from_tick, to_tick=context_slice.to_tick)
    # O recorte por evento não é um predicado de campo: a fatia é a cadeia
    # causal, e ela se recorta depois de ler a trilha do planeta.
    return EventQuery()


class ContextAssembler:
    """Dado um planeta e um recorte, entrega o dossiê factual daquele recorte."""

    def __init__(self, events: EventStoreQuery) -> None:
        self._events = events

    async def execute(self, planet_id: str, context_slice: ContextSlice) -> FactualContext:
        """Monta o dossiê. Fatia vazia devolve dossiê VAZIO, nunca erro."""
        if context_slice.kind is SliceKind.EVENT:
            return await self._around_event(planet_id, context_slice)
        found = await self._events.query(planet_id, _spec_for(context_slice))
        if not found:
            return FactualContext.empty(planet_id, context_slice)
        return FactualContext.of(planet_id, context_slice, tuple(found))

    async def _around_event(self, planet_id: str, context_slice: ContextSlice) -> FactualContext:
        """O contexto de UM evento: ele, o que o causou e o que dele decorreu.

        A subida reusa `causal_chain` da porta (que é o `walk_causal_chain` do
        M5); a descida é a floresta nova. As duas atravessam o MESMO
        `causation_id`, e nenhuma delas relê o Event Store por conta própria.

        A trilha visível é a projeção científica — `EventQuery()` já exclui o
        diagnóstico técnico. Ela decide o que existe para este dossiê, inclusive
        para a subida: um estouro de orçamento não é fenômeno do planeta, e o
        Tutor não narra a reclamação do motor como se fosse acontecimento
        (ADR-ARCH-0002).
        """
        event_id = str(context_slice.event_id)
        trail = tuple(await self._events.query(planet_id, _spec_for(context_slice)))
        visible = {event.event_id for event in trail}
        if event_id not in visible:
            return FactualContext.empty(planet_id, context_slice)

        ascending = tuple(
            event
            for event in await self._events.causal_chain(planet_id, event_id)
            if event.event_id in visible
        )
        descending = descendants_of(trail, event_id)

        collected: dict[str, DomainEvent] = {event.event_id: event for event in ascending}
        collected.update({event.event_id: event for event in descending})
        return FactualContext.of(
            planet_id,
            context_slice,
            tuple(collected.values()),
            ancestry=ascending,
        )


__all__ = ["ContextAssembler"]
