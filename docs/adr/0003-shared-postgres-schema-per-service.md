# 0003 — Uma instância de Postgres, um schema por serviço

- Status: Aceito (decisão já em vigor no scaffold; formalizada aqui)
- Data: 2026-07-22

## Contexto

`platform-api` (dados transacionais) e `ai-sim-service` (embeddings do RAG,
via pgvector) precisam de Postgres. Rodar duas instâncias separadas em
desenvolvimento (e potencialmente em produção) tem custo operacional maior
sem benefício claro nesta fase do projeto.

## Decisão

Uma única instância de Postgres (`pgvector/pgvector:pg16`, ver
`infra/compose/dev.yml`), com um schema dedicado por serviço:

- `platform` — migrations do `platform-api` (TypeORM, `synchronize: false`).
- `rag` — migrations do `ai-sim-service` (Alembic).

Cada serviço só tem permissão/uso do seu próprio schema (ver comentário em
`infra/docker/postgres/initdb/01-extensions-schemas.sql`, que já registra a
recomendação de roles distintas por schema em produção).

## Consequências

- Nenhum dos dois serviços acessa a tabela do outro diretamente — a única
  forma de integração é via API.
- Simplicidade operacional em dev/staging (uma instância, um backup, um
  monitoramento) sem violar isolamento lógico entre bounded contexts.
- Antes de produção, criar roles Postgres distintas por schema (apontado no
  comentário do script de init) para que uma credencial vazada de um serviço
  não dê acesso ao schema do outro.
