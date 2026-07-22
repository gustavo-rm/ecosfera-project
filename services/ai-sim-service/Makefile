.PHONY: help install run test lint type cov fmt check up down
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
install:  ## Cria o venv e instala deps (uv)
	uv sync
run:      ## Sobe a API em modo dev (reload)
	uv run uvicorn ecosfera_ai.main:app --reload --app-dir src
test:     ## Roda a suíte de testes
	uv run pytest
cov:      ## Testes com cobertura
	uv run pytest --cov=ecosfera_ai --cov-report=term-missing
lint:     ## Ruff (lint + import order)
	uv run ruff check src tests
fmt:      ## Ruff format
	uv run ruff format src tests
type:     ## Mypy strict
	uv run mypy
check: lint type test  ## Gate local completo (espelha o CI)
up:       ## Sobe infra local (compose)
	docker compose up -d --build
down:     ## Derruba infra local
	docker compose down
