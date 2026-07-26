"""Composition root: injeta adaptadores nas portas. Único lugar que conhece concretos."""
from __future__ import annotations

from functools import lru_cache

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.advance_era import AdvanceEraUseCase
from ecosfera_ai.application.simulation.create_planet import CreatePlanetUseCase
from ecosfera_ai.application.simulation.replay_state import ReplayStateUseCase
from ecosfera_ai.application.simulation.run_tick import RunTickUseCase
from ecosfera_ai.application.telemetry.ingest_event import IngestTelemetryUseCase
from ecosfera_ai.config.settings import get_settings
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.infrastructure.messaging.null_event_bus import NullEventBus
from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import (
    InMemoryPlanetRepository,
)
from ecosfera_ai.infrastructure.persistence.inmemory_telemetry_repo import (
    InMemoryTelemetryRepository,
)
from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator
from ecosfera_ai.simulation_engine.params import (
    SimulationParams,
    build_orchestrator,
    load_params,
)

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
def get_orchestrator() -> TickOrchestrator:
    return build_orchestrator(get_simulation_params())


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


def get_advance_era_use_case() -> AdvanceEraUseCase:
    params = get_simulation_params()
    return AdvanceEraUseCase(
        get_planet_repo(),
        get_orchestrator(),
        get_explain_use_case(),
        params.timeline.era_length,
    )


def get_replay_state_use_case() -> ReplayStateUseCase:
    return ReplayStateUseCase(get_planet_repo(), get_orchestrator())
