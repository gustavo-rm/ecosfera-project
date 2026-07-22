from __future__ import annotations

import pytest

from ecosfera_ai.application.telemetry.ingest_event import (
    ConsentRequiredError,
    IngestTelemetryUseCase,
)
from ecosfera_ai.domain.telemetry.models import TelemetryEvent
from ecosfera_ai.infrastructure.messaging.null_event_bus import NullEventBus
from ecosfera_ai.infrastructure.persistence.inmemory_telemetry_repo import (
    InMemoryTelemetryRepository,
)


@pytest.mark.asyncio
async def test_event_without_consent_is_blocked() -> None:
    uc = IngestTelemetryUseCase(InMemoryTelemetryRepository(), NullEventBus())
    ev = TelemetryEvent("s1", "p1", "intervene", {"tradeoff": "co2"}, consent=False)
    with pytest.raises(ConsentRequiredError):
        await uc.execute(ev)


@pytest.mark.asyncio
async def test_intervention_with_tradeoff_derives_evidence() -> None:
    repo = InMemoryTelemetryRepository()
    uc = IngestTelemetryUseCase(repo, NullEventBus())
    ev = TelemetryEvent("s1", "p1", "intervene", {"tradeoff": "co2"}, consent=True)
    evidence = await uc.execute(ev)
    assert evidence is not None
    assert evidence.competency_hint == "systems_thinking"
    assert await repo.count_events() == 1
