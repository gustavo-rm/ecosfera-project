# Relatório final — backend `platform-api`

Branch `feature/platform-api-backend` (a partir da `develop`), commits locais em Conventional Commits. **Nada foi enviado ao GitHub**: push e PR dependem de aprovação.

## 1. Ponto de partida

O `services/platform-api` era o starter do NestJS ("Hello World") mais a migração baseline de 18 tabelas. O `ai-sim-service` é só esqueleto (sem HTTP, sem gate de consentimento — o briefing dizia o contrário; ver D11). O pacote `packages/api-contracts` estava vazio.

## 2. O que foi feito

- **Arquitetura** (ADR 0005): monólito modular NestJS 11, quatro contextos (`identity`, `education`, `assessment`, `orchestration`) com `domain/application/infrastructure/interface`, domínio sem framework, portas e adaptadores.
- **Banco**: 4 migrações novas e aditivas sobre a baseline intocada (identidade/LGPD, educação/catálogo, avaliação/orquestração, contexto LTI), todas com `down`; 31 entidades TypeORM sem drift; papéis de banco por schema (`platform_app` sem UPDATE/DELETE no `audit_log`, sem acesso ao `rag`); `audit_log` imutável também por gatilho.
- **Identidade e acesso**: login (Argon2id, sem enumeração, limite por conta e por IP), JWT curto + sessão no Redis, refresh rotativo com revogação da família, cookie httpOnly ou corpo, logout, redefinição de senha, papéis ampliados (responsável, pesquisador, operador; serviço como credencial própria), desativação de conta. Autorização declarativa em toda rota, guard central que nega por padrão, posse e isolamento por escola verificados de novo nos casos de uso.
- **Consentimento e LGPD**: consentimento por finalidade (`platform_use`, `learning_assessment`, `research`), bloqueante, auditado, revogável com efeito imediato (inclusive fechando WebSockets); gate reutilizável com cache versionado; endpoint interno para outros serviços; evento `ConsentimentoRevogado`; inventário de dados; acesso, correção e exclusão (pseudonimização); retenção parametrizável com expurgo; textos legais como placeholders versionados.
- **Educação**: escolas com admin inicial, turmas, matrículas, trilhas, missões ancoradas à BNCC (422 para código inexistente), publicação para turmas, catálogo BNCC/competências como dado versionado revisável sem deploy (seed `pending_validation`), preferências de acessibilidade e idioma.
- **Gateway e tempo real**: portas `SimulationGateway`/`TutorGateway` com fakes determinísticos e adaptadores HTTP reais (timeout, repetição só em idempotentes, 503/504 tratados, `traceparent`); planeta, tick (202 + WebSocket quando pesado), intervenções com idempotência, linha do tempo, checkpoints, séries, eventos, sincronização offline idempotente; SSE do tutor sem buffer, com redação de PII; WebSocket com autenticação no handshake, fan-out Redis, replay, backpressure.
- **Avaliação e painel**: outbox transacional + Redis Streams (grupo, reprocessamento, fila morta); projeção idempotente e ordenada respeitando consentimento; perfil, evidências rastreáveis, mapa BNCC, visão da turma, competências, alertas por limiar por escola, status de consentimento da turma, agregado da escola, feedback cifrado, pré/pós-teste, exportação CSV/PDF em MinIO com URL assinada curta, dataset de pesquisa anonimizado (pseudônimo descartável, generalização, k=5, varredura de PII).
- **Federação**: OIDC (código + PKCE) e LTI 1.3 (launch, importação de turma por curso, mapeamento conservador de papéis), estado amarrado ao navegador.
- **Contratos**: OpenAPI 3.1 gerado das rotas e congelado em `packages/api-contracts` (87 operações, com `x-authorization`), AsyncAPI dos eventos, tipos TS gerados, documentação HTML estática.
- **Operação**: configuração validada no boot (fakes proibidos em produção, `NODE_ENV` obrigatório), logs JSON com traceId e redação de PII, métricas Prometheus, OpenTelemetry, `/health` e `/ready`, Dockerfile multi-stage não-root com healthcheck, compose do pacote, seed com senhas geradas, scripts de papéis, token de serviço, smoke e carga.
- **Documentação**: ADRs 0005–0017, `DECISOES` (38), `DIVERGENCIAS` (27), `PEDIDOS_A_OUTRAS_FRENTES` (P1–P10), `MATRIZ_DE_AUTORIZACAO` (gerada), `INVENTARIO_DE_DADOS`, `MATRIZ_DE_COBERTURA`, relatórios de segurança, carga, cobertura e smoke.

## 3. O que foi verificado e como

| Verificação | Resultado |
|---|---|
| Testes (Jest): 21 suítes, 156 testes (unitários + integração com PostgreSQL pgvector, Redis e MinIO reais via Testcontainers), app rodando como `platform_app` | todos passam |
| Teste de contrato: toda resposta de integração validada contra o OpenAPI congelado; arquivo congelado igual ao gerado | ✔ (pegou 404 não declarados em 20 rotas, corrigido) |
| Arquitetura: toda rota com contrato e autorização; lista fechada de 12 rotas públicas | ✔ |
| Matriz de acesso indevido gerada: 188 verificações (401/403/404) + credencial de serviço | ✔ |
| Migrações do zero, `down` das 4 novas e `up` de novo sem duplicar seed; drift; baseline idêntica à `develop` | ✔ |
| Cobertura: 86,2% linhas, 68,7% ramos, com gate | ✔ |
| Lint (typescript-eslint type-checked) e `tsc --strict` | 0 erros |
| Smoke de ponta a ponta (Anexo B) contra o servidor em execução, como `platform_app` | 60/60 (`relatorios/SMOKE.txt`) |
| Carga: 45 alunos, 45 WebSockets; ação → delta p95 140 ms; login p95 236 ms; painel p95 792 ms; 0 erros | ✔ (`relatorios/CARGA.md`) |
| Imagem Docker: build, produção com fake recusa o boot, produção real sobe saudável como uid 1000, HTTP sem TLS → 400 | ✔ |
| `pnpm audit --prod`: 0 vulnerabilidades altas/críticas nas dependências do platform-api | ✔ |
| Revisão independente por agente que não viu o trabalho | 15 achados + 4 suspeitas confirmadas, corrigidos com testes (seção 7) |

## 4. O que NÃO foi verificado e por quê

- **OIDC e LTI contra provedores reais** (Keycloak/Ory, Moodle/Canvas): não há acesso; verificado só contra provedor local de teste (`test/support/provedor-de-teste.ts`). NRPS (lista completa da turma no LMS) não implementado.
- **`ai-sim-service` real**: não existe como serviço; os adaptadores HTTP foram testados contra servidor local (timeout, repetição, erros), não contra o contrato real.
- **Traço OpenTelemetry até o ai-sim-service** e exportação OTLP: sem coletor no ambiente.
- **Duas réplicas simultâneas**: o desenho é sem estado (sessões, limites, fake e fan-out no Redis), mas não rodei duas instâncias atrás de balanceador.
- **SAST** (SonarQube/CodeQL): não disponível aqui; previsto no CI proposto.
- **Plano de execução dos índices em volume** (`EXPLAIN` com dados realistas).
- **CI no GitHub**: o job proposto não foi instalado (precisa de aprovação, P5). O `pnpm install --frozen-lockfile` do CI da raiz **falha hoje** sem o pedido P3.
- Corrida do cache de consentimento: a correção é lógica (versão atômica); a corrida em si não é reproduzida em teste.

## 5. Mudanças de comportamento em algo que já existia

- O starter "Hello World" (`GET /`, `AppController`, `AppService` e seus testes) foi removido; a API vive em `/platform/api/v1`.
- `tsconfig.json` passou a `strict`; `package.json` do pacote trocou scripts (`test` = unitários, `test:int`, `ci`, `migration:*`, etc.) e removeu a config Jest embutida.
- `data-source.ts` (CLI de migrações) agora usa a lista explícita de entidades e `uuidExtension: pgcrypto`; continua no mesmo caminho e com a mesma tabela de migrações.
- `.env.example` do pacote ganhou variáveis obrigatórias (segredos, `NODE_ENV`, Redis); `README.md` do pacote virou um ponteiro para `docs/backend/README.md`.
- `@nestjs/*` subiu de 11.1 para 11.2.10 e `express` para 5.3 (correções de segurança).
- Em `packages/api-contracts` (aditivo): `src/index.ts` exporta os tipos gerados; novos diretórios `openapi/`, `asyncapi/`, `docs/`, `src/generated/`.
- `pnpm-lock.yaml` mudou pelas dependências novas do pacote.

## 6. Riscos

- **Produção bloqueada por decisão jurídica**: com `CONSENT_REQUIRE_APPROVED_TEXT` (padrão em produção), nenhum menor usa a plataforma até o DPO aprovar os textos (P9) — comportamento correto, mas precisa estar no plano de implantação.
- **Sem mailer real**: em produção, contas precisam de senha inicial definida pelo admin; "esqueci a senha" não envia nada (sem enumeração, mas sem recuperação).
- **Confiança no admin da escola**: pode criar e vincular um responsável (auditado). Mitigação futura: confirmação do vínculo pelo responsável.
- **Painel**: uma checagem de consentimento por aluno (com cache); turmas muito grandes pedem consulta em lote.
- **Federação não testada contra produtos reais**; contrato interno com o ai-sim-service é proposta.
- **Sem Row Level Security**: isolamento por escola depende de código revisado e testado (ADR 0015).
- Dataset de pesquisa: risco residual de reidentificação em escolas pequenas mesmo com k=5.

## 7. Revisão independente

Achados e correções detalhados em `relatorios/SEGURANCA.md`. O mais grave (crítico): o admin de uma escola podia fazer o servidor enviar `JWT_ACCESS_SECRET` a um IdP controlado por ele e forjar token de operador — corrigido restringindo a variável de segredo a `OIDC_CLIENT_SECRET_*`. Também corrigidos: captura de aluno por matrícula, contorno do consentimento via `isMinor`, sessões que escapavam de "revogar todas", sequestro do e-mail do responsável, corrida do cache de consentimento, aceite sobre texto não aprovado, SSRF, CSRF de login federado, entre outros. Cada correção tem teste de regressão (`test/seguranca/regressoes-da-revisao.int-spec.ts`).

## 8. Decisões em aberto (precisam de alguém de fora)

| Decisão | Quem | Bloqueia? |
|---|---|---|
| Textos de consentimento, base legal do inventário, prazos de retenção, k do dataset | DPO / jurídico (P9) | Bloqueia uso por menores em produção |
| Validação do catálogo BNCC e dos limiares de alerta | Pedagogia (P10) | Não bloqueia o desenvolvimento; bloqueia ir a estudantes |
| Aprovar `allowBuilds` na raiz (P3) e o job de CI (P5) | Responsável pelo repositório | P3 bloqueia `pnpm install --frozen-lockfile` |
| Push da branch e abertura de PR | Você | — |
| Se a pedagogia quiser que o aluno veja algum progresso qualitativo (hoje vê só feedback textual) | Pedagogia | Não |

## 9. O que as outras frentes precisam fornecer para trocar os fakes

1. **ai-sim-service** (P4, P6): implementar o contrato interno proposto (`/simulation/api/v1/planets/...`, `/tutor/api/v1/...`, SSE `data: {"text": ...}`), aceitar a credencial de serviço do platform-api, ser autoritativo sobre pontos de ação, publicar `EvidenciaGerada`/`CompetenciaAtualizada` no stream `ecosfera.events.assessment` (AsyncAPI em `packages/api-contracts`), consultar `GET /internal/consent/{id}` antes de coletar e assinar `ConsentimentoRevogado`/`TitularExcluido`. Depois: `ADAPTER_SIMULATION=http`, `ADAPTER_TUTOR=http`, `AI_SIM_BASE_URL`.
2. **Infra** (P1, P7): imagem MinIO disponível; host público do MinIO para URLs assinadas; Keycloak/Ory e um LMS de teste no compose; coletor OTLP; provedor de e-mail (novo adaptador `Mailer`).
3. **Frontend** (P8): consumir o OpenAPI/tipos gerados, refresh por cookie, WebSocket com subprotocolos, tratar `consent-required`.
4. **Raiz do repositório** (P3, P5): `allowBuilds` e workflow de CI do pacote.
