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
biology_generations = Counter(
    "ecosfera_biology_generations_total", "Gerações evoluídas pelo AG (DEAP)"
)
biology_speciations = Counter(
    "ecosfera_biology_speciations_total", "Espécies surgidas por especiação"
)
biology_extinctions = Counter(
    "ecosfera_biology_extinctions_total", "Espécies extintas por pressão ambiental"
)
biology_jobs = Counter(
    "ecosfera_biology_jobs_total", "Jobs de evolução executados", ["backend", "outcome"]
)
simulation_replays = Counter(
    "ecosfera_simulation_replays_total",
    "Reconstruções de era executadas; 'matched' indica se bateram com o checkpoint",
    ["matched"],
)
