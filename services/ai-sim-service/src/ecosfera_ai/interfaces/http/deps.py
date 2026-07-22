"""Composition root: injeta adaptadores nas portas. Único lugar que conhece concretos."""
from __future__ import annotations

from functools import lru_cache

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.telemetry.ingest_event import IngestTelemetryUseCase
from ecosfera_ai.config.settings import get_settings
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.infrastructure.messaging.null_event_bus import NullEventBus
from ecosfera_ai.infrastructure.persistence.inmemory_telemetry_repo import (
    InMemoryTelemetryRepository,
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
