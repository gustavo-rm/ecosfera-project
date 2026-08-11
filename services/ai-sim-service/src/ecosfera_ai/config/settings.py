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

    # Tradução de Domain Events em observações para o motor de regras (ADR 0011)
    event_observations_path: Path = Field(default=Path("configs/event_observations.yaml"))

    # Templates de explicação do M6.1 — a prosa que chega ao aluno, versionada
    # como dado para que a revisão pedagógica não exija tocar em código.
    explanation_templates_path: Path = Field(default=Path("configs/explanation_templates.yaml"))

    # Backend de persistência do planeta: 'inmemory' (default — testes e dev sem
    # banco) ou 'postgres' (staging/prod). Trocar a flag troca só o adaptador da
    # porta PlanetRepository; nenhuma camada acima muda (ADR 0001/0005).
    persistence_backend: str = Field(default="inmemory")  # inmemory | postgres

    # Camada emergente (Inc 3). `biology_enabled` é o gate da fronteira
    # determinístico × IA: desligá-la deixa o serviço 100% determinístico, sem
    # alterar nenhum campo físico do estado (ADR 0006).
    #
    # DESLIGADA POR PADRÃO desde o M3 (ADR 0017, tempo 1 de 4). O que esta flag
    # liga hoje é o caminho de biologia POR ERA (`simulation_engine/biology/`),
    # que roda um AG do DEAP com `selTournament` sobre uma função de aptidão
    # ESCALAR. Isso viola a DEC-01 ("não existe função de aptidão em nenhum
    # ponto") e o ADR-ARCH-0001, e a auditoria de conformidade
    # (`docs/evolution-engine/00-auditoria-conformidade.md`) desaconselhou
    # explicitamente subir com ela ligada:
    #
    #   "isso publica como 'emergente' um comportamento que a especificação
    #    classifica como cientificamente inválido, e o tutor de IA passaria a
    #    explicar ao estudante uma dinâmica que não é o que o texto diz ser."
    #
    # Desligá-la é CONTENÇÃO, não arquitetura: não decide o destino do caminho
    # legado — apenas impede que ciência sabidamente errada rode sem alguém a ter
    # pedido. A biologia emergente do Evolution/Ecology Engine NÃO depende desta
    # flag: ela roda no tick, sempre, e é a única biologia do world-state.
    #
    # Volta a `True` no tempo 4, quando o único caminho existente for o
    # emergente — aí a flag liga biologia, e só há a biologia certa para ligar.
    biology_enabled: bool = Field(default=False)
    # Fila do job pesado de evolução: inline (dev/testes) ou arq (Redis).
    job_backend: str = Field(default="inline")  # inline | arq
    redis_dsn: str = Field(default="redis://localhost:6379")
    database_url: str = Field(
        default="postgresql+asyncpg://ecosfera:ecosfera@localhost:5432/ecosfera"
    )

    # `ECOSFERA_ENGINES_FRAMEWORK` foi REMOVIDA no M2 (ADR 0014). A moldura de
    # Engines é o único caminho de simulação: não há mais um segundo motor para
    # a flag escolher. Definir a variável de ambiente hoje não faz nada.
    #
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
