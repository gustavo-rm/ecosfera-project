"""Travessia DESCENDENTE da cadeia causal: causa → consequências.

O lado de leitura já sabia SUBIR. `walk_causal_chain` (contrato de query do M5)
vai do efeito à raiz pelo `causation_id`, e é com ela que se responde *"por que
isto aconteceu?"*. Este módulo acrescenta a direção que faltava: dado um
acontecimento, **o que decorreu dele** — a pergunta *"e daí o que aconteceu?"*,
que é a que sustenta uma narrativa em ordem cronológica.

## Por que descer não é subir ao contrário

Subir é um caminho: cada evento tem no máximo UMA causa (`causation_id` é
escalar), então a subida é uma lista. Descer é uma ÁRVORE: um mesmo meteoro pode
causar um resfriamento, um incêndio e uma extinção, e cada um desses pode ter
consequências próprias. Inverter a lista da subida entregaria um ramo só, e o
Tutor narraria a cascata do meteoro citando um único efeito como se fosse todo o
resultado — verdadeiro em cada elo e falso no conjunto.

## Por que a árvore vem daqui e não do evento

O campo `consequences` do envelope §4 existe, e os Engines NÃO o preenchem — no
instante em que emitem, os efeitos ainda não aconteceram, e inventá-los exigiria
que um Engine soubesse o que os seguintes vão fazer. A ligação para a frente é
PROJEÇÃO sobre o Event Store, feita depois do fato (ADR-ARCH-0002), e é esta.

## Duas propriedades que os testes exigem

* **Nenhum evento se perde.** Todo evento da fatia aparece EXATAMENTE uma vez na
  floresta. Uma trilha em que um evento some é pior que uma incompleta: o dossiê
  parece íntegro e não é.
* **A ordem é determinística.** Irmãos saem ordenados por (era, tick, id), nunca
  pela ordem de chegada — que é acidente de execução e faria o mesmo log produzir
  dossiês diferentes.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ecosfera_ai.shared_kernel.events import DomainEvent, event_to_dict


def _order_key(event: DomainEvent) -> tuple[int, int, str]:
    """Tempo de SIMULAÇÃO, com o id como desempate — nunca ordem de chegada."""
    return (event.occurred_at.era, event.occurred_at.tick, event.event_id)


@dataclass(frozen=True, slots=True)
class CausalNode:
    """Um evento e o que decorreu dele, recursivamente."""

    event: DomainEvent
    consequences: tuple[CausalNode, ...] = ()

    def walk(self) -> Iterator[DomainEvent]:
        """Percorre a subárvore em pré-ordem (a causa antes das consequências)."""
        yield self.event
        for child in self.consequences:
            yield from child.walk()

    @property
    def depth(self) -> int:
        """Comprimento do ramo mais longo — 1 para uma folha."""
        return 1 + max((child.depth for child in self.consequences), default=0)

    def to_dict(self) -> dict[str, Any]:
        """Árvore como dado portável, para inspeção humana e teste de aceite."""
        return {
            "event": event_to_dict(self.event),
            "consequences": [child.to_dict() for child in self.consequences],
        }


def _children_of(events: Sequence[DomainEvent]) -> dict[str, list[DomainEvent]]:
    """Inverte `causation_id`: de cada evento para os que ele causou.

    Só conta o elo cuja CAUSA também está na fatia. Um evento cuja causa ficou de
    fora não é órfão — é raiz local, e é assim que ele entra na floresta.
    """
    index = {event.event_id: event for event in events}
    children: dict[str, list[DomainEvent]] = {}
    for event in events:
        parent = event.causation_id
        if parent is None or parent not in index:
            continue
        children.setdefault(parent, []).append(event)
    return children


def _grow(
    event: DomainEvent,
    children: Mapping[str, list[DomainEvent]],
    seen: set[str],
) -> CausalNode:
    """Expande um nó, marcando o que já entrou na floresta.

    `seen` é compartilhado por toda a floresta e serve a dois propósitos ao mesmo
    tempo: garante que cada evento apareça uma única vez e corta ciclos. Ciclo em
    `causation_id` é trilha corrompida (um import malfeito, por exemplo) — e uma
    trilha corrompida não pode travar o consumidor em recursão infinita.
    """
    seen.add(event.event_id)
    grown = [
        _grow(child, children, seen)
        for child in sorted(children.get(event.event_id, ()), key=_order_key)
        if child.event_id not in seen
    ]
    return CausalNode(event=event, consequences=tuple(grown))


def build_causal_forest(events: Sequence[DomainEvent]) -> tuple[CausalNode, ...]:
    """Reconstrói a floresta causa→consequências da fatia.

    São raízes os eventos sem `causation_id` e os que apontam para uma causa fora
    da fatia — a segunda regra é o que faz uma fatia por era continuar navegável
    quando a causa ficou na era anterior.

    A varredura final promove a raiz o que sobrou: com um ciclo na trilha, nenhum
    de seus membros é raiz natural, e sem esta linha eles desapareceriam do
    dossiê em silêncio. Perder o evento seria pior que exibi-lo com a causa
    truncada — o dossiê ficaria íntegro na aparência.
    """
    ordered = sorted(events, key=_order_key)
    index = {event.event_id: event for event in ordered}
    children = _children_of(ordered)
    seen: set[str] = set()

    forest = [
        _grow(event, children, seen)
        for event in ordered
        if event.causation_id is None or event.causation_id not in index
    ]
    forest.extend(_grow(event, children, seen) for event in ordered if event.event_id not in seen)
    return tuple(forest)


def descendants_of(events: Sequence[DomainEvent], event_id: str) -> tuple[DomainEvent, ...]:
    """Tudo o que decorreu do evento, direta ou indiretamente — ele fora.

    É o complemento exato de `walk_causal_chain`: aquela sobe do efeito à raiz,
    esta desce da causa a todas as folhas. Juntas dão as duas direções sobre o
    MESMO mecanismo (`causation_id`), sem uma segunda leitura do Event Store.
    """
    ordered = sorted(events, key=_order_key)
    if event_id not in {event.event_id for event in ordered}:
        return ()
    children = _children_of(ordered)

    found: list[DomainEvent] = []
    seen = {event_id}
    frontier = [event_id]
    while frontier:
        current = frontier.pop(0)
        for child in sorted(children.get(current, ()), key=_order_key):
            if child.event_id in seen:
                continue
            seen.add(child.event_id)
            found.append(child)
            frontier.append(child.event_id)
    return tuple(sorted(found, key=_order_key))


__all__ = ["CausalNode", "build_causal_forest", "descendants_of"]
