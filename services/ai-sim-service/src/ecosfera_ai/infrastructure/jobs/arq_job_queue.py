"""Fila assíncrona sobre Redis com ARQ (staging/produção — ADR 0007).

Implementa a mesma porta `JobQueue` do adaptador inline; trocar de um para o
outro é uma variável de ambiente, e nenhuma camada acima percebe.

O import do driver é PREGUIÇOSO (dentro dos métodos): o serviço sobe em modo
`inline` sem o extra `infra` instalado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ecosfera_ai.application.ports.job_queue import JobRef, JobResult, JobStatus

if TYPE_CHECKING:  # pragma: no cover - só para tipagem
    from arq.connections import ArqRedis, RedisSettings

# Tradução dos estados do ARQ para o vocabulário da porta.
_ARQ_STATUS = {
    "deferred": JobStatus.PENDING,
    "queued": JobStatus.PENDING,
    "in_progress": JobStatus.RUNNING,
    "complete": JobStatus.COMPLETE,
    "not_found": JobStatus.UNKNOWN,
}


def redis_settings(dsn: str) -> RedisSettings:
    """Constrói as configurações de Redis do ARQ a partir de uma DSN."""
    from arq.connections import RedisSettings

    return RedisSettings.from_dsn(dsn)


class ArqJobQueue:
    """Adaptador ARQ/Redis da porta `JobQueue`."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: ArqRedis | None = None

    async def _connect(self) -> ArqRedis:
        if self._pool is None:
            from arq import create_pool

            self._pool = await create_pool(redis_settings(self._dsn))
        return self._pool

    async def enqueue(self, job_name: str, payload: dict[str, Any]) -> JobRef:
        pool = await self._connect()
        job = await pool.enqueue_job(job_name, payload)
        if job is None:  # o ARQ devolve None quando o job_id já existe na fila
            raise RuntimeError(f"não foi possível enfileirar '{job_name}'")
        return JobRef(job_id=job.job_id, job_name=job_name)

    async def get_status(self, job_id: str) -> JobResult | None:
        from arq.jobs import Job

        pool = await self._connect()
        job = Job(job_id, pool)
        status = _ARQ_STATUS.get(str(await job.status()), JobStatus.UNKNOWN)
        if status is JobStatus.UNKNOWN:
            return None

        result: dict[str, Any] | None = None
        error: str | None = None
        if status is JobStatus.COMPLETE:
            try:
                raw = await job.result(timeout=0)
                result = raw if isinstance(raw, dict) else {"value": raw}
            except Exception as exc:
                status = JobStatus.FAILED
                error = str(exc)
        return JobResult(job_id=job_id, job_name="", status=status, result=result, error=error)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
