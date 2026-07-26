# ECOSFERA — ai-sim-service

Serviço Python/FastAPI de **simulação científica** e **IA** do projeto ECOSFERA.
Respeita a fronteira **determinístico × IA** (Dossiê PD&I §8, GDD §10): a IA medeia
contexto, ritmo e explicação; **nunca** falsifica a ciência que o aluno precisa entender.

## O que já roda
Base do MVP / Inc 1 (walking skeleton) + **núcleo de simulação determinístico**
(Inc 2). Prefixo da API: `/ai/api/v1`.

| Método | Rota | Descrição | RF |
| --- | --- | --- | --- |
| POST | `/simulation/planets` | Cria e configura um planeta a partir de uma semente | RF-011/012 |
| POST | `/simulation/planets/{planet_id}/tick` | Avança 1 tick determinístico: novo estado + cadeia causal | RF-013/014/023 |
| GET | `/simulation/planets/{planet_id}` | Estado atual do planeta (último checkpoint) | RF-016 |
| POST | `/ai/explain` | Explicação causal por **regras determinísticas** (vira LLM+RAG no Inc 6) | RF-033/039 |
| POST | `/assessment/events` | Ingestão de **telemetria** com bloqueio de **consentimento** LGPD | RF-071 / RNF-009 |
| GET | `/health` | Liveness do serviço | — |
| GET | `/metrics` | Métricas Prometheus (fora do prefixo `/ai/api/v1`) | — |

O tick compõe o motor de simulação (que **produz** as observações) com o motor de
feedback causal existente (que **explica** o delta) — mesmo contrato de `/ai/explain`
(`source="rules"`, `grounded=true`). Simulação **reprodutível por seed** (RF-023).

## Rodar
```bash
uv sync            # cria .venv e instala deps
make run           # API em http://localhost:8000/docs
make check         # lint + mypy + testes (espelha o CI)
docker compose up  # infra local (postgres+pgvector, mongo, redis)
```

## Estrutura (hexagonal — ADR 0001)
```
domain/            regra pura (motor de regras causais, modelos de telemetria)
simulation_engine/ núcleo de simulação determinístico (estado, subsistemas, tick)
application/       casos de uso + portas (Protocols)
infrastructure/    adaptadores de saída (persistência, mensageria, LLM)
interfaces/        adaptadores de entrada (HTTP v1) + composition root
configs/           regras causais e parâmetros de simulação versionados (dados)
```
Pastas `rag/ embeddings/ agents/ evaluation/ models/ pipelines/` estão vazias por
design — cada uma é ativada em seu incremento (ver ROADMAP e ADR 0002).
