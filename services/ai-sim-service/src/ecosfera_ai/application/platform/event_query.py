"""Contrato de LEITURA do Event Store — o que o M6 vai assinar.

O ADR-ARCH-0002 fala em "três públicos, uma fonte de verdade": científico,
técnico e educacional leem a MESMA trilha por projeções diferentes. Este módulo
entrega o contrato de consulta e duas projeções; a educacional é do M6 e NÃO é
implementada aqui — o que se garante é que o envelope carrega tudo de que ela
precisará.

## Por que um contrato, e não consumidores

Implementar consumidores agora fixaria decisões de produto que ainda não foram
tomadas (o que `/species` significa, por exemplo — `docs/decisions/pending.md`).
O que o M5 deve entregar é a SUPERFÍCIE: por planeta, era, correlação, causa. O
M6 assina isso sem renegociar o formato.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from ecosfera_ai.shared_kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class EventQuery:
    """Filtro de consulta. Campos ausentes não restringem."""

    planet_id: str | None = None
    era: int | None = None
    from_tick: int | None = None
    to_tick: int | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    cause_codes: frozenset[str] = field(default_factory=frozenset)
    event_types: frozenset[str] = field(default_factory=frozenset)
    engine_ids: frozenset[str] = field(default_factory=frozenset)
    # Diagnóstico técnico fica FORA por padrão: a visão científica não deve ver
    # estouro de orçamento como se fosse fenômeno do planeta (ADR-ARCH-0002).
    include_diagnostics: bool = False

    def matches(self, event: DomainEvent) -> bool:
        if not self.include_diagnostics and event.is_diagnostic:
            return False
        if self.era is not None and event.occurred_at.era != self.era:
            return False
        if self.from_tick is not None and event.occurred_at.tick < self.from_tick:
            return False
        if self.to_tick is not None and event.occurred_at.tick > self.to_tick:
            return False
        if self.correlation_id is not None and event.correlation_id != self.correlation_id:
            return False
        if self.causation_id is not None and event.causation_id != self.causation_id:
            return False
        if self.cause_codes and str(event.cause_code.value) not in self.cause_codes:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        return not self.engine_ids or event.engine_id in self.engine_ids


class EventStoreQuery(Protocol):
    """Porta de leitura. O M6 depende DESTA assinatura, não de um adaptador."""

    def query(self, spec: EventQuery) -> Sequence[DomainEvent]: ...

    def causal_chain(self, event_id: str) -> Sequence[DomainEvent]: ...


@dataclass(frozen=True, slots=True)
class InMemoryEventQuery:
    """Implementação sobre uma trilha em memória — a de referência do contrato."""

    events: Sequence[DomainEvent]

    def query(self, spec: EventQuery) -> Sequence[DomainEvent]:
        return tuple(event for event in self.events if spec.matches(event))

    def causal_chain(self, event_id: str) -> Sequence[DomainEvent]:
        """Sobe a cadeia pelo `causation_id`, do efeito até a raiz.

        É a operação que o Tutor usa para responder "por que isso aconteceu?", e
        a que reconstrói `MeteorImpact → … → SpeciesExtinct`. O corte por ciclo
        não é defensivo por precaução: uma trilha corrompida por import não pode
        travar o consumidor.
        """
        index = {event.event_id: event for event in self.events}
        current = index.get(event_id)
        if current is None:
            return ()

        chain: list[DomainEvent] = [current]
        seen = {current.event_id}
        while current.causation_id and current.causation_id in index:
            parent = index[current.causation_id]
            if parent.event_id in seen:
                break
            chain.append(parent)
            seen.add(parent.event_id)
            current = parent
        return tuple(chain)


# --- As projeções (ADR-ARCH-0002, "três públicos") ----------------------------


@dataclass(frozen=True, slots=True)
class ScientificProjection:
    """Visão CIENTÍFICA: o fenômeno, sem o ruído técnico.

    Para pesquisa, replay e professor avançado. Filtra o diagnóstico e ordena por
    tempo de simulação — não por ordem de chegada, que é acidente de execução.
    """

    events: Sequence[DomainEvent]

    def of(self, planet_id: str | None = None, era: int | None = None) -> list[DomainEvent]:
        spec = EventQuery(planet_id=planet_id, era=era, include_diagnostics=False)
        return sorted(
            (e for e in self.events if spec.matches(e)),
            key=lambda e: (e.occurred_at.era, e.occurred_at.tick, e.event_id),
        )

    def by_cause(self) -> dict[str, int]:
        """Quantas vezes cada mecanismo ocorreu — o mapa que a pesquisa quer."""
        counts: dict[str, int] = {}
        for event in self.of():
            key = str(event.cause_code.value)
            counts[key] = counts.get(key, 0) + 1
        return counts


@dataclass(frozen=True, slots=True)
class TechnicalProjection:
    """Visão TÉCNICA: só o diagnóstico — orçamento estourado, invariante violada.

    O inverso exato da científica. Um operador quer ver o que o motor reclamou;
    misturar isso ao fenômeno faria o pesquisador tratar um estouro de orçamento
    como evento do planeta.
    """

    events: Sequence[DomainEvent]

    def diagnostics(self) -> list[DomainEvent]:
        return [event for event in self.events if event.is_diagnostic]

    def by_engine(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self.diagnostics():
            engine = str(event.cause_detail.get("engine", event.engine_id))
            counts[engine] = counts.get(engine, 0) + 1
        return counts


def educational_payload_is_complete(events: Iterable[DomainEvent]) -> bool:
    """A visão EDUCACIONAL é do M6 — aqui só se confere que nada lhe falta.

    Ela precisará, de cada evento: o mecanismo (`cause_code`), o elo causal
    (`causation_id`), o instante (`occurred_at`) e os números que sustentam a
    frase (`cause_detail`). Se algum evento não os traz, o M6 descobriria tarde.
    """
    for event in events:
        if event.is_diagnostic:
            continue
        if not event.cause_code or not event.correlation_id:
            return False
        if not event.cause_detail and not event.participants:
            return False
    return True
