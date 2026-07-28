"""Fila assíncrona real: ARQ sobre Redis (ADR 0007).

Sobe um Redis efêmero com Testcontainers e exercita o ciclo completo da porta
`JobQueue`: enfileirar -> worker executar -> status completar com o resultado.
Sem daemon Docker o módulo é PULADO — o caminho inline já cobre a lógica de
negócio, e a suíte não pode depender de infraestrutura para ficar verde.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

REDIS_IMAGE = "redis:7-alpine"


def _docker_available() -> bool:
    try:
        import docker  # type: ignore[import-untyped]

        docker.from_env().ping()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _docker_available(), reason="daemon Docker indisponível para Testcontainers"
)


@pytest.fixture(scope="module")
def redis_dsn() -> Iterator[str]:
    from testcontainers.redis import RedisContainer

    with RedisContainer(REDIS_IMAGE) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(container.port)
        yield f"redis://{host}:{port}"


@pytest.mark.asyncio
async def test_enqueue_and_worker_complete_the_job(redis_dsn: str) -> None:
    from arq import Worker

    from ecosfera_ai.application.ports.job_queue import JobStatus
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import ArqJobQueue, redis_settings

    executed: list[dict[str, Any]] = []

    async def run_evolution(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        """Substitui o corpo real: aqui o que se testa é o TRANSPORTE do job."""
        executed.append(payload)
        return {
            "era": payload["era"],
            "speciated": ["s1"],
            "extinct": [],
            "living": 1,
            "generations": 3,
        }

    queue = ArqJobQueue(redis_dsn)
    ref = await queue.enqueue("run_evolution", {"planet_id": "arq-planet", "era": 2})
    assert ref.job_name == "run_evolution"

    # Estado antes de o worker rodar: pendente, ainda sem resultado.
    pending = await queue.get_status(ref.job_id)
    assert pending is not None
    assert pending.status in (JobStatus.PENDING, JobStatus.RUNNING)

    worker = Worker(
        functions=[run_evolution],
        redis_settings=redis_settings(redis_dsn),
        burst=True,  # processa a fila e encerra
        poll_delay=0.01,
    )
    await worker.main()
    await worker.close()

    assert executed == [{"planet_id": "arq-planet", "era": 2}]

    done = await queue.get_status(ref.job_id)
    assert done is not None
    assert done.status is JobStatus.COMPLETE
    assert done.result is not None
    assert done.result["era"] == 2
    assert done.result["speciated"] == ["s1"]

    await queue.close()


@pytest.mark.asyncio
async def test_unknown_job_has_no_status(redis_dsn: str) -> None:
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import ArqJobQueue

    queue = ArqJobQueue(redis_dsn)
    assert await queue.get_status("job-que-nunca-existiu") is None
    await queue.close()
