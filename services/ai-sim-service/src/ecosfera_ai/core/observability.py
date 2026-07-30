"""Métricas Prometheus (técnicas e pedagógicas) desde o Inc 0 (Dossiê §16.2)."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

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

# ── Moldura de Engines (ADR-ARCH-0002, Spec §6) ──────────────────────────────
# Métricas POR ENGINE e POR TICK. São laterais: o Planet Engine as registra
# depois de compor o tick, e nenhuma decisão da simulação as consulta.
engine_tick_seconds = Histogram(
    "ecosfera_engine_tick_seconds",
    "Tempo de execução de um tick, por Engine",
    ["engine"],
)
engine_events_emitted = Counter(
    "ecosfera_engine_events_emitted_total", "Domain events emitidos, por Engine", ["engine"]
)
engine_entities_processed = Counter(
    "ecosfera_engine_entities_processed_total",
    "Entidades (células/coortes/organismos) processadas, por Engine",
    ["engine"],
)
engine_budget_exceeded = Counter(
    "ecosfera_engine_budget_exceeded_total",
    "Tetos de orçamento por tick estourados (gera DiagnosticEvent)",
    ["engine", "limit"],
)
