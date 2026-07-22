# ECOSFERA

Plataforma educacional de simulação de ecossistemas com um tutor de IA
(RAG/LLM) e avaliação stealth do aprendizado.

## Estrutura do monorepo

```
apps/
  web-client/        Next.js + React Three Fiber — cliente web
services/
  platform-api/      NestJS + TypeORM — identidade, contas, sessões (schema Postgres "platform")
  ai-sim-service/     Python — simulação do ecossistema e tutor de IA/RAG (schema Postgres "rag" + MongoDB)
packages/
  api-contracts/     Tipos/contratos de API compartilhados entre serviços
  shared-types/      Tipos compartilhados entre apps/services TypeScript
  ui/                Design system compartilhado
  config/            Configuração de lint/format compartilhada
infra/
  compose/           Docker Compose (Postgres+pgvector, MongoDB, Redis, MinIO, Ollama)
  docker/            Scripts de inicialização dos bancos
docs/
  adr/               Architecture Decision Records
  domain-language.md Glossário da linguagem ubíqua do domínio
```

Gerenciado com **pnpm workspaces** + **Turborepo** para os pacotes
TypeScript; `services/ai-sim-service` é um projeto Python independente
gerenciado com **uv**.

## Arquitetura

- Cada bounded context (`platform`, `simulation`, `tutor`) segue a convenção
  de camadas `domain/application/infrastructure/interface` —
  ver [`docs/adr/0001-layered-module-convention.md`](docs/adr/0001-layered-module-convention.md).
- `platform-api` e `ai-sim-service` são serviços separados que nunca acessam
  o schema um do outro diretamente — ver
  [`docs/adr/0002-platform-api-ai-sim-service-split.md`](docs/adr/0002-platform-api-ai-sim-service-split.md)
  e [`docs/adr/0003-shared-postgres-schema-per-service.md`](docs/adr/0003-shared-postgres-schema-per-service.md).
- Vocabulário de domínio (Planet, Era, Species, Session, Embedding, ...) em
  [`docs/domain-language.md`](docs/domain-language.md).

## Como rodar localmente

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md) para o passo a passo completo
(infra via Docker Compose, apps/services em Node, `ai-sim-service` em
Python/uv) e as checagens esperadas antes de abrir um PR.

## Licença

MIT — ver [`LICENSE`](LICENSE).
