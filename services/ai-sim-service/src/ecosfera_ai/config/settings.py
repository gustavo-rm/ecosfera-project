"""Configuração via variáveis de ambiente (12-factor), com Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ECOSFERA_", env_file=".env", extra="ignore")

    app_name: str = "ecosfera-ai-sim-service"
    environment: str = Field(default="dev")  # dev | staging | prod
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)  # True em staging/prod

    api_v1_prefix: str = "/ai/api/v1"

    # Regras causais versionadas (dados, não código)
    causal_rules_path: Path = Field(default=Path("configs/causal_rules.yaml"))

    # Parâmetros do núcleo de simulação determinístico (dados, não código)
    simulation_params_path: Path = Field(default=Path("configs/simulation_params.yaml"))

    # Backend de persistência do planeta: 'inmemory' (default — testes e dev sem
    # banco) ou 'postgres' (staging/prod). Trocar a flag troca só o adaptador da
    # porta PlanetRepository; nenhuma camada acima muda (ADR 0001/0005).
    persistence_backend: str = Field(default="inmemory")  # inmemory | postgres

    # Camada emergente (Inc 3). `biology_enabled` é o gate da fronteira
    # determinístico × IA: desligá-la deixa o serviço 100% determinístico, sem
    # alterar nenhum campo físico do estado (ADR 0006).
    biology_enabled: bool = Field(default=True)
    # Fila do job pesado de evolução: inline (dev/testes) ou arq (Redis).
    job_backend: str = Field(default="inline")  # inline | arq
    redis_dsn: str = Field(default="redis://localhost:6379")
    database_url: str = Field(
        default="postgresql+asyncpg://ecosfera:ecosfera@localhost:5432/ecosfera"
    )

    # Moldura de Engines (M0). Desligada por padrão: com ela ligada o tick roda
    # pelo Planet Engine em vez do TickOrchestrator direto. O resultado é o
    # mesmo bit a bit (ADR 0008) — a flag existe para permitir rollback imediato
    # enquanto os Engines científicos de M1/M2 não estabilizarem.
    engines_framework: bool = Field(default=False)
    # Spans de tracing da moldura (Pilar 4). No-op enquanto desligado.
    tracing_enabled: bool = Field(default=False)

    # Ativação de features por incremento (feature flags — TBD/rollout gradual)
    llm_enabled: bool = Field(default=False)  # ligado no Inc 6
    ollama_base_url: str = Field(default="http://localhost:11434")
    llm_model: str = Field(default="llama3")

    request_timeout_s: float = Field(default=3.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
