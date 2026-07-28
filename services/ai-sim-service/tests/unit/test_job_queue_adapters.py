"""Adaptadores da porta `JobQueue` (ADR 0007) — o que dá para testar sem Redis.

O caminho feliz do ARQ exige um Redis de verdade e vive nos testes de integração
(pulados sem Docker). Aqui ficam as partes puras: despacho e tratamento de erro
da fila inline, e a tradução de estados do ARQ — justamente a lógica que quebra
silenciosamente se alguém mexer no adaptador.
"""

from __future__ import annotations

from typing import Any

import pytest

from ecosfera_ai.application.ports.job_queue import JobRef, JobStatus
from ecosfera_ai.infrastructure.jobs.inline_job_queue import InlineJobQueue


@pytest.mark.asyncio
async def test_inline_queue_runs_the_handler_and_stores_the_result() -> None:
    queue = InlineJobQueue()

    async def handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {"echo": payload["value"]}

    queue.register("job", handler)
    ref = await queue.enqueue("job", {"value": 7})

    result = await queue.get_status(ref.job_id)
    assert result is not None
    assert result.status is JobStatus.COMPLETE
    assert result.result == {"echo": 7}
    assert result.error is None


@pytest.mark.asyncio
async def test_inline_queue_reports_a_missing_handler_instead_of_crashing() -> None:
    queue = InlineJobQueue()
    ref = await queue.enqueue("inexistente", {})

    result = await queue.get_status(ref.job_id)
    assert result is not None
    assert result.status is JobStatus.FAILED
    assert "nenhum handler" in str(result.error)


@pytest.mark.asyncio
async def test_inline_queue_turns_handler_errors_into_job_state() -> None:
    """Um job que falha não pode derrubar o avanço de era: vira estado do job."""
    queue = InlineJobQueue()

    async def broken(payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("evolução falhou")

    queue.register("job", broken)
    ref = await queue.enqueue("job", {})

    result = await queue.get_status(ref.job_id)
    assert result is not None
    assert result.status is JobStatus.FAILED
    assert "evolução falhou" in str(result.error)


@pytest.mark.asyncio
async def test_unknown_job_id_has_no_status() -> None:
    assert await InlineJobQueue().get_status("nao-existe") is None


@pytest.mark.asyncio
async def test_each_enqueue_gets_its_own_reference() -> None:
    queue = InlineJobQueue()

    async def handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    queue.register("job", handler)
    first = await queue.enqueue("job", {})
    second = await queue.enqueue("job", {})
    assert first.job_id != second.job_id
    assert isinstance(first, JobRef)


def test_arq_status_translation_covers_the_lifecycle() -> None:
    pytest.importorskip("arq", reason="extra `infra` não instalado")
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import _ARQ_STATUS

    assert _ARQ_STATUS["queued"] is JobStatus.PENDING
    assert _ARQ_STATUS["deferred"] is JobStatus.PENDING
    assert _ARQ_STATUS["in_progress"] is JobStatus.RUNNING
    assert _ARQ_STATUS["complete"] is JobStatus.COMPLETE
    assert _ARQ_STATUS["not_found"] is JobStatus.UNKNOWN


def test_redis_settings_parses_the_dsn_without_connecting() -> None:
    pytest.importorskip("arq", reason="extra `infra` não instalado")
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import redis_settings

    settings = redis_settings("redis://example.test:6390")
    assert settings.host == "example.test"
    assert settings.port == 6390
