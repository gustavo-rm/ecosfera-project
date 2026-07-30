"""Composition root: injeta adaptadores nas portas. Único lugar que conhece concretos."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.ports.job_queue import JobQueue
from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.advance_era import JOB_RUN_EVOLUTION, AdvanceEraUseCase
from ecosfera_ai.application.simulation.create_planet import CreatePlanetUseCase
from ecosfera_ai.application.simulation.evolve_biology import EvolveBiologyUseCase
from ecosfera_ai.application.simulation.replay_state import ReplayStateUseCase
from ecosfera_ai.application.simulation.run_tick import RunTickUseCase
from ecosfera_ai.application.telemetry.ingest_event import IngestTelemetryUseCase
from ecosfera_ai.config.settings import get_settings
from ecosfera_ai.core.observability import biology_jobs
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.engines.legacy.orchestrator import (
    FrameworkTickOrchestrator,
    build_planet_engine,
)
from ecosfera_ai.infrastructure.jobs.inline_job_queue import InlineJobQueue
from ecosfera_ai.infrastructure.messaging.null_event_bus import NullEventBus
from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import (
    InMemoryPlanetRepository,
)
from ecosfera_ai.infrastructure.persistence.inmemory_telemetry_repo import (
    InMemoryTelemetryRepository,
)
from ecosfera_ai.shared_kernel.observability import (
    CompositeSink,
    InMemoryEventStore,
    ObservabilitySink,
    PrometheusMetricsSink,
    StructlogSink,
    configure_tracing,
)
from ecosfera_ai.simulation_engine.biology.engine import BiologyEngine
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine
from ecosfera_ai.simulation_engine.params import (
    SimulationParams,
    build_orchestrator,
    load_params,
)
from ecosfera_ai.simulation_engine.subsystems.life import LifeSubsystem
from ecosfera_ai.simulation_engine.ticker import Ticker

# Singletons de processo (substituíveis por adaptadores reais via settings/flags)
_repo = InMemoryTelemetryRepository()
_bus = NullEventBus()


@lru_cache
def get_explain_use_case() -> ExplainCausalUseCase:
    settings = get_settings()
    engine = build_engine(settings.causal_rules_path)
    return ExplainCausalUseCase(engine)


def get_ingest_use_case() -> IngestTelemetryUseCase:
    return IngestTelemetryUseCase(_repo, _bus)


def get_repo() -> InMemoryTelemetryRepository:
    return _repo


@lru_cache
def get_simulation_params() -> SimulationParams:
    return load_params(get_settings().simulation_params_path)


@lru_cache
def get_event_store() -> InMemoryEventStore:
    """Event Store do processo — fonte de verdade do Canal B até o M5.

    Trocá-lo por um adaptador Postgres não toca em nenhum Engine: o Planet
    Engine só conhece a porta `ObservabilitySink` (ADR-ARCH-0002).
    """
    return InMemoryEventStore()


@lru_cache
def get_observability_sink() -> ObservabilitySink:
    """Compõe os pilares: Event Store + métricas Prometheus + logs estruturados."""
    configure_tracing(enabled=get_settings().tracing_enabled)
    return CompositeSink([get_event_store(), PrometheusMetricsSink(), StructlogSink()])


@lru_cache
def get_orchestrator() -> Ticker:
    """Escolhe entre o tick direto e o tick pela moldura de Engines (M0).

    As duas rotas produzem o MESMO estado para a mesma semente — o que muda é
    quem orquestra e se o Canal B é alimentado. A flag existe para rollback
    imediato enquanto os Engines científicos não estabilizarem (ADR 0008).
    """
    params = get_simulation_params()
    legacy = build_orchestrator(params)
    if not get_settings().engines_framework:
        return legacy
    planet = build_planet_engine(
        legacy,
        budget=params.engine_budget,
        sink=get_observability_sink(),
    )
    return FrameworkTickOrchestrator(legacy, planet)


@lru_cache
def get_planet_repo() -> PlanetRepository:
    """Seleciona o adaptador da porta conforme a feature flag de persistência.

    O import do adaptador Postgres é PREGUIÇOSO: em modo `inmemory` o serviço
    sobe sem o extra `infra` (SQLAlchemy/asyncpg) instalado.
    """
    settings = get_settings()
    if settings.persistence_backend == "postgres":
        from ecosfera_ai.infrastructure.persistence.postgres_planet_repo import (
            PostgresPlanetRepository,
            create_engine,
        )

        return PostgresPlanetRepository(create_engine(settings.database_url))
    return InMemoryPlanetRepository()


def get_create_planet_use_case() -> CreatePlanetUseCase:
    return CreatePlanetUseCase(get_planet_repo(), get_simulation_params())


def get_run_tick_use_case() -> RunTickUseCase:
    return RunTickUseCase(get_planet_repo(), get_orchestrator(), get_explain_use_case())


@lru_cache
def get_life_subsystem() -> LifeSubsystem:
    """Subsistema determinístico de vida — publica a capacidade de suporte."""
    return LifeSubsystem(get_simulation_params().life)


@lru_cache
def get_biology_engine() -> BiologyEngine:
    params = get_simulation_params()
    evolution = EvolutionEngine(params.evolution, params.fitness)
    return BiologyEngine(evolution, params.ecology)


def get_evolve_biology_use_case() -> EvolveBiologyUseCase:
    return EvolveBiologyUseCase(get_planet_repo(), get_biology_engine(), get_life_subsystem())


@lru_cache
def get_job_queue() -> JobQueue:
    """Seleciona a fila conforme a flag; o handler do job é registrado no inline.

    O import do ARQ é PREGUIÇOSO: em modo `inline` o serviço sobe sem o extra
    `infra` instalado (ADR 0007).
    """
    settings = get_settings()
    if settings.job_backend == "arq":
        from ecosfera_ai.infrastructure.jobs.arq_job_queue import ArqJobQueue

        return ArqJobQueue(settings.redis_dsn)

    queue = InlineJobQueue()

    async def _run_evolution(payload: dict[str, Any]) -> dict[str, Any]:
        use_case = get_evolve_biology_use_case()
        summary = await use_case.execute(str(payload["planet_id"]), int(payload["era"]))
        biology_jobs.labels(backend="inline", outcome="complete").inc()
        return dict(summary.to_dict())

    queue.register(JOB_RUN_EVOLUTION, _run_evolution)
    return queue


def get_advance_era_use_case() -> AdvanceEraUseCase:
    params = get_simulation_params()
    settings = get_settings()
    return AdvanceEraUseCase(
        get_planet_repo(),
        get_orchestrator(),
        get_explain_use_case(),
        params.timeline.era_length,
        get_job_queue(),
        biology_enabled=settings.biology_enabled,
        # Só a fila inline resolve na hora; com ARQ a rota responde 202.
        resolves_inline=settings.job_backend != "arq",
    )


def get_replay_state_use_case() -> ReplayStateUseCase:
    return ReplayStateUseCase(
        get_planet_repo(),
        get_orchestrator(),
        get_evolve_biology_use_case() if get_settings().biology_enabled else None,
    )
