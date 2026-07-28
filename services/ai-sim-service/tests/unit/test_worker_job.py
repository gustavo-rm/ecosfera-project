"""Corpo do job do worker ARQ (ADR 0007), testável sem Redis nem Postgres.

O worker é um segundo composition root, mas o JOB em si só orquestra o caso de
uso — e é isso que se verifica aqui, com um duplo no lugar do `EvolveBiologyUseCase`.
"""

from __future__ import annotations

from typing import Any

import pytest

from ecosfera_ai.application.simulation.evolve_biology import BiologySummary
from ecosfera_ai.infrastructure.jobs.worker import run_evolution


class _StubUseCase:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple[str, int]] = []
        self._fail = fail

    async def execute(self, planet_id: str, era: int) -> BiologySummary:
        self.calls.append((planet_id, era))
        if self._fail:
            raise RuntimeError("banco indisponível")
        return BiologySummary(era=era, speciated=["s1"], extinct=[], living=1, generations=4)


@pytest.mark.asyncio
async def test_job_delegates_to_the_use_case_and_returns_a_serializable_summary() -> None:
    stub = _StubUseCase()
    ctx: dict[str, Any] = {"use_case": stub}

    result = await run_evolution(ctx, {"planet_id": "gaia", "era": 3})

    assert stub.calls == [("gaia", 3)]
    # O resultado precisa ser serializável: ele atravessa o Redis.
    assert result == {
        "era": 3,
        "speciated": ["s1"],
        "extinct": [],
        "living": 1,
        "generations": 4,
    }


@pytest.mark.asyncio
async def test_job_coerces_the_payload_types() -> None:
    """O payload volta do Redis como JSON: ids e eras precisam ser normalizados."""
    stub = _StubUseCase()
    await run_evolution({"use_case": stub}, {"planet_id": 42, "era": "5"})
    assert stub.calls == [("42", 5)]


@pytest.mark.asyncio
async def test_job_propagates_failures_for_arq_to_retry() -> None:
    stub = _StubUseCase(fail=True)
    with pytest.raises(RuntimeError, match="banco indisponível"):
        await run_evolution({"use_case": stub}, {"planet_id": "p", "era": 1})
