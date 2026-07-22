# Contributing

## Getting started

```bash
cp infra/compose/.env.example infra/compose/.env       # edit the passwords
cp services/platform-api/.env.example services/platform-api/.env
cp services/ai-sim-service/.env.example services/ai-sim-service/.env

docker compose -f infra/compose/dev.yml --env-file infra/compose/.env up -d

pnpm install
pnpm turbo run dev            # apps/web-client + services/platform-api

cd services/ai-sim-service && uv sync
```

## Architectural conventions

- **Layering**: every domain module in `platform-api` and every bounded
  context in `ai-sim-service` follows
  `domain/application/infrastructure/interface` — see
  [`docs/adr/0001-layered-module-convention.md`](docs/adr/0001-layered-module-convention.md).
  `domain` never imports the ORM/driver/framework directly.
- **Bounded contexts**: see
  [`docs/domain-language.md`](docs/domain-language.md) for the shared
  vocabulary (Planet, Era, Species, Session, Embedding, ...) and
  [`docs/adr/`](docs/adr/) for why the codebase is split the way it is.
- **AI-specific code** (prompts, agents, RAG pipelines) lives under
  `services/ai-sim-service/src/ai_sim_service/tutor/` — prompts are files in
  `tutor/prompts/`, never inline strings in application code.

## Naming

- TypeScript workspace packages are scoped `@ecosfera/*`.
- NestJS files follow the framework's own convention (`*.module.ts`,
  `*.controller.ts`, `*.service.ts`).
- Python packages/modules use `snake_case`; each bounded context
  (`simulation`, `tutor`) is a top-level package under `ai_sim_service`.

## Checks before opening a PR

```bash
# Node packages (apps/web-client, services/platform-api)
pnpm turbo run lint build test

# ai-sim-service
cd services/ai-sim-service
uv run ruff check .
uv run mypy
uv run pytest
```

Both are wired into CI (`.github/workflows/ci-node.yml` and
`ci-python.yml`) and run on every push/PR to `develop`/`main`.

## Commit messages

Conventional-commit style (`type(scope): summary`), in English —
e.g. `feat(tutor): add retrieval pipeline`, `fix(platform-api): ...`,
`docs(architecture): ...`.
