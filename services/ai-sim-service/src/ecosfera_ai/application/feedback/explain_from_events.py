"""Feedback causal derivado do Event Store, não do world-state (ADR 0011).

Fecha o embrião do AI Tutor previsto no ADR-ARCH-0001: um consumidor read-side
que explica o fenômeno **sem recalcular ciência** e **sem inspecionar memória de
Engine**. Ele lê a trilha de eventos e a traduz em observações, que o motor de
regras determinístico de sempre narra. Não há LLM aqui — isso é o M6.

Duas fronteiras que este módulo respeita de propósito:

* **Não importa nenhum Engine.** Conhece o vocabulário dos eventos (nomes de
  tipo e campos de `cause_detail`), que vem de `configs/event_observations.yaml`.
  Um Engine pode ser reescrito inteiro sem tocar aqui, desde que continue
  emitindo o mesmo envelope §4.
* **Não escreve prosa científica.** O evento traz `cause_code` estruturado; a
  frase sai do motor de regras, que é o consumidor. É a Correção 1 do
  ADR-ARCH-0002 aplicada na prática.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.domain.feedback.models import CausalExplanation, Observation
from ecosfera_ai.shared_kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class EventMapping:
    """Como um tipo de evento vira uma observação do motor de regras."""

    event_type: str
    variable: str
    field: str | None = None
    minuend: str | None = None
    subtrahend: str | None = None

    def delta_of(self, detail: Mapping[str, Any]) -> float | None:
        """Extrai a magnitude do `cause_detail`, ou None se o evento não a traz."""
        if self.field is not None:
            value = detail.get(self.field)
            return None if value is None else float(value)
        if self.minuend is not None and self.subtrahend is not None:
            after, before = detail.get(self.minuend), detail.get(self.subtrahend)
            if after is None or before is None:
                return None
            return float(after) - float(before)
        return None


@dataclass(frozen=True, slots=True)
class EventTranslation:
    """Tabela versionada de tradução evento -> observação."""

    version: int
    mappings: Mapping[str, EventMapping]

    def observations(self, events: Iterable[DomainEvent]) -> list[Observation]:
        """Traduz a trilha, ignorando diagnóstico técnico e tipos desconhecidos.

        Um evento sem tradução é silenciosamente pulado: o Event Store cresce com
        Engines novos, e o tutor não pode quebrar porque apareceu um tipo que ele
        ainda não sabe narrar.
        """
        result: list[Observation] = []
        for event in events:
            if event.is_diagnostic:
                continue
            mapping = self.mappings.get(event.event_type)
            if mapping is None:
                continue
            delta = mapping.delta_of(event.cause_detail)
            if delta is None or delta == 0.0:
                continue
            result.append(Observation(variable=mapping.variable, delta=delta))
        return result


def load_translation(path: Path) -> EventTranslation:
    """Lê a tabela do YAML versionado."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mappings: dict[str, EventMapping] = {}
    for entry in raw.get("mappings", []):
        source = entry.get("delta_from", {})
        mappings[str(entry["event_type"])] = EventMapping(
            event_type=str(entry["event_type"]),
            variable=str(entry["variable"]),
            field=source.get("field"),
            minuend=source.get("minuend"),
            subtrahend=source.get("subtrahend"),
        )
    return EventTranslation(version=int(raw.get("version", 1)), mappings=mappings)


@dataclass(frozen=True, slots=True)
class CausalLink:
    """Um elo do rastro causal, reconstruído por `causation_id`."""

    cause_event: str
    cause_type: str
    effect_event: str
    effect_type: str
    cause_code: str


@dataclass(frozen=True, slots=True)
class EventExplanation:
    """Explicação do tutor mais o rastro que a sustenta (auditabilidade)."""

    explanation: CausalExplanation
    trace: tuple[CausalLink, ...] = ()


class ExplainFromEventsUseCase:
    """Narra a cadeia causal a partir da trilha de eventos, sem LLM."""

    def __init__(self, explain: ExplainCausalUseCase, translation: EventTranslation) -> None:
        self._explain = explain
        self._translation = translation

    def execute(self, planet_id: str, events: Sequence[DomainEvent]) -> EventExplanation:
        observations = self._translation.observations(events)
        return EventExplanation(
            explanation=self._explain.execute(planet_id, observations),
            trace=causal_trace(events),
        )


def causal_trace(events: Sequence[DomainEvent]) -> tuple[CausalLink, ...]:
    """Reconstrói os elos causa->efeito invertendo `causation_id`.

    Os Engines não preenchem `consequences` na emissão porque, no instante em que
    emitem, os efeitos ainda não aconteceram — inventá-los exigiria que um Engine
    soubesse o que os seguintes vão fazer. A ligação para a frente é PROJEÇÃO do
    Event Store, e é esta função.
    """
    by_id = {event.event_id: event for event in events}
    links: list[CausalLink] = []
    for event in events:
        parent = by_id.get(event.causation_id) if event.causation_id else None
        if parent is None:
            continue
        links.append(
            CausalLink(
                cause_event=parent.event_id,
                cause_type=parent.event_type,
                effect_event=event.event_id,
                effect_type=event.event_type,
                cause_code=str(event.cause_code),
            )
        )
    return tuple(links)
