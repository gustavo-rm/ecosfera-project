"""Worker ARQ que executa o job pesado de evolução (ADR 0007).

Rodar:

    uv run arq ecosfera_ai.infrastructure.jobs.worker.WorkerSettings

O worker é um SEGUNDO composition root: monta suas próprias dependências a partir
das settings, porque roda em outro processo (sem FastAPI). O corpo do job, porém,
é exatamente o `EvolveBiologyUseCase` usado pela fila inline — o backend muda
ONDE o trabalho roda, nunca O QUE ele faz.
"""

from __future__ import annotations

from typing import Any

from ecosfera_ai.application.simulation.evolve_biology import EvolveBiologyUseCase
from ecosfera_ai.config.settings import get_settings
from ecosfera_ai.core.logging import configure_logging
from ecosfera_ai.core.observability import biology_jobs
from ecosfera_ai.simulation_engine.biology.engine import BiologyEngine
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine
from ecosfera_ai.simulation_engine.params import load_params


def build_use_case() -> EvolveBiologyUseCase:
    """Monta o caso de uso com persistência real (o worker não usa in-memory)."""
    from ecosfera_ai.infrastructure.persistence.postgres_planet_repo import (
        PostgresPlanetRepository,
        create_engine,
    )

    settings = get_settings()
    params = load_params(settings.simulation_params_path)
    repo = PostgresPlanetRepository(create_engine(settings.database_url))
    biology = BiologyEngine(EvolutionEngine(params.evolution, params.fitness), params.ecology)
    return EvolveBiologyUseCase(repo, biology)


async def run_evolution(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Job `run_evolution`: evolui a biologia de uma era já fechada."""
    use_case: EvolveBiologyUseCase = ctx["use_case"]
    try:
        summary = await use_case.execute(str(payload["planet_id"]), int(payload["era"]))
    except Exception:
        biology_jobs.labels(backend="arq", outcome="failed").inc()
        raise
    biology_jobs.labels(backend="arq", outcome="complete").inc()
    return dict(summary.to_dict())


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    ctx["use_case"] = build_use_case()


def _redis_settings() -> Any:
    from ecosfera_ai.infrastructure.jobs.arq_job_queue import redis_settings

    return redis_settings(get_settings().redis_dsn)


class WorkerSettings:
    """Configuração do worker consumida pela CLI do ARQ.

    `redis_settings` é lido como ATRIBUTO pelo ARQ (não como método), por isso é
    resolvido aqui na definição da classe. `from_dsn` apenas interpreta a URL —
    não abre conexão —, então importar este módulo continua barato.
    """

    functions = (run_evolution,)
    on_startup = startup
    redis_settings = _redis_settings()
