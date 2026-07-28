"""Porta de saída para trabalho assíncrono pesado (Dossiê §4, ADR 0007).

A evolução (AG) é o primeiro processo do serviço caro o bastante para não caber
no ciclo request/response de um avanço de era com muitas espécies. Em vez de
acoplar o caso de uso a Redis/ARQ, ele fala com esta porta.

Dois adaptadores a implementam:
  - `InlineJobQueue` — executa na hora, no mesmo processo (dev e testes);
  - `ArqJobQueue` — enfileira no Redis para um worker (staging/produção).

Com o inline, todo o fluxo é testável ponta a ponta SEM infraestrutura.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class JobStatus(StrEnum):
    """Ciclo de vida de um job assíncrono."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class JobRef:
    """Referência opaca devolvida ao cliente para consultar o andamento."""

    job_id: str
    job_name: str


@dataclass(frozen=True, slots=True)
class JobResult:
    """Estado corrente de um job e, quando concluído, sua carga de resultado."""

    job_id: str
    job_name: str
    status: JobStatus
    result: dict[str, Any] | None = None
    error: str | None = None


class JobQueue(Protocol):
    async def enqueue(self, job_name: str, payload: dict[str, Any]) -> JobRef: ...
    async def get_status(self, job_id: str) -> JobResult | None: ...
