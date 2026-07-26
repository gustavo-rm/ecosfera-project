# ECOSFERA — ai-sim-service

Serviço Python/FastAPI de **simulação científica** e **IA** do projeto ECOSFERA.
Respeita a fronteira **determinístico × IA** (Dossiê PD&I §8, GDD §10): a IA medeia
contexto, ritmo e explicação; **nunca** falsifica a ciência que o aluno precisa entender.

## O que já roda
Base do MVP / Inc 1 (walking skeleton) + **núcleo de simulação determinístico**
com **linha do tempo, replay e persistência real**. Prefixo da API: `/ai/api/v1`.

| Método | Rota | Descrição | RF |
| --- | --- | --- | --- |
| POST | `/simulation/planets` | Cria e configura um planeta a partir de uma semente | RF-011/012 |
| POST | `/simulation/planets/{planet_id}/tick` | Avança 1 tick determinístico: novo estado + cadeia causal | RF-013/014/023 |
| GET | `/simulation/planets/{planet_id}` | Estado atual do planeta | RF-016 |
| POST | `/simulation/planets/{planet_id}/advance-era` | Avança uma **era** inteira: checkpoint append-only + marcos + cadeia causal | RF-013/014/016 |
| GET | `/simulation/planets/{planet_id}/timeline` | Lista as eras e seus metadados | RF-016 |
| GET | `/simulation/planets/{planet_id}/eras/{era}` | **Reconstrói** o estado da era por replay determinístico | RF-016/023 |
| POST | `/ai/explain` | Explicação causal por **regras determinísticas** (vira LLM+RAG no Inc 6) | RF-033/039 |
| POST | `/assessment/events` | Ingestão de **telemetria** com bloqueio de **consentimento** LGPD | RF-071 / RNF-009 |
| GET | `/health` | Liveness do serviço | — |
| GET | `/metrics` | Métricas Prometheus (fora do prefixo `/ai/api/v1`) | — |

Tick e era compõem o motor de simulação (que **produz** as observações) com o motor
de feedback causal existente (que **explica** o delta) — mesmo contrato de
`/ai/explain` (`source="rules"`, `grounded=true`).

**Determinismo (RF-023) é verificável em produção:** `GET .../eras/{era}` reexecuta o
motor a partir do checkpoint anterior e responde `matches_checkpoint`, indicando se a
reconstrução bateu com o estado gravado na época.

### Subsistemas do tick
Estratégias plugáveis, rodadas nesta ordem de acoplamento (ADR 0004):

```
physics -> chemistry -> climate -> geology -> ocean -> life
```
`physics` integra a órbita por **velocity Verlet** (simplético: a energia orbital
não deriva) e entrega a irradiância; `geology` mantém o vulcanismo que alimenta a
desgaseificação; `ocean` fecha o ciclo da água, dilui/concentra a salinidade e
sequestra calor da superfície.

## Rodar
```bash
uv sync            # cria .venv e instala deps (modo inmemory, sem banco)
make run           # API em http://localhost:8000/docs
make check         # lint + mypy + testes (espelha o CI)
docker compose up  # infra local (postgres+pgvector, mongo, redis)
```

## Persistência
O backend é escolhido por **feature flag**; a porta `PlanetRepository` é a mesma
nos dois casos (ADR 0005), então nenhuma camada acima muda.

| `ECOSFERA_PERSISTENCE_BACKEND` | Uso |
| --- | --- |
| `inmemory` (default) | testes e dev — sobe **sem** o extra `infra` instalado |
| `postgres` | staging/prod — exige `uv sync --extra infra` |

```bash
# 1. Suba o banco e aplique as migrations (schema `simulation`)
docker compose up -d postgres
uv sync --extra infra
export DATABASE_URL="postgresql+asyncpg://ecosfera:ecosfera@localhost:5432/ecosfera"
uv run python -m alembic upgrade head     # NUNCA o binário direto (evita conda)
uv run python -m alembic upgrade head --sql   # opcional: só gera o SQL, sem banco

# 2. Suba a API apontando para o Postgres
ECOSFERA_PERSISTENCE_BACKEND=postgres \
ECOSFERA_DATABASE_URL="$DATABASE_URL" \
  uv run uvicorn ecosfera_ai.main:app --app-dir src
```
As migrations do serviço vivem numa **única árvore** (`migrations/`) cobrindo os
schemas `rag` (Inc 6) e `simulation`. Os testes de integração da persistência real
usam Testcontainers e são **pulados automaticamente** quando não há Docker.

## Estrutura (hexagonal — ADR 0001)
```
domain/            regra pura (motor de regras causais, modelos de telemetria)
simulation_engine/ núcleo determinístico (estado, subsistemas, tick, timeline/replay)
application/       casos de uso + portas (Protocols)
infrastructure/    adaptadores de saída (persistência in-memory/Postgres, mensageria, LLM)
interfaces/        adaptadores de entrada (HTTP v1) + composition root
configs/           regras causais e parâmetros de simulação versionados (dados)
migrations/        Alembic — uma árvore para os schemas `rag` e `simulation`
```
Pastas `rag/ embeddings/ agents/ evaluation/ models/ pipelines/` estão vazias por
design — cada uma é ativada em seu incremento (ver ROADMAP e ADR 0002).
