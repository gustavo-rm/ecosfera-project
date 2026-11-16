# 0006 — Contrato HTTP declarado em código (Zod) e OpenAPI 3.1 congelado

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

O Dossiê define REST/OpenAPI 3.1 congelado em `packages/api-contracts`; o backlog fala em tRPC + Zod. Precisamos de validação de borda e de um contrato que não divirja da implementação.

## Decisão

- Cada rota declara um `definirEndpoint({...})` com schemas Zod de parâmetros, query, corpo e respostas. O decorador `@Endpoint` liga a rota do Nest a esse contrato; um interceptor valida a entrada com ele.
- `pnpm openapi:gerar` produz `packages/api-contracts/openapi/platform-api.v1.yaml` (OpenAPI 3.1), `asyncapi/platform-events.v1.yaml`, tipos TypeScript (`src/generated/platform-api.ts`, via openapi-typescript) e documentação HTML estática.
- `pnpm openapi:verificar` (e um teste) falham se o arquivo congelado divergir do código. Todas as respostas dos testes de integração são validadas contra o arquivo congelado (AJV 2020).
- **Não adotamos tRPC** (decisão travada pelo Dossiê; mudaria o contrato com o frontend).

## Consequências

- Mudança de contrato aparece como diff no PR do pacote de contratos — revisão explícita.
- Mensagens de validação em pt-BR (locale do Zod), sem ecoar valores enviados.
