.PHONY: help install run test cov lint fmt fmt-check type check ci test-all up down

# Gate rápido do dia a dia:  make check   (não depende de Docker)
# Gate completo (como o CI):  make ci      (sobe extra infra + roda integração e cobertura)

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Cria o venv e instala deps do núcleo (uv)
	uv sync

install-all:  ## Instala núcleo + extra infra + grupo dev (persistência real)
	uv sync --extra infra --group dev

run:  ## Sobe a API em modo dev (reload)
	uv run uvicorn ecosfera_ai.main:app --reload --app-dir src

test:  ## Roda a suíte de testes (integração é PULADA sem extra infra + Docker)
	uv run pytest

cov:  ## Testes com cobertura
	uv run pytest --cov=ecosfera_ai --cov-report=term-missing

lint:  ## Ruff (lint + ordem de imports)
	uv run ruff check src tests

fmt:  ## Ruff format (altera arquivos)
	uv run ruff format src tests

fmt-check:  ## Verifica formatação sem alterar arquivos (falha se algo estiver desformatado)
	uv run ruff format --check src tests

type:  ## Mypy strict
	uv run mypy

check: lint fmt-check type test  ## Gate local rápido (sem integração; não exige Docker)

test-all:  ## Sincroniza extra infra + roda a suíte COMPLETA com cobertura (exige Docker)
	uv sync --extra infra --group dev
	uv run pytest --cov=ecosfera_ai --cov-report=term-missing

ci: lint fmt-check type test-all  ## Gate completo, como o CI roda (inclui integração)

up:  ## Sobe infra local (compose)
	docker compose -f infra/compose/dev.yml --env-file infra/compose/.env up -d

down:  ## Derruba infra local
	docker compose -f infra/compose/dev.yml --env-file infra/compose/.env down