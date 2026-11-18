# Matriz de cobertura (Anexo A)

Status: **FV** = feito e verificado (teste automatizado ou smoke), **FNV** = feito e não verificado, **P** = parcial, **NF** = não feito. "Smoke n" = passo do `relatorios/SMOKE.txt`.

## Requisitos funcionais

| ID | Status | Onde / como foi verificado | Observação |
|---|---|---|---|
| RF-001 | FV | `POST /schools` cria escola + admin inicial; `educacao.int-spec`, smoke 1 | Só o operador da plataforma cria escola |
| RF-002 | FV | `POST /users` com regras por papel; desativar/reativar (`PATCH /users/{id}/status`); matriz de acesso | Papéis ampliados (ADR 0008). Sem mailer real em produção: contas novas precisam de senha inicial definida pelo admin |
| RF-003 | FV | Login, falha negada e auditada; `autenticacao.int-spec` | |
| RF-004 | FV | Guard central + reverificação; matriz (183 checagens) | |
| RF-005 | FV | Turmas, matrícula, aluno vê só as suas; `educacao.int-spec` | |
| RF-006 | FV | Esqueci/redefinir e redefinição pelo admin | E-mail real não existe: Mailer falso em dev, `disabled` em produção |
| RF-007 | FV | `POST /users/{id}/guardians`; smoke 1 | |
| RF-008 | FV | Consentimento por finalidade, bloqueante, revogável; fluxo e smoke 2–4 | Textos são placeholders (P9) |
| RF-009 | P | LTI 1.3 (launch, importação de turma por curso, mapeamento de papéis) e OIDC; `federacao.int-spec` | Só provedor local de teste; NRPS (lista completa da turma) não feito |
| RF-010 | FV | `PATCH /users/{id}/preferences` | |
| RF-061 | FV | Trilha por turma; `PATCH /classes/{id}/track` | |
| RF-062 | FV | Missão com BNCC obrigatória, 422 para código inexistente; smoke 5 | |
| RF-063 | FV | `/dashboard/classes/{id}/overview` | |
| RF-064 | FV | `/dashboard/classes/{id}/competencies`, perfil por aluno | |
| RF-065 | NF | — | "Could"; dados existem (planetas por aluno), visualização comparativa não foi feita |
| RF-066 | FV | Exportação CSV/PDF com URL assinada que expira; smoke 7; MinIO real | PDF não tem teste de conteúdo |
| RF-067 | FV | Feedback cifrado em repouso; aluno lê e marca como lido; `lgpd-e-avaliacao.int-spec` | |
| RF-068 | FV | `/dashboard/classes/{id}/consents`; smoke 2 | |
| RF-071 | FV (lado plataforma) | Gate de consentimento na projeção e no `POST /assessment/events`; endpoint interno `/internal/consent/{id}` | Ingestão de telemetria bruta é do ai-sim-service (P6) |
| RF-072/073 | FV (projeção) | Projeção idempotente de `CompetenciaAtualizada`; perfil | Cálculo é do ai-sim-service |
| RF-074 | FV | `POST/GET /assessment/students/{id}/assessments`; `lgpd-e-avaliacao.int-spec` | Aluno não registra nem lê |
| RF-075 | P | Rubrica via evento `RubricaAvaliada` (projeção) ou registro `kind=rubric` pelo professor | O registro pelo professor é testado; o evento `RubricaAvaliada` não tem teste dedicado |
| RF-076 | FV | Evidências rastreáveis (`eventId`, planeta, BNCC) e mapa BNCC | |
| RF-077 | FV | Alertas por limiar configurável por escola (unitário + fluxo) | Limiares placeholder (P10) |
| RF-078 | FV | Dataset anonimizado, k=5, varredura de PII, auditoria; smoke 8 | |
| RF-011/012/013 | FV (gateway) | Criar, validar, tick síncrono e 202 assíncrono | Fake de simulação |
| RF-015/016 | FV (gateway) | Checkpoints e linha do tempo | Fake |
| RF-017/018 | FV (gateway) | Intervenção com trade-off, 409 por pontos, idempotência | Pontos de ação são do ai-sim-service (P4) |
| RF-021 | FV (gateway) | Séries por métrica | Fake |
| RF-033/039 | FV (proxy) | SSE sem buffer, PII redigida | Fake do tutor |
| RF-035/036 | FV (proxy) | `/ai/hint` (exige missão acessível), `/ai/advisor`; `lgpd-e-avaliacao.int-spec` | Fake do tutor |

## Requisitos técnicos

| ID | Status | Observação |
|---|---|---|
| RT-002 | FV | Contrato REST versionado congelado; contrato interno com o ai-sim-service proposto (P4) |
| RT-004 | FV | PostgreSQL (TypeORM), Redis, MinIO; não toca `rag` nem MongoDB (teste de permissão) |
| RT-005 | FV | WebSocket com fan-out, replay, backpressure; carga com 45 conexões |
| RT-006 | FV | Dockerfile multi-stage não-root com healthcheck; compose do pacote; imagem testada |
| RT-007 | P | Ver RF-009 |
| RT-010 | P | Métricas Prometheus, logs com traceId, OpenTelemetry com propagação W3C; não verificado com coletor OTLP real nem traço atravessando o ai-sim-service real |

## Não funcionais

| ID | Status | Observação |
|---|---|---|
| RNF-002 | FV | Ação → delta p95 91 ms (fake); `relatorios/CARGA.md` |
| RNF-003 | FV (repasse) | SSE em fluxo verificado por tempos de chegada; a meta de 5 s depende do LLM real |
| RNF-004 | FV | Sem estado em memória além das conexões WebSocket abertas; sessões, limites, idempotência, fake de simulação no Redis/PostgreSQL. Não testado com 2 réplicas simultâneas |
| RNF-005 | FV | 45 alunos simultâneos, 0 erros |
| RNF-006 | FV | Matriz de acesso indevido + testes de token |
| RNF-007 | P | HTTPS obrigatório em produção, HSTS, segredos via ambiente/cofre, feedback cifrado; criptografia de disco/backup é da infraestrutura |
| RNF-009 | FV | Gate bloqueante, revogação imediata (inclusive WebSocket) |
| RNF-010 | FV (documental) | `INVENTARIO_DE_DADOS.md`; minimização no LTI |
| RNF-011 | FV | Anonimização com supressão e varredura |
| RNF-012 | FV (mecanismo) | Acesso, correção, exclusão (pseudonimização, sessões encerradas, `TitularExcluido`) e retenção após revogação testados | Prazos são placeholder do DPO (P9) |
| RNF-013 | FV | Filtros por escola, 404 entre escolas (41 rotas testadas), papéis de banco por schema |
| RNF-021 | P | Ponto de entrada idempotente `POST /planets/{id}/sync` (testado); formato final depende do contrato com o simulador |
| RNF-024 | FV | Lint e `tsc` estrito limpos, cobertura 86% linhas / 69% ramos com gate, ADRs |
| RNF-025 | P | `/health`, `/ready`, `/metrics`, logs estruturados; painéis de saúde/engajamento não feitos (infra) |
| RNF-026 | P | Mensagens de erro e validação em pt-BR; strings não externalizadas num catálogo i18n |

## Pedagógicos

| ID | Status | Observação |
|---|---|---|
| RP-001 | FV | Missão exige ≥ 1 habilidade BNCC do catálogo |
| RP-002 | FV | Trilhas EF II, Médio, Técnico |
| RP-004 | FV | Aluno não acessa perfil/evidências/BNCC/avaliações (403 testado) |
| RP-007 | FV | Alertas e perfis são informativos, com origem rastreável e aviso; nenhuma ação automática |

## Tarefas do backlog

| Tarefa | Status | Observação |
|---|---|---|
| TASK-0003 | FV | Dockerfile multi-stage, não-root, healthcheck (imagem construída e executada) |
| TASK-0004 | FV | Configuração Zod validada no boot |
| TASK-0005 | P | Job de CI do pacote proposto (`ci/platform-api.yml`), aguarda aprovação (P5) |
| TASK-0008 | P | OTel + Prometheus; sem coletor real |
| TASK-0010/0011/0012 | FV | TypeORM (não Prisma): 4 migrações novas, reversíveis, drift no teste e no CI proposto; índices de turma por escola e evidência por aluno/competência. Plano de execução **não** conferido com `EXPLAIN` em volume (FNV) |
| TASK-0014 | FV | Redis: sessões, revogação, limites, cache, pub/sub, streams |
| TASK-0016 | FV | Bootstrap modular, `/health`, logs estruturados |
| TASK-0017 | FV (divergência) | Zod nas bordas; sem tRPC (ADR 0006) |
| TASK-0018 | FV | CRUD acadêmico com RBAC |
| TASK-0019 | FV | Orquestração com posse, registro (outbox), repasse e job assíncrono |
| TASK-0020 | FV | Redis Streams atrás de porta, reprocessamento e DLQ, contratos AsyncAPI |
| TASK-0021 | FV | MinIO/S3 real testado; validação de tipo e tamanho; URLs assinadas. Upload de arquivos pelo usuário não existe (não há caso de uso) |
| TASK-0022 | FV | WebSocket autenticado, reconexão com replay, backpressure, carga |
| TASK-0023 | FV | OpenAPI 3.1 gerado + tipos TS |
| TASK-0024 | FV | Endpoints de planeta e tick |
| TASK-0025 | FV | Testes de contrato em toda resposta de integração |
| TASK-0026 | FV | JWT curto + refresh rotativo em cookie httpOnly + revogação Redis |
| TASK-0027 | FV | RBAC por guard + matriz |
| TASK-0028 | P | OIDC/LTI 1.3 contra provedor local |
| TASK-0029 | FV | Consentimento bloqueante, auditável, revogável |
| TASK-0030 | FV | Rate limiting, CORS, helmet, validação, limites de corpo, auditoria |
| TASK-0063/0064/0065 | FV (servidor) | Dashboards, missões BNCC, relatórios |
| TASK-0071/0072 | FV | Jest (unit/int), Testcontainers |
| TASK-0076 | P | Testes de authz por papel e escola, auditoria de dependências; SAST não rodado |
| TASK-0078 | FV | ADRs 0005–0017 |
| TASK-0080 | FV | Documentação HTML gerada do OpenAPI e verificada no CI (proposto) |
