# Plano do backend (`platform-api`) — documento vivo

Pacote: `services/platform-api` (o Dossiê o chama de `apps/platform-api`; o backlog, de `apps/api`).
Branch: `feature/platform-api-backend`, criada a partir da `develop`.

## Ponto de partida (reconhecimento, fase 0)

- O `platform-api` era o *starter* do NestJS 11 ("Hello World"), mais a migração baseline TypeORM com 18 tabelas no schema `platform` e um `data-source.ts`.
- TypeORM instalado é a **1.1.0**. NestJS 11. Testes com Jest (ts-jest). ESLint com `typescript-eslint` e Prettier.
- Convenção de camadas já aprovada: ADR 0001 (`domain/`, `application/`, `infrastructure/`, `interface/`).
- ADRs ficam em `docs/adr/NNNN-titulo.md`, em português (0001 a 0004 existem).
- `packages/api-contracts` existe e está vazio (placeholder para specs OpenAPI/AsyncAPI).
- `ai-sim-service` é só esqueleto de pastas Python. **Não** tem HTTP, gate de consentimento nem ingestão (o briefing diz o contrário; ver `DIVERGENCIAS.md`).
- O compose de dev sobe PostgreSQL (pgvector), MongoDB, Redis, MinIO e Ollama. A imagem `minio/minio:latest` não baixa mais do Docker Hub neste ambiente.
- O CI da raiz (`ci-node.yml`) roda `pnpm turbo run lint build test` em todos os pacotes.

## Arquitetura escolhida (resumo; detalhes nos ADRs 0005 a 0017)

- Monólito modular NestJS com quatro contextos em `src/modules/`: `identity`, `education`, `assessment`, `orchestration`. Cada um com `domain/ application/ infrastructure/ interface/`.
- `src/shared/` contém o que atravessa contextos: configuração, observabilidade, erros RFC 7807, contrato HTTP, autorização central, banco, Redis, auditoria, barramento de eventos, armazenamento de objetos.
- Contrato HTTP declarado em código (Zod) por rota e exportado para OpenAPI 3.1 em `packages/api-contracts/openapi/platform-api.v1.yaml`. O CI falha se o arquivo congelado divergir do código ou se a resposta real divergir do contrato.
- Autorização: decorador `@Autorizacao(...)` obrigatório em toda rota, avaliado por um guard global e verificado de novo nos casos de uso.

## Fases

| Fase | Conteúdo | Estado |
|---|---|---|
| 0 | Reconhecimento, branch, plano, divergências | feito |
| 1 | Fundação: config validada, logs, RFC 7807, health/ready, migrações + drift, Redis, Testcontainers, CI do pacote (proposto), Dockerfile | feito |
| 2 | Identidade e acesso | feito |
| 3 | Consentimento e LGPD | feito |
| 4 | Educação | feito |
| 5 | Gateway e tempo real | feito |
| 6 | Avaliação (leitura) e painel | feito |
| 7 | Federação OIDC e LTI 1.3 | feito (verificado só contra provedor local) |
| 8 | Acabamento: contratos, carga, smoke, relatórios, revisão independente e correções | feito |

O estado por requisito está em `MATRIZ_DE_COBERTURA.md`; o resumo final, em `RELATORIO_FINAL.md`.
