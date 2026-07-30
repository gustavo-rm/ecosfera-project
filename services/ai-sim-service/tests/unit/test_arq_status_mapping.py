"""Contrato entre os estados do ARQ e o vocabulário da porta `JobQueue`.

Este arquivo existe por causa de um defeito concreto: `get_status` consultava o
mapa de tradução com `str(job.status())`. Como `arq.jobs.JobStatus` é um
`class JobStatus(str, Enum)` — e não um `StrEnum` —, `str()` devolve
"JobStatus.queued" em vez de "queued". Resultado: nenhuma chave batia, e o
adaptador respondia `None` para QUALQUER job, em qualquer estado.

O defeito sobreviveu porque a única cobertura do adaptador ARQ dependia de
Docker (Testcontainers) e nunca havia rodado. Estes testes verificam o mesmo
contrato **sem infraestrutura**: bastam o enum do ARQ e o mapa. Assim a
regressão aparece no `make check` de qualquer máquina.
"""

from __future__ import annotations

import pytest

from ecosfera_ai.application.ports.job_queue import JobStatus

arq_jobs = pytest.importorskip("arq.jobs", reason="extra `infra` não instalado")


def test_every_arq_state_is_translated() -> None:
    """Um estado novo do ARQ não pode passar despercebido para UNKNOWN."""
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import _ARQ_STATUS

    arq_values = {member.value for member in arq_jobs.JobStatus}
    assert arq_values <= set(_ARQ_STATUS), (
        f"estados do ARQ sem tradução: {sorted(arq_values - set(_ARQ_STATUS))}"
    )


def test_the_map_is_keyed_by_value_not_by_str() -> None:
    """Fixa exatamente o erro cometido: `str(enum)` não é a chave."""
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import _ARQ_STATUS

    queued = arq_jobs.JobStatus.queued
    assert str(queued) not in _ARQ_STATUS, (
        "se str(enum) virar chave válida, o teste abaixo deixa de proteger nada"
    )
    assert _ARQ_STATUS[queued.value] is JobStatus.PENDING


@pytest.mark.parametrize(
    ("arq_state", "expected"),
    [
        ("deferred", JobStatus.PENDING),
        ("queued", JobStatus.PENDING),
        ("in_progress", JobStatus.RUNNING),
        ("complete", JobStatus.COMPLETE),
        ("not_found", JobStatus.UNKNOWN),
    ],
)
def test_each_state_maps_to_the_expected_port_status(arq_state: str, expected: JobStatus) -> None:
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import _ARQ_STATUS

    assert _ARQ_STATUS[arq_state] is expected


def test_arq_registers_functions_by_qualname() -> None:
    """Por que o worker do serviço declara `run_evolution` no nível do módulo.

    `arq.worker.func` usa `coroutine.__qualname__` quando nenhum `name` é dado.
    Uma função ANINHADA seria registrada como
    "test_x.<locals>.run_evolution" e o worker jamais acharia o job enfileirado
    como "run_evolution" — falha que só aparece com um Redis de verdade.
    """
    from arq.worker import func

    from ecosfera_ai.application.simulation.advance_era import JOB_RUN_EVOLUTION
    from ecosfera_ai.infrastructure.jobs.worker import run_evolution

    assert func(run_evolution).name == JOB_RUN_EVOLUTION

    def _outer() -> object:
        async def run_evolution(ctx: dict[str, object], payload: dict[str, object]) -> None: ...

        return run_evolution

    nested = func(_outer())  # type: ignore[arg-type]
    assert nested.name != JOB_RUN_EVOLUTION
    assert "<locals>" in nested.name
