"""Ambiente de migrations do Alembic (ai-sim-service).

Lê a conexão de DATABASE_URL e serve a UMA árvore de migrations que cobre TODOS
os schemas Python do serviço (`rag` do RAG e `simulation` do núcleo
determinístico) — cada revisão cria o schema de que precisa, mantendo o serviço
isolado das migrations do platform-api (schema `platform`).

Suporta URL síncrona (psycopg) e assíncrona (asyncpg): o adaptador de produção
usa asyncpg, e rodar `alembic` com a mesma DATABASE_URL precisa funcionar sem
exigir um segundo driver instalado.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, engine_from_config, pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Migrations são escritas à mão (sem autogenerate) neste baseline.
target_metadata = None

# Schema onde vive a tabela de versão do Alembic. Mantido em `rag` por
# compatibilidade com bancos já migrados (débito de nomenclatura registrado no
# ADR 0005): o nome remete ao primeiro schema do serviço, não ao seu conteúdo.
VERSION_SCHEMA = "rag"


def _is_async_url(url: str) -> bool:
    return "+asyncpg" in url or "+aiosqlite" in url


def _configure(connection: Connection) -> None:
    """Garante o schema da tabela de versão e configura o contexto."""
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {VERSION_SCHEMA}"))
    connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=VERSION_SCHEMA,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        version_table_schema=VERSION_SCHEMA,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_async() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_run)
    await connectable.dispose()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or ""
    if _is_async_url(url):
        asyncio.run(run_migrations_async())
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _run(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
