"""Métricas Prometheus (técnicas e pedagógicas) desde o Inc 0 (Dossiê §16.2)."""
from __future__ import annotations

from prometheus_client import Counter

feedback_requests = Counter(
    "ecosfera_feedback_requests_total", "Explicações causais geradas", ["source"]
)
telemetry_events = Counter(
    "ecosfera_telemetry_events_total", "Eventos de telemetria ingeridos", ["processed"]
)
