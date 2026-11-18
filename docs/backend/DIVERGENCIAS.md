# Divergências entre documentos e repositório

Regra: o repositório manda sobre o que existe; os documentos mandam sobre o que deveria existir. Cada linha diz a leitura adotada.

## Herdadas do briefing (seção 13)

| # | Onde | Divergência | Leitura adotada |
|---|---|---|---|
| D1 | Dossiê antigo × v3 | Partes citam Java/Spring/JPA | NestJS + TypeORM |
| D2 | Backlog × Dossiê v3 | Backlog usa Prisma | TypeORM (baseline já aplicada) |
| D3 | Backlog × Dossiê v3 | Backlog usa NATS | Redis Streams atrás da porta `EventPublisher`/`AssessmentEventSource` |
| D4 | Backlog × Dossiê | Backlog usa tRPC + Zod | OpenAPI 3.1 congelado; Zod só para validar bordas e gerar o OpenAPI. Sem tRPC (ADR 0006) |
| D5 | Backlog × Dossiê | Backlog cita Socket.IO | WebSocket nativo (`ws`) com mensagens tipadas (ADR 0011) |
| D6 | Nomes de pastas | `apps/api` / `apps/platform-api` / `packages/shared` | Reais: `services/platform-api`, `packages/api-contracts` |
| D7 | Dossiê ERS | `POST /assessment/events` na API da plataforma, mas a ingestão é do `ai-sim-service` | O `platform-api` expõe `POST /assessment/events` só para credencial de serviço, com gate de consentimento, e consome Redis Streams (ADR 0013) |
| D8 | Dossiê ERS | "pesquisador" e "serviço" como papéis de auth, RBAC com 4 papéis | Ver ADR 0008 |
| D9 | Backlog | Dependências cruzadas inconsistentes | Seguimos os requisitos |
| D10 | Memória do projeto | `tutoring`, nome da camada `interface/`, numeração de ADR | `tutoring` fica em `orchestration` (só proxy); camada `interface/` mantida (ADR 0001 já aprovado); ADRs seguem `docs/adr/NNNN` |

## Encontradas no repositório (fase 0)

| # | Onde | Divergência | Leitura adotada |
|---|---|---|---|
| D11 | Briefing §1.4 × `services/ai-sim-service` | O briefing diz que o `ai-sim-service` tem "walking skeleton" com HTTP versionado, RFC 7807, ingestão de telemetria com gate de consentimento e cobertura de 95%. O repositório tem só pastas vazias e uma migração Alembic | Tratamos o serviço como inexistente: todas as portas têm fakes. O endpoint interno de consentimento é proposta para quando ele existir |
| D12 | Briefing × baseline | Papéis do briefing em português (`aluno`, `professor`...). O enum `platform.user_role` da baseline usa `student`, `teacher`, `coordinator`, `admin`, `guardian` | Valores do enum da baseline na API e no banco. No domínio, nomes em português mapeiam 1:1 |
| D13 | Briefing §6.1 × baseline | Briefing: "Missao N───N HabilidadeBNCC", missão do professor para a turma. Baseline: `mission.track_id NOT NULL` (missão pertence a uma trilha), sem escola nem autor | Missão continua presa à trilha (nível). Nova migração adiciona escola, autor, objetivo, parâmetros e a tabela `mission_assignment` (publicação para turmas) |
| D14 | Briefing §6.1 × baseline | `feedback.assessment_id NOT NULL`: feedback só existe preso a uma avaliação. RF-067 pede feedback do professor ao aluno | Nova migração torna `assessment_id` opcional e adiciona aluno, autor e escola (alteração não destrutiva) |
| D15 | Briefing × baseline | `track` não tem nível (EF II/Médio/Técnico) e `class` não aponta para trilha | Nova migração: `track.level` e `class.track_id` |
| D16 | Briefing × baseline | `competency` sem código; `bncc_skill` sem vínculo com competência (modelo conceitual: Habilidade N───1 Competência) | Nova migração adiciona códigos, vínculo e estado de validação |
| D17 | Briefing × baseline | `consent` sem finalidade, versão do texto nem revogação | Nova migração adiciona essas colunas |
| D18 | README/glossário × briefing | `docs/domain-language.md` diz que o contexto "Platform" cuida só de "identidade, contas, sessões". O briefing dá ao `platform-api` também turmas, missões, painel e gateway | Seguimos o briefing (Dossiê v3). O glossário é de outra frente: pedido de atualização registrado |
| D19 | `infra/compose/dev.yml` | `minio/minio:latest` não baixa mais do Docker Hub (acesso negado neste ambiente) | Testes usam `chainguard/minio`. Pedido à frente de infra |
| D20 | `.nvmrc` (24.18.0) × ambiente | O ambiente local tem Node 22.23 | O pacote declara `engines.node >=22`; CI usa o `.nvmrc` |
| D21 | Briefing §5.1 | Base `/{service}/api/v1` sem nome de serviço definido | Base adotada: `/platform/api/v1` |
| D22 | Briefing §5.2 × backlog | Dossiê devolve `refreshToken` no corpo; backlog pede cookie `httpOnly` | Os dois, ver ADR 0009 |
| D23 | Dossiê §5.8 `GET /dashboard/reports/export` | O Dossiê não diz se devolve o arquivo ou um link | Devolve JSON com URL assinada de curta duração (o arquivo fica no MinIO/S3). Idem `GET /research/dataset` |
| D24 | Dossiê §5.3 | Só `POST /users/{id}/consent`; não há rota de revogação | Acrescentada `POST /users/{id}/consent/revoke` (aditiva) |
| D25 | Briefing §5.5 × Dossiê | `GET /planets/{id}/stream` é WebSocket, sem lugar no OpenAPI | Documentado na descrição do OpenAPI e no ADR 0011; não é operação REST |
| D26 | Briefing §1.4 | "Docker Compose ... MinIO" | `minio/minio:latest` não baixa; testes usam `chainguard/minio` (D19/P1) |
| D27 | Backlog TASK-0028 (Keycloak/Ory) | Não há provedor OIDC no compose | Implementação genérica OIDC; verificada só contra provedor local de teste (P7) |
