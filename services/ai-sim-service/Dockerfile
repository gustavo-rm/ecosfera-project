# Imagem enxuta com uv (build reprodutível a partir do uv.lock)
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

FROM base AS deps
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

FROM base AS runtime
COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY src ./src
COPY configs ./configs
COPY prompts ./prompts
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://localhost:8000/ai/api/v1/health').status_code==200 else 1)"
CMD ["uvicorn", "ecosfera_ai.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
