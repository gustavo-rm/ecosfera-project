# 0015 — Isolamento por escola (multi-tenancy) e papéis de banco

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

RNF-013 e as duas formas de implantar (SaaS multi-tenant e on-premise por escola).

## Decisão

- Coluna de escola nas tabelas relevantes (novas colunas `school_id` por migração); regras de posse e consultas de leitura sempre filtram pela escola do ator.
- Papéis de banco por schema (`db/papeis-por-schema.sql`): `platform_app` só DML no schema `platform`, sem `UPDATE/DELETE/TRUNCATE` no `audit_log`, sem acesso ao `rag`; `platform_migrator` para DDL. Os testes rodam a aplicação como `platform_app`.
- **Sem Row Level Security por ora**: exigiria `SET` por transação com pool e reescrita das consultas; o ganho existe, mas o risco de regressão agora é maior. Registrado como evolução.

## Consequências

- Um vazamento entre escolas depende de erro em código revisado e testado (matriz gerada); RLS seria a terceira barreira.
