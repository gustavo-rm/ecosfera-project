"""Fila SÍNCRONA: executa o job na hora, no mesmo processo (ADR 0007).

É o adaptador padrão em dev e testes. Executar inline mantém o fluxo inteiro
— avançar era, evoluir, persistir códex — verificável **sem Redis, sem worker e
sem Docker**, o que é decisivo para a suíte determinística deste serviço.

O handler é registrado pelo composition root, então este adaptador não conhece
nada de biologia: só sabe despachar por nome.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from ecosfera_ai.application.ports.job_queue import JobRef, JobResult, JobStatus

JobHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class InlineJobQueue:
    """Adaptador in-process da porta `JobQueue`."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}
        self._results: dict[str, JobResult] = {}

    def register(self, job_name: str, handler: JobHandler) -> None:
        """Registra quem executa um job (chamado no composition root)."""
        self._handlers[job_name] = handler

    async def enqueue(self, job_name: str, payload: dict[str, Any]) -> JobRef:
        job_id = uuid4().hex
        ref = JobRef(job_id=job_id, job_name=job_name)
        handler = self._handlers.get(job_name)
        if handler is None:
            self._results[job_id] = JobResult(
                job_id=job_id,
                job_name=job_name,
                status=JobStatus.FAILED,
                error=f"nenhum handler registrado para '{job_name}'",
            )
            return ref
        try:
            result = await handler(payload)
        except Exception as exc:
            self._results[job_id] = JobResult(
                job_id=job_id, job_name=job_name, status=JobStatus.FAILED, error=str(exc)
            )
            return ref
        self._results[job_id] = JobResult(
            job_id=job_id, job_name=job_name, status=JobStatus.COMPLETE, result=result
        )
        return ref

    async def get_status(self, job_id: str) -> JobResult | None:
        return self._results.get(job_id)
