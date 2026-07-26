"""Métricas Prometheus (técnicas e pedagógicas) desde o Inc 0 (Dossiê §16.2)."""
from __future__ import annotations

from prometheus_client import Counter

feedback_requests = Counter(
    "ecosfera_feedback_requests_total", "Explicações causais geradas", ["source"]
)
telemetry_events = Counter(
    "ecosfera_telemetry_events_total", "Eventos de telemetria ingeridos", ["processed"]
)
simulation_ticks = Counter(
    "ecosfera_simulation_ticks_total", "Ticks de simulação determinística executados"
)
simulation_eras = Counter(
    "ecosfera_simulation_eras_total", "Eras avançadas (checkpoints append-only gravados)"
)
simulation_replays = Counter(
    "ecosfera_simulation_replays_total",
    "Reconstruções de era executadas; 'matched' indica se bateram com o checkpoint",
    ["matched"],
)
