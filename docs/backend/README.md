# platform-api — como rodar, testar e operar

Backend da plataforma ECOSFERA (`services/platform-api`): identidade e consentimento, educação (turmas, trilhas, missões BNCC), avaliação em modo leitura e painel, gateway de planetas/tutor, tempo real. NestJS 11 + TypeORM 1.1 + PostgreSQL (schema `platform`) + Redis + MinIO/S3.

Documentos: [PLANO](PLANO.md) · [MATRIZ_DE_AUTORIZACAO](MATRIZ_DE_AUTORIZACAO.md) · [INVENTARIO_DE_DADOS](INVENTARIO_DE_DADOS.md) · [DECISOES](DECISOES.md) · [DIVERGENCIAS](DIVERGENCIAS.md) · [PEDIDOS_A_OUTRAS_FRENTES](PEDIDOS_A_OUTRAS_FRENTES.md) · [MATRIZ_DE_COBERTURA](MATRIZ_DE_COBERTURA.md) · [RELATORIO_FINAL](RELATORIO_FINAL.md) · relatórios em [relatorios/](relatorios/) · ADRs `docs/adr/0005`–`0017` · contrato em `packages/api-contracts/openapi/platform-api.v1.yaml` (docs navegáveis: `packages/api-contracts/docs/platform-api.html`).

## Rodar em desenvolvimento

```bash
cp infra/compose/.env.example infra/compose/.env
```

```bash
docker compose -f infra/compose/dev.yml --env-file infra/compose/.env up -d postgres redis minio minio-init
```

```bash
cp services/platform-api/.env.example services/platform-api/.env
```

Preencha os quatro segredos do `.env` com valores gerados na sua máquina (`openssl rand -base64 48`; `DATA_ENCRYPTION_KEY` com `openssl rand -base64 32`) e ajuste senhas iguais às do compose.

```bash
pnpm install
```

```bash
pnpm --filter platform-api migration:run
```

```bash
pnpm --filter platform-api seed:dev
```

```bash
pnpm --filter platform-api dev
```

A API fica em `http://localhost:3000/platform/api/v1` (`/health`, `/ready`). O WebSocket do planeta é `ws://localhost:3000/platform/api/v1/planets/{id}/stream` com subprotocolos `ecosfera.v1` e `bearer.<accessToken>`.

> Observação: neste momento o pnpm 11 recusa `pnpm install --frozen-lockfile` enquanto o pedido P3 (`allowBuilds` na raiz) não for aprovado. Localmente, `npm_config_verify_deps_before_run=false` permite rodar os scripts.

### Credenciais locais

O seed **gera** as senhas a cada execução e grava em `services/platform-api/.credenciais-dev.json` (permissão 600, ignorado pelo git). Lá estão o operador da plataforma, admin, professores (Marina, Rafael), coordenadora (Beatriz), alunos (Lucas, Sofia), responsável (Helena) e pesquisador. Lucas começa **sem consentimento**: entre como Helena e registre o consentimento (`POST /users/{id}/consent`).

### Implantação em contêiner (on-premise por escola)

```bash
docker compose -f services/platform-api/compose.platform-api.yml --env-file infra/compose/.env up -d --build
```

Imagem multi-stage, usuário não-root, healthcheck; migrações num passo separado (`node dist/migrar.js`, papel `platform_migrator`). Em produção: `NODE_ENV=production`, adaptadores reais (`ADAPTER_SIMULATION=http`, `ADAPTER_TUTOR=http`, `ADAPTER_MAILER=disabled`, `ADAPTER_STORAGE=s3`), TLS terminado no proxy reverso com `TRUST_PROXY=true`, papéis de banco de `db/papeis-por-schema.sql` (`pnpm db:roles`), segredos do cofre. **Fakes não ligam em produção** (o boot falha).

## Testar

| Comando | O que roda |
|---|---|
| `pnpm --filter platform-api test` | Unitários (domínio, políticas, configuração, guard, cliente HTTP) — sem Docker |
| `pnpm --filter platform-api test:int` | Integração com Testcontainers (PostgreSQL pgvector, Redis, MinIO): migrações do zero e `down`, drift, audit_log imutável, auth, educação, gateway/WebSocket/SSE, projeção, painel, exportação, LGPD, federação, contrato e arquitetura, matriz de acesso indevido |
| `pnpm --filter platform-api test:cov` | Tudo, com gate de cobertura |
| `pnpm --filter platform-api ci` | lint + tipos + contrato congelado + `test:cov` |
| `pnpm --filter platform-api db:drift` | Drift entre entidades e migrações (`--aplicar-migracoes` num banco vazio) |
| `pnpm --filter platform-api openapi:gerar` / `openapi:verificar` | Gera / confere o contrato em `packages/api-contracts` |
| `pnpm --filter platform-api authz:matriz` | Regenera a matriz de autorização |
| `pnpm --filter platform-api smoke` | Smoke de ponta a ponta contra o servidor em execução (saída em `relatorios/SMOKE.txt`) |
| `pnpm --filter platform-api carga` | Carga: 45 alunos, 45 WebSockets, p95 |

Os testes de integração sobem a aplicação **como o papel restrito `platform_app`** e validam toda resposta contra o OpenAPI congelado.

## Convenção de chaves Redis (prefixo `REDIS_KEY_PREFIX`, padrão `ecosfera:platform:`)

| Chave | Conteúdo | TTL |
|---|---|---|
| `session:{sid}` (+ `:used`) | Sessão/família do refresh: `uid`, hash do refresh atual; conjunto de hashes já usados | validade do refresh (7 dias), renovada na rotação |
| `user_sessions:{uid}` | Sessões do usuário (para revogar tudo) | idem |
| `pwreset:{hash}` | Código de redefinição de senha | 30 min |
| `ratelimit:{nome}:{chave}` | Contadores de limite (conta por HMAC, nunca e-mail) | janela |
| `consent:{uid}` | Cache do gate de consentimento | 60 s, invalidado a cada mudança |
| `fed_state:{state}`, `fed_nonce:{nonce}` | Estado e nonce de OIDC/LTI (uso único) | 10 min / 1 h |
| `planet:{id}:stream` | Canal pub/sub do planeta | — |
| `planet:{id}:replay` | Últimas mensagens (reconexão) | 1 h |
| `consent:revoked` | Canal de revogação (fecha WebSockets) | — |
| `idem_lock:{escopo}:{chave}` | Trava de idempotência em andamento | 30 s |
| `fake_sim:{id}`, `action_points:{id}` | **Só o adaptador falso** de simulação | 7 dias |
| streams `ecosfera.events.platform` / `ecosfera.events.assessment` (+ `.dlq`) | Barramento de eventos | MAXLEN ~100k |
