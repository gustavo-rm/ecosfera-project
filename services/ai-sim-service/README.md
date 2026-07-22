# ECOSFERA — ai-sim-service

Serviço Python/FastAPI de **simulação científica** e **IA** do projeto ECOSFERA.
Respeita a fronteira **determinístico × IA** (Dossiê PD&I §8, GDD §10): a IA medeia
contexto, ritmo e explicação; **nunca** falsifica a ciência que o aluno precisa entender.

## O que já roda (walking skeleton — base do MVP / Inc 1)
- `POST /ai/api/v1/ai/explain` — explicação causal por **regras determinísticas**
  (RF-033/039), pronta para virar LLM+RAG no Inc 6 sem mudar o contrato.
- `POST /ai/api/v1/assessment/events` — ingestão de **telemetria** (RF-071) com
  bloqueio de **consentimento** LGPD (RNF-009).
- `GET /ai/api/v1/health` e `/metrics` (Prometheus).

## Rodar
```bash
uv sync            # cria .venv e instala deps
make run           # API em http://localhost:8000/docs
make check         # lint + mypy + testes (espelha o CI)
docker compose up  # infra local (postgres+pgvector, mongo, redis)
```

## Estrutura (hexagonal — ADR 0001)
```
domain/         regra pura (motor de regras causais, modelos de telemetria)
application/    casos de uso + portas (Protocols)
infrastructure/ adaptadores de saída (persistência, mensageria, LLM)
interfaces/     adaptadores de entrada (HTTP v1) + composition root
configs/        regras causais versionadas (dados, não código)
```
Pastas `rag/ embeddings/ agents/ evaluation/ models/ pipelines/` estão vazias por
design — cada uma é ativada em seu incremento (ver ROADMAP e ADR 0002).
