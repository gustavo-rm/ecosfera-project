"""Contrato de Observabilidade da moldura (Spec §6, ADR-ARCH-0002).

Quatro pilares sobre UMA fonte de verdade (o Event Store): eventos, logs,
métricas e traces. Logs e métricas são PROJEÇÕES; nenhum deles é consultado
pela simulação.

## A invariante que este módulo existe para proteger

> A simulação nunca depende dos logs. Os logs dependem da simulação.

Operacionalmente isso vira uma regra de chamada, verificada em teste
(`tests/unit/test_observability_purity.py`): **o sink é acionado pelo Planet
Engine DEPOIS de compor o tick**, jamais por um Engine durante o cálculo.
Nenhum caminho de decisão lê métrica, log ou trace. Medir o tempo de tick é
permitido; reagir a ele dentro do loop, não — seria fazer o resultado da
simulação depender da carga da máquina, e o replay morreria com isso.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Protocol

import structlog

from ecosfera_ai.core.observability import (
    engine_budget_exceeded,
    engine_entities_processed,
    engine_events_emitted,
    engine_tick_seconds,
)
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import CoreCauseCode, DomainEvent


class ObservabilitySink(Protocol):
    """Destino lateral dos três sinais que a moldura produz."""

    def record_metrics(self, sample: PerfSample) -> None: ...

    def emit(self, event: DomainEvent) -> None: ...

    def log(self, message: str, /, **fields: object) -> None: ...


class NullSink:
    """Sink que descarta tudo — padrão em testes e no caminho puro.

    Existe para que "sem observabilidade" seja uma escolha explícita, e não um
    `if sink is not None` espalhado pelo Planet Engine.
    """

    def record_metrics(self, sample: PerfSample) -> None:
        del sample

    def emit(self, event: DomainEvent) -> None:
        del event

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields


@dataclass(slots=True)
class InMemoryEventStore:
    """Event Store append-only em memória (fonte de verdade do M0).

    Append-only não é detalhe de implementação: é o que garante que a trilha
    consumida pelo Tutor seja a mesma que o replay reconstrói. Substituível por
    um adaptador Postgres no M5 sem que a moldura mude.
    """

    _events: list[DomainEvent] = field(default_factory=list)

    @property
    def events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._events)

    def record_metrics(self, sample: PerfSample) -> None:
        del sample  # o Event Store guarda eventos; métricas têm sink próprio

    def emit(self, event: DomainEvent) -> None:
        self._events.append(event)

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields

    def by_correlation(self, correlation_id: str) -> tuple[DomainEvent, ...]:
        """Cadeia causal de um instante — a consulta que o Tutor faz (Pilar 4)."""
        return tuple(e for e in self._events if e.correlation_id == correlation_id)

    def scientific_view(self) -> tuple[DomainEvent, ...]:
        """Projeção científica: tudo menos o diagnóstico técnico."""
        return tuple(e for e in self._events if not e.is_diagnostic)

    def technical_view(self) -> tuple[DomainEvent, ...]:
        """Projeção técnica: só os `DiagnosticEvent`s."""
        return tuple(e for e in self._events if e.is_diagnostic)


class PrometheusMetricsSink:
    """Pilar 3 — tempo, eventos e entidades por Engine e por tick."""

    def record_metrics(self, sample: PerfSample) -> None:
        engine_tick_seconds.labels(engine=sample.engine_id).observe(sample.duration_s)
        engine_events_emitted.labels(engine=sample.engine_id).inc(sample.events_emitted)
        engine_entities_processed.labels(engine=sample.engine_id).inc(sample.entities_processed)

    def emit(self, event: DomainEvent) -> None:
        """Deriva o contador de orçamento do EVENTO, não de um canal paralelo.

        Métrica é projeção de evento (ADR-ARCH-0002): se o `DiagnosticEvent` não
        foi emitido, não existe teto estourado a contar.
        """
        if event.cause_code is not CoreCauseCode.BUDGET_EXCEEDED:
            return
        engine_budget_exceeded.labels(
            engine=str(event.cause_detail.get("engine", event.engine_id)),
            limit=str(event.cause_detail.get("limit", "unknown")),
        ).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields


class StructlogSink:
    """Pilar 2 — logs estruturados como projeção dos eventos.

    Correlacionados por `correlation_id`, de modo que a linha de log e o evento
    apontem para a mesma cadeia causal. O log nunca inspeciona estado interno de
    Engine: ele só reescreve o que o evento já declara.
    """

    def __init__(self, logger: structlog.stdlib.BoundLogger | None = None) -> None:
        self._log = logger or structlog.get_logger("ecosfera.engines")

    def record_metrics(self, sample: PerfSample) -> None:
        self._log.debug(
            "engine_tick",
            engine=sample.engine_id,
            tick=sample.tick,
            era=sample.era,
            duration_s=round(sample.duration_s, 6),
            events=sample.events_emitted,
        )

    def emit(self, event: DomainEvent) -> None:
        self._log.info(
            "domain_event",
            event_type=event.event_type,
            engine=event.engine_id,
            tick=event.occurred_at.tick,
            era=event.occurred_at.era,
            cause_code=str(event.cause_code),
            correlation_id=event.correlation_id,
        )

    def log(self, message: str, /, **fields: object) -> None:
        self._log.info(message, **fields)


@dataclass(slots=True)
class CompositeSink:
    """Encaminha o mesmo sinal a vários sinks, na ordem declarada."""

    sinks: Sequence[ObservabilitySink]

    def record_metrics(self, sample: PerfSample) -> None:
        for sink in self.sinks:
            sink.record_metrics(sample)

    def emit(self, event: DomainEvent) -> None:
        for sink in self.sinks:
            sink.emit(event)

    def log(self, message: str, /, **fields: object) -> None:
        for sink in self.sinks:
            sink.log(message, **fields)


# ── Pilar 4 — traces ────────────────────────────────────────────────────────
# Gancho de OpenTelemetry atrás de flag, no-op por padrão. Trazer o SDK agora
# custaria dependência pesada para um span que ninguém coleta ainda; o que
# precisa existir desde já é o PONTO DE ENGATE, para que ligar tracing no M5 não
# exija tocar no Planet Engine. A cadeia causal, enquanto isso, já é
# reconstruível por `correlation_id`/`causation_id` no Event Store.

_TRACING_ENABLED = False


def configure_tracing(*, enabled: bool) -> None:
    """Liga/desliga os spans da moldura (default: desligado)."""
    global _TRACING_ENABLED
    _TRACING_ENABLED = enabled


def tracing_enabled() -> bool:
    return _TRACING_ENABLED


@contextmanager
def span(name: str, **attributes: object) -> Iterator[None]:
    """Span por Engine/tick. No-op enquanto o tracing estiver desligado."""
    if not _TRACING_ENABLED:
        yield
        return
    logger = structlog.get_logger("ecosfera.trace")
    logger.debug("span_start", span=name, **attributes)
    try:
        yield
    finally:
        logger.debug("span_end", span=name, **attributes)
