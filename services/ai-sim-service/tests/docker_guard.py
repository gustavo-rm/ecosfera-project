"""Guarda de disponibilidade de Docker — e a trava que impede o skip virar esconderijo.

Os testes de persistência usam Testcontainers. Sem daemon Docker eles pulam, o
que é razoável numa máquina de desenvolvimento — e perigoso num pipeline: um
runner sem Docker silenciaria a suíte inteira de persistência e a árvore
continuaria verde, atestando uma verificação que não aconteceu.

`ECOSFERA_REQUIRE_POSTGRES=1` (ligada no CI) inverte o padrão: a ausência de
Docker passa a ser FALHA, não skip. O pulo continua disponível onde é legítimo, e
deixa de estar disponível onde seria mentira.
"""

from __future__ import annotations

import os

import pytest

# Imagem COM pgvector: a migration 0001 (baseline do schema `rag`) faz
# `CREATE EXTENSION vector`, que não existe no postgres oficial nem no alpine.
#
# Vive aqui, e não em cada teste, porque já divergiu uma vez: o arquivo do Event
# Store nasceu com `postgres:16-alpine` e só o CI viu — localmente ele pulava por
# falta de Docker, então a suíte ficava verde apontando para uma imagem em que a
# primeira migration nem aplica. Constante compartilhada para que o próximo
# arquivo de persistência herde a escolha em vez de repeti-la errado.
POSTGRES_IMAGE = "pgvector/pgvector:pg16"


def run_migrations(async_url: str) -> None:
    """Aplica as migrations via API do Alembic (equivale a `alembic upgrade head`)."""
    from alembic import command
    from alembic.config import Config

    os.environ["DATABASE_URL"] = async_url
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    command.upgrade(config, "head")


def docker_available() -> bool:
    try:
        import docker

        docker.from_env().ping()
    except Exception:
        return False
    return True


def postgres_required() -> bool:
    """O ambiente EXIGE persistência de verdade? (CI liga; dev não.)"""
    return os.environ.get("ECOSFERA_REQUIRE_POSTGRES", "").strip().lower() in {"1", "true", "yes"}


def requires_postgres() -> pytest.MarkDecorator:
    """Marca para testes que precisam de Postgres real.

    Pula onde é honesto pular; falha onde pular seria esconder.
    """
    if docker_available():
        return pytest.mark.skipif(False, reason="")
    if postgres_required():
        return pytest.mark.fail_without_docker
    return pytest.mark.skipif(True, reason="daemon Docker indisponível para Testcontainers")
