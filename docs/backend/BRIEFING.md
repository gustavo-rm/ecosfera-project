---
title: "ECOSFERA — Briefing do backend (platform-api)"
subtitle: "Extrato do Dossiê PD&I v3, da Especificação do Evolution Engine e do backlog, só com o que o backend da plataforma precisa"
---

# 0. Como usar este arquivo

Este arquivo substitui a leitura integral dos documentos originais. O Dossiê tem cerca de 7 500 linhas e a maior parte trata de jogo, simulação e IA, que não fazem parte desta frente. Use este briefing como fonte principal. Quando ele não bastar, procure o identificador (`RF-008`, `§10`, `RSK-05`) com `grep` nos originais e leia só o trecho.

Convenções do texto:

- **[Dossiê §x]** indica de onde a informação veio.
- **[Inferência]** marca algo que não está escrito no Dossiê e foi deduzido. Confirme no repositório antes de tratar como fato.
- **[Proposta]** marca uma sugestão deste briefing, não uma decisão do projeto.
- O repositório é autoritativo sobre o que existe. Os documentos são autoritativos sobre o que deveria existir. Se discordarem, registre a divergência.

---

# 1. Escopo e fronteiras

## 1.1 O que é o backend desta tarefa

O backend desta tarefa é o **`platform-api`**: a plataforma educacional, em Node.js/NestJS/TypeScript. Ele cuida de:

- usuários, papéis, escolas, responsáveis e consentimento (LGPD);
- autenticação e autorização (JWT, refresh, RBAC, OIDC, LTI 1.3);
- turmas, matrículas, trilhas, missões ancoradas à BNCC e currículo;
- persistência relacional (PostgreSQL, schema `platform`), cache e sessões (Redis) e objetos (MinIO/S3);
- a parte de **leitura** da avaliação (perfil de competências, evidências, mapa BNCC) e o painel do professor, da coordenação e do pesquisador;
- o **gateway** que recebe as chamadas do cliente sobre planetas e as encaminha ao serviço de simulação e IA, depois de autorizar e registrar;
- tempo real para o cliente (WebSocket), auditoria, segurança, observabilidade e documentação de API.

## 1.2 O que está fora

Fora do escopo desta tarefa:

- **Motor evolutivo e simulação científica** (Evolution Engine, tick, clima, geologia, ecologia, eventos, Diretor).
- **IA:** tutor LLM, RAG, guardrails de LLM, stealth assessment (rede bayesiana), adaptação, embeddings.
- O serviço `ai-sim-service` (Python/FastAPI) e seus bancos: schema `rag` no PostgreSQL (Alembic) e MongoDB.
- O cliente web.

O backend conversa com o que está fora por **portas** (interfaces). Enquanto esses serviços não estiverem disponíveis, as portas têm **adaptadores falsos** (fakes) determinísticos. O backend implementa de verdade tudo o que é dele e simula só a borda (seção 9).

## 1.3 Estado do repositório

Repositório: `https://github.com/gustavo-rm/ecosfera-project`. A branch de trabalho do backend deve sair da `develop`.

Monorepo poliglota (pnpm workspaces + Turborepo para TypeScript; uv para Python) [Dossiê §7 de organização dos repositórios]:

| Unidade | Caminho no Dossiê | Caminho no backlog | Observação |
|---|---|---|---|
| Cliente web | `apps/web-client/` | `apps/web` | Fora desta tarefa |
| **Plataforma** | `apps/platform-api/` | `apps/api` | **Esta tarefa** |
| Simulação e IA | `services/ai-sim-service/` | `services/ai` | Fora; é dono do schema `rag` e do MongoDB |
| Contratos | `packages/api-contracts` | `packages/shared` | Fonte única de verdade dos contratos |
| Outros pacotes | `packages/config`, `packages/ui`, `packages/shared-types` | | |
| Infra | `infra/compose`, `infra/docker` | `infra`, `database` | |
| Docs | `docs/` | `docs` | Dossiê, ADRs e artefatos oficiais |

Os nomes diferem entre Dossiê e backlog. Descubra os nomes reais no repositório e não presuma caminhos.

## 1.4 O que já existe (informado pelo Dossiê)

O Dossiê v2/v3 registra o seguinte como construído [Dossiê §10.1, "Estado atual da implementação"]:

- Monorepo com pnpm workspaces e Turborepo, TypeScript e lint compartilhados.
- Docker Compose de desenvolvimento com PostgreSQL (pgvector), MongoDB, Redis, MinIO e Ollama.
- Scripts de inicialização que criam a extensão `vector` e os schemas `platform` e `rag`.
- **Migração baseline do `platform-api` via TypeORM com 18 tabelas** fiéis ao modelo relacional do Dossiê.
- Migração baseline do schema `rag` (Alembic) com a tabela de embeddings.
- Pacotes compartilhados (`config`, `api-contracts`, `ui`, `shared-types`) e guias de desenvolvimento e onboarding.
- `ai-sim-service` com "walking skeleton" validado: arquitetura hexagonal, motor de regras causais, **ingestão de telemetria com gate de consentimento embutido** (RF-071/RNF-009), HTTP versionado com erros RFC 7807 e métricas Prometheus, qualidade verde (ruff, mypy `--strict`, cobertura de 95%).

**Atenção.** Não se sabe, só por este briefing, quanto do código do `platform-api` já existe além da migração baseline. **Inspecione o repositório primeiro** (módulos, entidades, testes, CI) e parta do que estiver lá. Se houver código, reorganize só quando melhorar a base e diga isso no relatório.

---

# 2. Produto, atores e o que o backend precisa servir

ECOSFERA é um jogo educacional. Cada estudante cria e evolui um planeta e aprende ciências por causa e efeito. É alinhado à BNCC e apoiado por IA explicável. Atende estudantes do Fundamental II (cerca de 12 anos), do Ensino Médio e do técnico, além de professores, coordenação e responsáveis.

Cinco fatos que moldam o backend:

1. **Crianças e LGPD.** Dados de menor só são tratados com consentimento do responsável. Sem consentimento, não há coleta. É requisito legal bloqueante (RF-008, RNF-009, RSK-05).
2. **A IA informa; o professor decide** (RP-007). O backend entrega ao professor dados e alertas, nunca decisões automáticas sobre o aluno.
3. **Avaliação invisível** (RP-004). O estudante não vê nota. A avaliação é só do professor, via painel.
4. **Hardware e internet modestos** (RSK-10). O servidor não escala por aluno na parte de tempo real, porque o render e a simulação leve rodam no cliente (RNF-004). O backend deve ser sem estado e horizontal.
5. **Duas formas de implantar** com a mesma base de código: nuvem multi-tenant (SaaS) ou on-premise por escola (Docker Compose + Ollama local) [Dossiê §11].

## 2.1 Papéis (RBAC)

`aluno`, `professor`, `coordenador`, `admin`. Há ainda os atores `responsável` (consente pelo menor; não é um papel de login pleno no Dossiê, mas tem vínculo e consentimento), `pesquisador` (exporta dataset anonimizado, RF-078) e `serviço` (chamadas entre serviços, como o `ai-sim-service`). O Dossiê lista `pesquisador` e `serviço` na coluna "Auth" dos contratos. Como são tratados no modelo de papéis é decisão sua; registre em ADR.

## 2.2 Personas que o backend serve

| Persona | O que precisa do backend |
|---|---|
| Lucas (12, Chromebook) | Login simples; nada que dependa de rede perfeita |
| Sofia (16) | Ver e exportar séries do planeta (vêm do serviço de simulação, via gateway) |
| Marina (prof. de Ciências) | Criar missão BNCC em minutos; ver quem entendeu o quê |
| Rafael (prof. de Matemática) | Acessar e exportar séries numéricas (RF-021/066) |
| Beatriz (coordenadora) | Relatórios agregados por competência e cobertura BNCC entre turmas |
| Carlos (TI da escola) | Implantar com Docker; importar turmas via LTI |
| Helena (mãe) | Consentir de forma clara; ver finalidades |

## 2.3 Histórias de usuário que tocam o backend [Dossiê §11]

- **US-06** (professor): criar atividade ligada a uma habilidade BNCC em poucos minutos (RF-062/RP-001).
- **US-07**: acessar séries numéricas do planeta (RF-021/066).
- **US-08**: painel de domínio por competência e alertas (RF-063/064/077).
- **US-09** (coordenadora): relatórios agregados por competência alinhados à BNCC (RF-064/076).
- **US-10** (admin/TI): subir em contêineres e importar turmas via LTI (RT-006/007).
- **US-11** (responsável): ver finalidades claras e decidir sobre o consentimento (RF-008/RNF-009).
- **US-13** (pesquisador): exportar dataset anonimizado, sem PII (RF-078/RNF-011).
- **US-15** (professor): definir trilha EF/Médio/Técnico (RF-061/RP-002).
- **US-05** (aluno): continuar offline e sincronizar depois (RNF-021). O backend precisa aceitar a sincronização posterior (seção 4.4).

---

# 3. Arquitetura do `platform-api`

## 3.1 Decisões já tomadas (travadas) [Dossiê §2.1, §10.3, §12]

- **Node.js + NestJS + TypeScript.** Veio de uma migração Java/Spring Boot → Node/NestJS, porque a equipe agora é TypeScript-cêntrica. O NestJS preserva modularidade, injeção de dependência e organização hexagonal.
- **Monólito modular**, organizado por **DDD** com **arquitetura hexagonal** (portas e adaptadores) interna e **quatro bounded contexts**: `identity`, `education`, `assessment`, `orchestration`.
- **ORM: TypeORM.** Supera a recomendação anterior de Prisma, porque a baseline de 18 tabelas já está aplicada. **Atenção:** o backlog ainda fala em Prisma (TASK-0010/0011); o Dossiê v3 manda TypeORM.
- **Persistência poliglota** com dono por schema: `platform` é do `platform-api` (TypeORM); `rag` e MongoDB são do `ai-sim-service`. **Cada serviço é dono exclusivo do seu schema e das suas migrações.** O `platform-api` nunca escreve no schema `rag` nem no MongoDB.
- **Barramento de eventos escalonado:** Redis Streams no MVP; NATS a partir do Incremento 7 se o volume exigir. O backlog menciona NATS (TASK-0020); o Dossiê v3 prefere Redis Streams primeiro.
- **REST/JSON com OpenAPI 3.1** como contrato versionado e congelado em `packages/api-contracts`. Erros em **RFC 7807**. O backlog menciona tRPC e Zod compartilhados (TASK-0017); veja a divergência na seção 13.
- **WebSocket** para o stream de estado do planeta; **SSE** para o texto do tutor.
- **TLS** obrigatório, segredos em cofre, dados sensíveis cifrados em repouso.
- **Stateless e horizontal:** nenhum estado de sessão em memória do processo. Estado em PostgreSQL e Redis.
- **Trunk-Based Development** com branches curtas, Conventional Commits, PRs pequenos com CI verde e squash merge [Dossiê §8 da estratégia Git]. Nota prática: o fluxo atual do projeto parte da `develop` (seção 11).

## 3.2 Módulos do `platform-api` [Dossiê §2.1]

| Módulo | Responsabilidades | Tecnologias | Contexto |
|---|---|---|---|
| Autenticação (IAM) | Login, sessão, tokens, SSO/LTI | NestJS + Passport, JWT, OAuth2/OIDC | identity |
| Autorização (RBAC) | Permissões por papel (RF-004) | Guards e decorators do NestJS | identity |
| Usuários e perfis | CRUD, preferências, consentimento (RF-002/007/008/010) | TypeORM | identity |
| Turmas e trilhas | Turmas, vínculos, trilha por nível (RF-005/061) | NestJS, TypeORM | education |
| Missões e currículo (BNCC) | Desafios ancorados a habilidades (RF-062, RP-001) | NestJS | education |
| Painel do professor | Indicadores e relatórios (RF-063 a RF-067) | NestJS, WebSocket Gateway | assessment |
| Integração LMS (LTI) | Importar turmas, SSO (RF-009/RT-007) | Biblioteca LTI 1.3 (Node) | identity/orchestration |
| Administração | Escolas, tenants, configuração (RF-001) | NestJS | education |
| Orquestração/Gateway | Encaminha chamadas ao `ai-sim-service` | NestJS, cliente HTTP (undici/axios), Redis Streams | orchestration |

O backlog propõe nomes de módulos um pouco diferentes (`auth`, `academic`, `simulation-orchestration`, `teacher`, `files`, `events`, `realtime`). Os nomes de módulo e de pasta são decisão sua, desde que respeitem os quatro bounded contexts e a linguagem ubíqua.

## 3.3 Componentes internos [Dossiê §3.3]

- **AuthN/AuthZ:** provedor de identidade, emissor de JWT, avaliador RBAC, adaptador LTI.
- **Serviços de aplicação** (casos de uso do ERS): orquestram domínio e repositórios.
- **Agregador de dashboard:** compõe indicadores por competência e turma, assinando eventos de avaliação.
- **Adaptadores de saída:** repositórios (TypeORM), cliente do `ai-sim-service`, produtor e consumidor de eventos, armazenamento de objetos.

## 3.4 Decisões de arquitetura ainda em aberto (da memória do projeto)

- `tutoring` é um bounded context próprio ou parte de `orchestration`? [Dossiê §7.1 desenha "Tutoria/IA" como contexto, mas o `platform-api` só lista quatro.] **Padrão sugerido:** o `platform-api` não tem lógica de tutoria; só faz proxy autorizado. Fica em `orchestration`.
- Renomear a camada `interface/` para `presentation/` ou `api/`.
- Numeração de ADR: coexistem a série de projeto (`ADR-ARCH-`) e a série interna do `ai-sim-service`. O Dossiê recomenda unificar em `docs/adr/` ou prefixar por escopo (`PROJ-`, `AISIM-`). Siga a convenção que encontrar no repositório e prefixe com o escopo do `platform-api` se não houver.

---

# 4. Requisitos que o backend precisa atender

Prioridade MoSCoW: M = Must, S = Should, C = Could.

## 4.1 Cadastro, contas e gestão de acesso [Dossiê ERS §4.1]

| ID | Descrição | Prior. | Critério de aceitação | Dep. |
|---|---|---|---|---|
| RF-001 | Cadastrar instituição/escola | M | Escola criada com dados básicos; admin inicial gerado | — |
| RF-002 | Cadastrar e gerir usuários com papéis (aluno, professor, coordenador, admin) | M | Papel atribuído; permissões RBAC aplicadas por papel | RF-001 |
| RF-003 | Autenticar usuário (login) | M | Credencial válida concede sessão; inválida é negada **e registrada** | RF-002 |
| RF-004 | Autorizar ações por papel (RBAC) | M | Cada ação verifica permissão; acesso indevido bloqueado | RF-003 |
| RF-005 | Criar turmas e vincular alunos/professor | M | Turma com alunos e docente; aluno vê só sua(s) turma(s) | RF-002 |
| RF-006 | Recuperar/redefinir senha | S | Fluxo seguro de redefinição por e-mail ou admin | RF-003 |
| RF-007 | Cadastrar responsável e vincular a aluno menor | M | Vínculo responsável↔aluno registrado | RF-002 |
| RF-008 | Registrar **consentimento do responsável** (LGPD) no cadastro de menor | M | Sem consentimento válido, a conta do menor fica **restrita** | RF-007 |
| RF-009 | Integrar turmas via **LTI 1.3** (LMS) | S | Turma/alunos importados do LMS; SSO funcional | RF-005 |
| RF-010 | Gerir perfil e preferências (idioma, acessibilidade) | S | Preferências persistem e afetam a UI | RF-002 |

## 4.2 Painel do professor [Dossiê ERS §4.5]

| ID | Descrição | Prior. | Critério de aceitação | Dep. |
|---|---|---|---|---|
| RF-061 | Gerir turmas, alunos e trilhas (Fundamental/Médio/Técnico) | M | Professor administra sua turma e define a trilha | RF-005 |
| RF-062 | Criar/atribuir desafios ancorados a **objetivo BNCC** | M | Desafio vinculado a habilidade BNCC e a parâmetros | RF-022 |
| RF-063 | Acompanhar progresso individual e da turma (dashboard) | M | Painel mostra avanço, dificuldades e engajamento | RF-071 |
| RF-064 | Visualizar relatórios de aprendizagem (stealth assessment) | M | Relatório liga evidências a competências | RF-072 |
| RF-065 | Comparar planetas/decisões entre alunos | C | Visualização comparativa de estratégias e resultados | RF-063 |
| RF-066 | Exportar relatórios (PDF/CSV) | S | Exportação íntegra e legível | RF-064 |
| RF-067 | Enviar feedback/mensagens ao aluno | S | Aluno recebe e visualiza o retorno do professor | RF-063 |
| RF-068 | Gerir consentimento e privacidade da turma | M | Professor vê status de consentimento; respeita restrições | RF-008 |

## 4.3 Avaliação e aprendizagem (lado da plataforma) [Dossiê ERS §4.6]

O cálculo (RF-072, RF-073, rede bayesiana) é do `ai-sim-service`. O backend serve e projeta os resultados.

| ID | Descrição | Prior. | Papel do backend |
|---|---|---|---|
| RF-071 | Registrar learning analytics (telemetria) | M | A ingestão fica no `ai-sim-service`. O backend fornece o **gate de consentimento** (seção 9.3) e consome os eventos resultantes |
| RF-072/073 | Inferir competências; manter modelo do aluno | M/S | Não implementar. Receber `CompetênciaAtualizada` e projetar em `competency_estimate`/`cognitive_profile` |
| RF-074 | Integrar pré/pós-teste (opcional) | S | Vincular testes ao perfil do aluno (dado da plataforma) |
| RF-075 | Rubricas de pensamento científico e trade-offs | S | Registrar o resultado da rubrica quando vier do serviço |
| RF-076 | Mapear evidências → habilidades BNCC | M | Servir o mapeamento; manter a matriz `bncc_skill`/`competency` |
| RF-077 | Alertar professor sobre aluno em dificuldade | S | Alertas por limiar configurável, expostos ao painel |
| RF-078 | Exportar dataset anonimizado para pesquisa | C | Pipeline de anonimização, sem PII (RNF-011), com auditoria |

## 4.4 Requisitos técnicos relevantes [Dossiê §7.6]

| ID | Requisito | Prior. |
|---|---|---|
| RT-001 | Simulação híbrida cliente-servidor (cliente = render + sim leve; servidor = ciência/IA + persistência) | M |
| RT-002 | Separação plataforma × IA/ciência, com **contratos REST versionados** | M |
| RT-004 | Persistência poliglota (Postgres/Mongo/Redis; SQLite no modo local) | M |
| RT-005 | Tempo real por WebSocket para o estado do planeta | M |
| RT-006 | Empacotamento e implantação por contêineres (Docker Compose) | M |
| RT-007 | Integração LMS via **LTI 1.3** | S |
| RT-008 | Inferência de LLM local/on-premise habilitável | S |
| RT-010 | Observabilidade (métricas, latência, engajamento) | S |

**Sincronização offline (RNF-021)** [Dossiê §8.2]: ações e checkpoints locais são reconciliados ao reconectar, com estratégia *last-write-wins* por planeta, preservando a linha do tempo do aluno. O backend precisa de um ponto de entrada idempotente para receber essas ações. O formato fica para o contrato futuro; **[Proposta]** aceite uma chave de idempotência por ação.

## 4.5 Requisitos não funcionais relevantes [Dossiê §8.1]

| ID | Categoria | Requisito | Meta |
|---|---|---|---|
| RNF-002 | Desempenho | Latência de intervenção (ação→feedback) | ≤ 1 s (p95) para efeitos locais |
| RNF-003 | Desempenho | Explicação do tutor (LLM) | ≤ 5 s (p95), com streaming |
| RNF-004 | Escalabilidade | Simulação em tempo real na GPU do cliente | Servidor não escala por aluno nessa parte |
| RNF-005 | Escalabilidade | Turmas concorrentes | ≥ 40 alunos simultâneos por instância escolar sem degradação |
| RNF-006 | Segurança | Autenticação e RBAC por papel | Toda ação sensível autorizada; **testes de acesso indevido** |
| RNF-007 | Segurança | TLS e dados em repouso protegidos | HTTPS obrigatório; segredos em cofre |
| RNF-008 | Segurança | Proteção do LLM | Filtros de entrada e saída (lado do serviço de IA) |
| RNF-009 | Privacidade | **Consentimento do responsável** antes de tratar dados de menor | Sem consentimento → dados não coletados ou uso restrito |
| RNF-010 | Privacidade | **Minimização de dados** | Inventário de dados justificado por finalidade |
| RNF-011 | Privacidade | **Anonimização/pseudonimização** | Dataset de pesquisa sem PII (RF-078) |
| RNF-012 | Privacidade | Direitos do titular e retenção | Fluxos de acesso, correção e exclusão; política de retenção documentada |
| RNF-013 | Privacidade | Armazenamento seguro e **segregação por escola/turma** | Isolamento lógico; controle de acesso a dados pessoais |
| RNF-021 | Offline | Funcionamento parcial sem conexão | Sincronizar depois |
| RNF-024 | Manutenibilidade | Código modular, testado e documentado | Cobertura mínima definida; ADR para decisões |
| RNF-025 | Observabilidade | Métricas, logs e alertas | Painéis de saúde e de engajamento |
| RNF-026 | i18n | Arquitetura i18n (pt-BR base) | Strings externalizadas |

Os RNF-014 a RNF-020 (acessibilidade) são do cliente. O backend ajuda guardando as preferências (RF-010) e servindo mensagens de erro claras.

## 4.6 Requisitos pedagógicos que afetam o backend [Dossiê §5.4]

- **RP-001:** toda atividade é ancorável a pelo menos uma habilidade BNCC pelo professor (a missão exige selecionar habilidade).
- **RP-002:** trilhas diferenciadas por nível (EF II, Médio, Técnico).
- **RP-004:** avaliação embutida, sem interromper o jogo.
- **RP-006:** conteúdo apropriado à idade (o filtro é do serviço de IA; o backend só repassa).
- **RP-007:** preservar o papel mediador do professor.

---

# 5. Contratos de API

Esta é a base do contrato real do backend. Diferente do frontend, **o backend precisa definir os contratos**: parta daqui, formalize em OpenAPI 3.1 em `packages/api-contracts` e valide por testes de contrato. O contrato congelado ali é a fonte de verdade.

## 5.1 Convenções [Dossiê §5]

- **Base:** `/{service}/api/v1`. **Auth:** `Authorization: Bearer <JWT>`. JSON em UTF-8.
- **Erros** no formato **RFC 7807 (Problem Details)**:

```json
{ "type": "/errors/validation", "title": "Dados inválidos", "status": 422,
  "detail": "massa fora da faixa permitida", "instance": "/planets", "traceId": "..." }
```

- **Códigos comuns:** 200 OK, 201 Created, 202 Accepted (job assíncrono), 204 No Content, 400/422 (validação), 401 (não autenticado), 403 (sem permissão), 404, 409 (conflito), 429 (limite), 5xx.

## 5.2 Autenticação

| Método | URL | Descrição | Auth | Request | Response | Códigos |
|---|---|---|---|---|---|---|
| POST | `/auth/login` | Autentica e emite JWT | — | `{email, senha}` | `{accessToken, refreshToken, perfil}` | 200/401 |
| POST | `/auth/refresh` | Renova token | refresh | `{refreshToken}` | `{accessToken}` | 200/401 |
| POST | `/auth/lti/launch` | SSO via LTI 1.3 | LTI | claims LTI | `{accessToken, turma}` | 200/401 |
| POST | `/auth/logout` | Encerra sessão | Bearer | — | 204 | 204 |

Erros do login: 401 credenciais inválidas; 429 tentativas excessivas. O backlog (TASK-0026) pede: JWT de vida curta, **refresh rotativo em cookie httpOnly**, **revogação em Redis**.

## 5.3 Usuários e consentimento

| Método | URL | Descrição | Auth | Códigos |
|---|---|---|---|---|
| POST | `/users` | Cria usuário (papel) | admin/prof | 201/409 |
| GET | `/users/{id}` | Perfil | dono/prof/admin | 200/403/404 |
| PATCH | `/users/{id}/preferences` | Acessibilidade e idioma (RF-010) | dono | 200 |
| POST | `/users/{id}/consent` | Registra consentimento do responsável (RF-008) | responsável | 201 |
| GET | `/users/{id}/consent` | Status LGPD | prof/admin | 200 |

## 5.4 Turmas, trilhas e missões

| Método | URL | Descrição | Auth | Códigos |
|---|---|---|---|---|
| POST | `/classes` | Cria turma | prof | 201 |
| POST | `/classes/{id}/students` | Vincula alunos | prof | 200 |
| PATCH | `/classes/{id}/track` | Define trilha (EF/Médio/Técnico) | prof | 200 |
| POST | `/missions` | Cria missão ancorada à BNCC (RF-062) | prof | 201/422 |
| GET | `/missions?classId=` | Lista missões da turma | prof/aluno | 200 |

## 5.5 Planetas e simulação (o backend é gateway)

O cliente fala só com o `platform-api`. O `platform-api` **autentica, autoriza (posse), registra e encaminha** ao serviço de simulação pela porta. A resposta volta composta. O backend **não** calcula o estado do planeta.

| Método | URL | Descrição | Auth | Request | Response | Códigos |
|---|---|---|---|---|---|---|
| POST | `/planets` | Cria planeta (RF-011) | aluno | `{params, seed?, missionId?}` | `{planetId, state}` | 201/422 |
| GET | `/planets/{id}` | Estado atual | dono/prof | — | `{state, era, indicators}` | 200 |
| POST | `/planets/{id}/validate` | Valida parâmetros (RF-012) | aluno | `{params}` | `{ok, warnings[]}` | 200 |
| POST | `/planets/{id}/tick` | Avança tempo (RF-013) | aluno | `{steps, speed}` | 202 `{jobId}` ou `{delta}` | 200/202 |
| POST | `/planets/{id}/interventions` | Aplica intervenção/trade-off (RF-017/018) | aluno | `{action, target, cost}` | `{delta, tradeoffs, actionPoints}` | 200/409 |
| GET | `/planets/{id}/timeline` | Linha do tempo e checkpoints (RF-015/016) | dono/prof | — | `{eras[], checkpoints[]}` | 200 |
| POST | `/planets/{id}/checkpoints` | Salva checkpoint (RF-015) | aluno | — | 201 `{checkpointId}` | 201 |
| GET | `/planets/{id}/series?metric=` | Séries temporais (RF-021) | dono/prof | — | `{points[]}` | 200 |

Exemplo de intervenção: request `{"action":"INDUSTRIALIZE","target":"region-7","cost":{"actionPoints":2,"energy":10}}`; response `{"delta":{...},"tradeoffs":[{"gain":"prosperity+","cost":"co2+, temp+"}],"actionPoints":{"remaining":3}}`. Erros: 409 pontos insuficientes; 404 planeta; 403 não é dono.

**Eventos do planeta:**

| Método | URL | Descrição | Auth | Códigos |
|---|---|---|---|---|
| GET | `/planets/{id}/events` | Histórico de eventos | dono/prof | 200 |
| POST | `/planets/{id}/events/respond` | Responde a evento em curso | aluno | 200 |

**Regras de posse:** o aluno só acessa **o próprio** planeta; professor acessa planetas dos alunos das suas turmas; admin conforme tenant. Aplique no gateway e no domínio (defesa em profundidade).

## 5.6 IA (proxy autorizado)

O backend apenas autoriza e repassa. Não implementa tutor.

| Método | URL | Descrição | Auth | Request | Response | Códigos |
|---|---|---|---|---|---|---|
| POST | `/ai/explain` | Explicação causal (RF-033/039) | aluno | `{planetId, contextRef, question?}` | SSE stream de texto | 200 |
| POST | `/ai/hint` | Dica personalizada (RF-035) | aluno | `{planetId, missionId}` | `{hint, level}` | 200 |
| POST | `/ai/advisor` | Conselheiro-agente (RF-036) | aluno | `{role, query}` | `{advice}` | 200 |
| GET | `/ai/adaptation/{studentId}` | Parâmetros adaptativos | plataforma | — | `{difficulty, unlocks[]}` | 200 |

O repasse do SSE precisa preservar o streaming (RNF-003: ≤ 5 s p95, com texto em fluxo).

## 5.7 Avaliação e stealth assessment (lado de leitura)

| Método | URL | Descrição | Auth | Códigos |
|---|---|---|---|---|
| POST | `/assessment/events` | Ingesta de telemetria/evidência (RF-071) | serviço | 202 |
| GET | `/assessment/students/{id}/profile` | Perfil cognitivo por competência (RF-072/073) | prof/dono | 200 |
| GET | `/assessment/students/{id}/evidence` | Evidências rastreáveis (RF-076) | prof | 200 |
| GET | `/assessment/students/{id}/bncc` | Domínio mapeado à BNCC | prof/coord | 200 |

Observação: no desenho atual a ingestão de telemetria está implementada no `ai-sim-service`, com o gate de consentimento embutido. Veja a seção 9.3 sobre o que o `platform-api` oferece a ela.

## 5.8 Painel do professor e coordenação

| Método | URL | Descrição | Auth | Códigos |
|---|---|---|---|---|
| GET | `/dashboard/classes/{id}/overview` | Visão de turma (RF-063) | prof | 200 |
| GET | `/dashboard/classes/{id}/competencies` | Progresso por competência | prof/coord | 200 |
| GET | `/dashboard/classes/{id}/alerts` | Alertas de dificuldade (RF-077) | prof | 200 |
| POST | `/dashboard/students/{id}/feedback` | Envia feedback ao aluno (RF-067) | prof | 201 |
| GET | `/dashboard/reports/export?format=pdf\|csv` | Exporta relatório (RF-066) | prof/coord | 200 |
| GET | `/research/dataset?anonymized=true` | Dataset anonimizado (RF-078) | pesquisador | 200 |

## 5.9 Tempo real (WebSocket)

- `ws://.../planets/{id}/stream`: deltas de estado por tick, eventos e notificações (RF-021/052/056).
- Mensagens tipadas: `{ type: "delta" | "event" | "tutor" | "alert", payload: {...}, tickId }`.
- **Autenticação no handshake** (JWT). **Fan-out via Redis pub/sub.** O backlog (TASK-0022) pede reconexão tratada, entrega por sessão, backpressure e um teste de carga básico.

## 5.10 Mecanismos de comunicação [Dossiê §4]

| Interação | Mecanismo | Sínc./Assínc. |
|---|---|---|
| Cliente ↔ plataforma (ações, CRUD, auth) | REST/JSON | Síncrono |
| Stream de estado do planeta | WebSocket | Assíncrono |
| Explicação do tutor | SSE (ou WS) | Assíncrono |
| Plataforma ↔ IA/Sim | REST interno (leve) + fila (pesado) | Misto |
| Eventos de domínio | Pub/sub (Redis Streams; NATS depois) | Assíncrono (EDA) |
| Cache e fan-out de WebSocket | Redis | — |

**Princípio:** síncrono onde o usuário espera a resposta (login, criar planeta, aplicar ação); assíncrono onde o trabalho é pesado ou tem vários interessados (evolução, LLM, stealth, dashboard).

---

# 6. Modelo de dados

## 6.1 Modelo conceitual [Dossiê §6.1]

```
Escola 1───N Usuario ──(Papel: Aluno|Professor|Coordenador|Admin)
Usuario(menor) 1───1 Consentimento N───1 Responsavel
Professor 1───N Turma 1───1 Trilha ; Turma N───N Aluno (Matricula)
Aluno 1───N Planeta ; Planeta N───1 Missao (opcional)
Missao N───N HabilidadeBNCC N───1 Competencia
Planeta 1───N Estado(Era) ; Planeta 1───N Checkpoint       (lado simulação)
Aluno 1───N Sessao 1───N Evidencia
Evidencia N───1 EventoDoJogo ; Evidencia N───1 Competencia
Aluno 1───1 PerfilCognitivo 1───N EstimativaCompetencia
Avaliacao 1───N Evidencia ; Aluno 1───N Feedback
```

Uma turma pertence a um professor e adota uma trilha. Alunos entram por matrícula (N:N). Cada aluno cria planetas. Um planeta pode estar ligado a uma missão, que referencia habilidades BNCC, cada uma sob uma competência. A jogabilidade gera evidências (por sessão), ligadas a eventos do jogo e a competências. O motor de stealth mantém o perfil cognitivo (uma estimativa por competência). Avaliação agrega evidências e feedback é dirigido ao aluno.

## 6.2 Modelo lógico no PostgreSQL, schema `platform` [Dossiê §6.2]

Tabelas citadas: `school`, `user` (com `role`), `guardian`, `consent`, `class`, `enrollment`, `track`, `mission`, `mission_bncc`, `bncc_skill`, `competency`, `cognitive_profile`, `competency_estimate`, `evidence` (estruturada), `assessment`, `feedback`, `planet_meta` (`id`, `owner`, `current_era`, `seed`, `mission_id`), `audit_log`.

**[Inferência]** São 18 nomes, o que bate com a baseline de 18 tabelas já aplicada (e `embedding` fica no schema `rag`). **Confirme na migração existente** e trate a migração como a verdade sobre colunas e tipos. Novas necessidades (por exemplo, tokens de refresh, redefinição de senha, identidades externas OIDC/LTI, plataformas LTI registradas, mensagens de feedback do professor, alertas, registros de exportação, retenção) entram por **novas migrações**, nunca editando a baseline.

## 6.3 Onde cada dado mora [Dossiê §6.3 e §9]

| Dado | Store | Dono | Observação |
|---|---|---|---|
| Usuários, turmas, matrículas, missões BNCC, avaliação (projeção), consentimento, auditoria | PostgreSQL schema `platform` | `platform-api` (TypeORM) | Sistema de registro; ACID |
| Vetores e metadados do RAG | PostgreSQL schema `rag` | `ai-sim-service` (Alembic) | **O backend não toca** |
| Estado do planeta, espécies, ecossistemas, log de eventos, telemetria bruta | MongoDB | `ai-sim-service` | **O backend não toca** |
| Cache, sessões, pub/sub de WebSocket, Redis Streams, contadores efêmeros | Redis | Compartilhado | Chaves: `session:{id}`, `action_points:{planetId}`, canais pub/sub, filas |
| Exportações (PDF/CSV), dumps de dataset, assets | MinIO/S3 | `platform-api` | URLs assinadas, validação de tipo e tamanho |
| Estado local offline | SQLite/IndexedDB | Cliente | Fora desta tarefa |

Cada serviço é dono exclusivo do seu schema e das suas migrações: isso elimina conflito entre TypeORM e Alembic. **Em produção, use roles de banco restritas por schema.** A extensão `vector` e os schemas são criados na inicialização do banco; as tabelas moram só nas migrações, versionadas e reexecutáveis. Parâmetro fixado: a dimensão do vetor é 768 (all-mpnet-base-v2); isso é do schema `rag`, só para você saber.

## 6.4 Projeção da avaliação [Proposta]

As tabelas `evidence`, `competency_estimate`, `cognitive_profile` e `assessment` estão no schema `platform`, mas o cálculo é do `ai-sim-service`. **[Proposta]** O `platform-api` consome os eventos `EvidênciaGerada` e `CompetênciaAtualizada` (Redis Streams) e **projeta** em Postgres como modelo de leitura, de forma idempotente (chave natural ou id de evento). Com isso, o painel funciona e é testável sem o serviço de IA. Registre a decisão em ADR.

---

# 7. Modelo de domínio (DDD)

## 7.1 Bounded contexts [Dossiê §7.1 e §2.1]

- **identity:** IAM, RBAC, usuários, consentimento, LGPD, LTI/OIDC.
- **education:** escolas, turmas, trilhas, missões, currículo BNCC, administração.
- **assessment:** perfil cognitivo, competência, evidência, painel (principalmente leitura).
- **orchestration:** gateway e cliente do `ai-sim-service`, produtor e consumidor de eventos, tempo real.

(O Dossiê desenha ainda "Simulação" e "Tutoria/IA" como contextos do sistema; eles pertencem ao `ai-sim-service`.)

## 7.2 Agregados do backend [Dossiê §7.2]

- **`Usuário`** (raiz): `Papel`, `Consentimento`; VO `Preferências`.
- **`Turma`** (raiz): `Matrícula`, `Trilha`; VO `Nível`.
- **`Missão`** (raiz): vínculos com `HabilidadeBNCC`; VO `HabilidadeBNCC(código)`, `ObjetivoPedagógico`.
- **`PerfilCognitivo`** (raiz): `EstimativaCompetência`; VO `CompetênciaScore(valor, incerteza)`. No backend é um modelo de leitura.
- **`Planeta`** é raiz **do domínio de simulação** (fora). No backend existe só `planet_meta` (dono, era atual, seed, missão) como referência para autorização e vínculo.

## 7.3 Eventos de domínio [Dossiê §7.4]

`PlanetaCriado`, `EraAvançada`, `IntervençãoAplicada`, `EventoOcorreu`, `EvidênciaGerada`, `CompetênciaAtualizada`, `MissãoConcluída`. São o contrato assíncrono entre simulação, avaliação e dashboard. O backend **publica** os que nascem nele (por exemplo, criação de planeta e intervenção autorizada, quando passam pelo gateway) e **consome** os que vêm do serviço. **Linguagem ubíqua:** Planeta, Espécie, Trade-off, Competência, Evidência, Missão, PerfilCognitivo. Use os nomes do domínio em português no modelo e no vocabulário dos módulos, como nos artefatos pedagógicos.

---

# 8. Segurança e LGPD (checklist)

Segurança em profundidade, atendendo RNF-006 a RNF-013 [Dossiê §10].

## 8.1 Autenticação

- JWT de vida curta + refresh token. Refresh rotativo, com revogação (Redis). **[Proposta]** guardar refresh em cookie `httpOnly`, `Secure`, `SameSite` adequado, como pede o backlog.
- OAuth2/OIDC para provedores externos (Keycloak ou Ory, TASK-0028). LTI 1.3 para SSO via LMS, com mapeamento de papéis.
- Senhas com hash forte: **Argon2** ou bcrypt. **Nunca** pedir ou guardar credenciais de terceiros em texto.
- Login inválido é negado e **registrado** (RF-003). Rate limiting nos endpoints de auth (429).
- Redefinição de senha segura (RF-006), sem revelar se o e-mail existe.

## 8.2 Autorização

- RBAC por papel (aluno/professor/coordenador/admin) **mais verificação de posse**. O aluno só acessa o próprio planeta e os próprios dados.
- Aplicada no gateway (guards) **e** no domínio. Um guard sozinho não basta.
- **Segregação por escola e turma** (RNF-013): toda consulta filtra pelo tenant. Teste explicitamente o vazamento entre escolas.
- Testes de acesso indevido por papel e por tenant são requisito (RNF-006).

## 8.3 Criptografia e segredos

- TLS em trânsito. Dados sensíveis cifrados em repouso. Segredos em cofre e **nunca** no repositório. Configuração validada no boot (TASK-0004, Zod), com erro claro se faltar variável.
- Imagens Docker com usuário não-root e healthcheck (TASK-0003).

## 8.4 LGPD

| Tema | Regra | Fonte |
|---|---|---|
| Consentimento | **Bloqueante.** Sem consentimento válido do responsável, a conta do menor fica restrita e dados pessoais não são coletados nem processados. Aceite registrado e auditável. **Revogação suportada.** | RF-007/008, RNF-009 |
| Minimização | Coletar só o necessário à finalidade pedagógica. Manter um inventário de dados com a finalidade de cada campo | RNF-010 |
| Anonimização | Dataset de pesquisa sem PII. Pipeline remove identificadores antes da exportação | RNF-011, RF-078 |
| Retenção e direitos do titular | Política de retenção documentada. Fluxos de acesso, correção e exclusão. DPO designado | RNF-012 |
| Segregação | Isolamento lógico multi-tenant | RNF-013 |

## 8.5 Auditoria, logs e abuso

- `audit_log` **imutável** para ações sensíveis: consentimento, exportações, mudanças de permissão. Garanta a imutabilidade de verdade (por exemplo, sem UPDATE/DELETE para a role da aplicação) e teste isso.
- Logs estruturados, correlacionados por `traceId` (o mesmo `traceId` aparece nos erros RFC 7807).
- Rate limiting, CORS restrito, validação e sanitização em todas as bordas (TASK-0030).
- Nada de PII em logs, em URLs ou em mensagens de erro.
- **Proteção da IA:** o backend redige PII antes de enviar contexto ao serviço de IA e trata o conteúdo recebido como dado, não como instrução [Dossiê §10, "Proteção da IA"]. Aplique a parte que cabe ao gateway.

## 8.6 Riscos relevantes [Dossiê §14]

| ID | Risco | Mitigação que cabe ao backend |
|---|---|---|
| RSK-04 | Conteúdo impróprio para menores | Auditoria; repassar só pelo gateway autorizado |
| RSK-05 | Não conformidade LGPD (consentimento, retenção) | Consentimento no cadastro; minimização; anonimização; DPO |
| RSK-06 | Códigos/habilidades BNCC incorretos | A matriz BNCC é **dado versionado e revisável por especialista**, não código fixo |
| RSK-07 | Escopo excessivo | Monólito modular; sem microsserviços prematuros; MoSCoW rígido |
| RSK-11 | Viés algorítmico na avaliação | O backend expõe só o que o serviço calcula, com rastreabilidade (RF-076) |

---

# 9. Integrações: portas e fakes

O `ai-sim-service` (Python/FastAPI) existe como "walking skeleton", mas o planeta e o tick ainda não estão disponíveis como serviço. O backend define **portas** e entrega **fakes** determinísticos, para o gateway, o painel e os testes funcionarem sem ele.

## 9.1 Portas sugeridas [Proposta]

| Porta | Função | Adaptador real (futuro) | Fake (agora) |
|---|---|---|---|
| `SimulationGateway` | Criar planeta, validar parâmetros, tick, intervenção, séries, timeline, checkpoints, eventos | Cliente HTTP (undici/axios) + Redis Streams ao `ai-sim-service` | Estado em memória, determinístico por `seed` |
| `TutorGateway` | `explain` (SSE), `hint`, `advisor`, `adaptation` | Idem | Respostas fixas, marcadas como simuladas |
| `AssessmentEventSource` | Receber `EvidênciaGerada` e `CompetênciaAtualizada` | Consumidor de Redis Streams | Gerador sintético que alimenta a projeção |
| `EventPublisher` | Publicar eventos de domínio | Redis Streams (NATS depois) | Em memória, para teste |
| `ObjectStorage` | Upload/download, URLs assinadas | MinIO/S3 | Sistema de arquivos temporário ou MinIO do compose |
| `IdentityProvider` | OIDC/LTI | Keycloak/Ory + biblioteca LTI 1.3 | Provedor de teste local |
| `Clock`, `IdGenerator` | Testabilidade | Reais | Controláveis em teste |

Os fakes têm de ser claramente identificáveis (nome, log e flag de configuração), nunca ligados em produção por acidente.

## 9.2 Regras do gateway

- O gateway autentica, autoriza a posse, **registra** a ação (para auditoria e eventos) e só então chama a porta.
- Trabalho leve: REST síncrono. Trabalho pesado (tick longo, LLM): `202 Accepted` com `jobId`, resultado por WebSocket.
- Resposta composta: o backend junta o retorno do serviço com o que é dele (por exemplo, pontos de ação, se o backend for o dono desse contador; veja abaixo).
- Falha da porta é erro tratado (RFC 7807), com timeout e degradação graciosa. Nada de 500 genérico.

**Pontos de ação (`action_points:{planetId}` no Redis).** O Dossiê cita a chave e o campo `actionPoints` na resposta da intervenção, mas não diz quem é o dono da regra de economia. **[Proposta]** O `ai-sim-service` é autoritativo sobre o efeito das intervenções e sobre a economia. O gateway só repassa e valida o formato. Registre em ADR e confirme com a equipe de simulação.

## 9.3 Gate de consentimento para outros serviços [Proposta]

O `ai-sim-service` já bloqueia a coleta de telemetria sem consentimento. Para isso, ele precisa consultar o estado de consentimento, que é dado do `platform-api`. **[Proposta]** exponha um endpoint interno, autenticado por credencial de serviço, que responde se um usuário tem consentimento válido e para qual finalidade (por exemplo, `GET /internal/consent/{userId}`), mais um evento `ConsentimentoRevogado` para que os outros serviços parem de coletar. Mantenha a resposta mínima, sem PII. Autentique serviço a serviço com credencial própria (por exemplo, JWT de serviço assinado ou mTLS); registre a escolha em ADR.

---

# 10. Estado atual, marcos e decisões registradas

## 10.1 Marcos [Dossiê §10.2]

| Marco | Comprovação exigida | Release |
|---|---|---|
| M0 Fundação | Monorepo, CI/CD, **autenticação** e ambiente de ponta a ponta | v0.1 |
| M1 MVP jogável | Ciclo completo: criar planeta, clima, vida básica, salvar, com feedback causal | v0.2 |
| M2 Validação pedagógica | Playtest | v0.2 |
| M3 Mundo vivo | Motor ambiental, ecossistemas, eventos, trade-offs | v0.3 |
| M4 Inteligência ativa | Tutor LLM+RAG ancorado, com guardrails | v0.5 |
| M5 Avaliação invisível | Stealth assessment mapeado à BNCC | v0.5 |
| M6 Valor para o professor | Docente cria missão BNCC e acompanha a turma sem assistência | v1.0 |
| M7 Pronto para piloto | Acessibilidade, PWA/offline, **LGPD**, desempenho e **segurança** nas metas | v1.0 |
| M8 Piloto validado | Uso real em turma, com dados de aprendizagem | pós-v1.0 |

Esta frente do backend cobre o M0 por inteiro e boa parte do M6 e do M7 (LGPD e segurança), e dá a base de autorização para os demais.

## 10.2 Decisões registradas (ADRs e tabela de decisões) [Dossiê §10.3]

| Decisão | Justificativa |
|---|---|
| Migração Java/Spring → Node.js/NestJS | Equipe TypeScript-cêntrica |
| Persistência poliglota (Postgres + Mongo + Redis) | Naturezas de dados distintas |
| Separação por schema (`platform` / `rag`) | Isolar migrações de TypeORM e Alembic sem segundo servidor |
| Feedback causal por regras antes do LLM | Hipótese pedagógica testável no MVP |
| Barramento escalonado (Redis Streams → NATS) | Evitar infraestrutura nova antes da necessidade medida |
| TypeORM (supera Prisma) | Estado real do código; baseline de 18 tabelas aplicada |
| Arquitetura de Engines (ADR-ARCH-0001) e Observabilidade por Design (ADR-ARCH-0002) | Do `ai-sim-service`; só contexto |

Escreva os ADRs do backend em **português**. Siga a convenção de ADR que já existir no repositório.

## 10.3 Observabilidade [Dossiê §10.5 e RNF-025]

Instrumente o backend com OpenTelemetry e métricas Prometheus (latência, erros, filas), e logs estruturados com `traceId`. O traço deve atravessar `platform-api` → `ai-sim-service` (TASK-0008). Métricas pedagógicas (engajamento, conclusão) vêm dos eventos, não de logs.

---

# 11. Git, CI, testes e definição de pronto

## 11.1 Git

- Repositório: `https://github.com/gustavo-rm/ecosfera-project`. **A branch do backend deve sair da `develop`.**
- Branches curtas, Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`), PRs pequenos ligados ao RF/US, squash merge, CI verde obrigatória, ao menos um revisor. Revisão pedagógica quando a mudança tocar avaliação ou conteúdo.
- Convenção do projeto: commits, PRs e nomes de branch em **inglês**; ADRs e documentação em **português**.

## 11.2 CI/CD (GitHub Actions) [Dossiê §9 da estratégia de CI]

| Estágio | TypeScript (back) |
|---|---|
| Lint/estático | ESLint, Prettier, `tsc` |
| Testes | Vitest (ou Jest, conforme o repositório) + Testcontainers |
| Cobertura | c8/istanbul, com **limiar** que barra o PR se cair |
| Análise | SonarQube CE: PR barrado com bugs ou vulnerabilidades novas |
| Build | Imagem Docker multi-stage |
| Deploy | Staging automático no merge; produção com aprovação manual |

Observabilidade publicada junto ao deploy.

## 11.3 Pirâmide de testes [Dossiê §10 da estratégia de testes]

| Tipo | O que cobre | Obrigatório desde |
|---|---|---|
| Unitários | Regras de domínio, funções puras | Sempre |
| Integração | Serviço ↔ banco/fila (Testcontainers para Postgres, Redis; Mongo só se necessário) | Inc 1 |
| API/Contrato | Conformidade com o OpenAPI de `packages/api-contracts` | Inc 1 |
| E2E | Fluxos completos | Inc 3 |
| Segurança | Dependências, SAST, testes de authz por papel e tenant | Antes do piloto (TASK-0076) |
| Desempenho | Latência p95 com k6; ≥ 40 alunos simultâneos (RNF-005) | Inc 1 em diante |

Regra: todo incremento entrega testes proporcionais ao seu risco.

## 11.4 Definition of Done (geral) [Dossiê §11]

- Código revisado e integrado; testes unitários e de integração verdes; cobertura ≥ limiar.
- Análise estática sem novos bugs ou vulnerabilidades.
- Telemetria instrumentada quando gerar evidência.
- Documentação e ADR atualizados.
- Implantado em staging e demonstrável.

DoD do backlog para tarefas de backend: "Código revisado (PR aprovado); testes automatizados passando; cobertura >= limiar; análise estática sem erros novos; documentação atualizada; deploy em staging".

---

# 12. Backlog: tarefas do backend para a matriz de cobertura

Use estas tarefas como **lista de verificação**, não como plano rígido. As dependências do CSV têm inconsistências (por exemplo, TASK-0026 listada como bloqueada por TASK-0015, que trata de pgvector). Siga a lógica dos requisitos. O CSV é grande: filtre por `Repositório: apps/api` ou pelos épicos Backend, APIs, Segurança e Banco de Dados com script ou `grep`.

| Tarefa | Resumo | Observação para o backend |
|---|---|---|
| TASK-0010/0011/0012 | Schema inicial, pipeline de migrações, índices | O backlog diz Prisma. **Use TypeORM** (baseline já existe). Migrações com verificação de drift no CI; índices para turma por escola e evidência por aluno/competência |
| TASK-0014 | Redis (cache, sessões, streams) | Cache com TTL, sessões/refresh em Redis, stream publicando e consumindo |
| TASK-0016 | Bootstrap NestJS | Módulos, `/health`, logs estruturados |
| TASK-0017 | tRPC + Zod em shared | Veja divergência (seção 13) |
| TASK-0018 | CRUD acadêmico | Escolas, turmas, matrículas (RF-001/005) com RBAC |
| TASK-0019 | Orquestração de simulação | Autoriza, registra, encaminha ao serviço, compõe a resposta. Job pesado por fila |
| TASK-0020 | Mensageria | O backlog diz NATS; Dossiê prefere Redis Streams no MVP. Reprocessamento em falha; contratos de mensagem em `api-contracts` |
| TASK-0021 | Arquivos (MinIO/S3) | Upload/download, URLs assinadas, validação, limites configuráveis |
| TASK-0022 | WebSocket gateway | Autenticado, deltas por sessão, reconexão, backpressure, teste de carga |
| TASK-0023 | OpenAPI 3.1 | Contratos versionados e clientes gerados |
| TASK-0024 | Endpoints de planeta e tick | Criar, configurar, tick (RF-011/012/013) pelo gateway |
| TASK-0025 | Testes de contrato | Quebra de contrato falha o CI |
| TASK-0026 | JWT + refresh | Refresh rotativo em cookie httpOnly, revogação em Redis (RF-003) |
| TASK-0027 | RBAC por guards | Testes por papel (RF-004) |
| TASK-0028 | OIDC/LTI 1.3 | Keycloak/Ory; mapeamento de papéis (RF-009) |
| TASK-0029 | Consentimento bloqueante | Sem consentimento não há coleta; aceite auditável; revogação (RF-008) |
| TASK-0030 | Rate limiting, CORS, auditoria | Validação em todas as bordas |
| TASK-0004 | Configuração e segredos | Validação no boot |
| TASK-0003/0005/0006 | Dockerfile, CI, CD | Só a parte do `platform-api`; o resto da infra é de outra frente |
| TASK-0063/0064/0065 | Dashboards, missões BNCC, relatórios | **Só o lado servidor** (endpoints, agregação, exportação). A UI é do frontend |
| TASK-0071/0072/0076 | Frameworks de teste, Testcontainers, segurança | Lado do `platform-api` |
| TASK-0080 | Documentação de API | OpenAPI navegável, sincronizada no CI |
| TASK-0008/0009 | Observabilidade, backup | Instrumentação do `platform-api`; backup é de infra |
| TASK-0078 | ADRs | Escreva os do backend |

Tarefas de simulação, IA, algoritmo genético, ABM, eventos de simulação, tutor, analytics, bayesiano e gráficos **não** fazem parte desta frente.

---

# 13. Divergências conhecidas (registre; não esconda)

| # | Onde | O que diverge | Leitura sugerida |
|---|---|---|---|
| 1 | Dossiê (partes antigas) × v3 | Ainda cita Java/Spring, "JPA", "plataforma (Java)" em tabelas e textos | Superado por NestJS/TypeORM. Trate "Java" como "plataforma" |
| 2 | Backlog × Dossiê v3 | Backlog usa **Prisma** (TASK-0010/0011/0018/0029) | **TypeORM**; a baseline já está aplicada |
| 3 | Backlog × Dossiê v3 | Backlog usa **NATS**; Dossiê prefere **Redis Streams** no MVP e NATS só no Inc 7 | Redis Streams atrás de uma porta, trocável por NATS |
| 4 | Backlog × Dossiê | Backlog usa **tRPC + Zod** como contrato interno e OpenAPI só para integrações externas; Dossiê define **REST/OpenAPI** como contrato congelado | O contrato congelado em `api-contracts` é o OpenAPI. Use Zod (ou similar) para validar as bordas. tRPC só se a equipe confirmar. **Decisão em aberto: peça aprovação ou registre em ADR** |
| 5 | Backlog × Dossiê | Backlog cita **Socket.IO**; Dossiê descreve WebSocket com mensagens tipadas | Prefira WebSocket nativo; decisão sua, registrada em ADR |
| 6 | Nomes de pastas | `apps/platform-api` × `apps/api`; `packages/api-contracts` × `packages/shared`; `services/ai-sim-service` × `services/ai` | Descubra os reais no repositório |
| 7 | Dossiê (ERS) | O contrato `POST /assessment/events` está na API da plataforma, mas a ingestão (com gate de consentimento) está no `ai-sim-service` | Veja seção 9.3 |
| 8 | Dossiê (ERS) | "Pesquisador" e "serviço" aparecem como papéis de autenticação, mas o RBAC do RF-002 tem 4 papéis | Decida o modelo e registre em ADR |
| 9 | Backlog | Dependências cruzadas inconsistentes | Siga os requisitos |
| 10 | Memória do projeto | `tutoring` próprio ou dentro de `orchestration`; nome da camada `interface/`; numeração de ADR | Seção 3.4 |

Em conflito que **muda de forma material** a arquitetura, a segurança ou a LGPD, trate como bloqueio de verdade: registre, deixe o item de lado e continue com o que for independente.

---

# 14. Referência rápida de BNCC e competências (para a matriz curricular)

A matriz é o **contrato entre pedagogia e engenharia** [Dossiê, Modelo pedagógico §5]. Os códigos abaixo vêm do Dossiê §5.3 e servem para inicializar o catálogo (`bncc_skill`, `competency`). **Eles precisam de validação por especialista antes de ir a estudantes (RSK-06)**; trate-os como dado versionado, revisável sem novo deploy do código, e nunca como constante no código.

## 14.1 Competências do modelo pedagógico

Pensamento científico (CG2); Causa-efeito (CG2); Pensamento sistêmico; Tomada de decisão (CG7); Análise de consequências; Letramento de dados (CG5); Evolução (Biologia); Persistência; Criatividade; Argumentação (CG7).

## 14.2 Habilidades BNCC citadas na matriz funcionalidade ↔ BNCC

| Tema | Componente | Competências Gerais | Códigos |
|---|---|---|---|
| Criar planeta / zona habitável | Ciências (Astronomia) | CG2 | EF09CI16; EF09CI14; EM13CNT201/202 |
| Estrutura da Terra e geologia | Ciências | CG2 | EF06CI11 |
| Órbita, estações, dia/noite | Ciências | CG2 | EF06CI14; EF09CI17 |
| Atmosfera e efeito estufa | Ciências (Química/Física) | CG2, CG10 | EF07CI13; EF07CI12 |
| Camada de ozônio | Ciências | CG2 | EF07CI14 |
| Clima e circulação | Ciências/Geografia | CG2 | EF08CI14 |
| Eventos climáticos | Ciências | CG2 | EF08CI15 |
| Alterações climáticas | Ciências | CG10 | EF08CI16 |
| Ciclos do carbono/água/nitrogênio | Ciências (Química) | CG2 | EM13CNT101; EM13CNT203 |
| Ecossistemas e cadeias tróficas | Ciências (Ecologia) | CG2 | EF07CI07; EF07CI08 |
| Biodiversidade e espécies | Ciências | CG10 | EF09CI12; EM13CNT206 |
| Evolução e seleção natural | Ciências (Biologia) | CG2 | EF09CI11; EF09CI09 |
| Séries temporais e dados | Matemática | CG2, CG5 | EF07MA17; EF07MA35 a 37 |
| Trade-offs e decisão socioambiental | Sustentabilidade | CG7, CG10 | EM13CNT203; EM13CNT206; EM13CNT306 |
| Investigar (hipótese→teste→revisão) | Transversal | CG2, CG7 | EM13CNT301; EM13CNT302 |

Observe que a lista foi lida de uma tabela com quebras de linha. Antes de semear, **confira cada código** contra o documento completo da matriz (Dossiê §5.3) ou contra a BNCC oficial. Onde houver dúvida, deixe o registro pendente de validação, em vez de inventar.

Na criação de uma missão (RF-062/RP-001), valide que cada código de habilidade existe no catálogo (erro 422 caso contrário).

---

# 15. Glossário curto

| Termo | Significado |
|---|---|
| ai-sim-service | Serviço Python/FastAPI de simulação e IA. Fora desta tarefa |
| platform-api | Este backend: plataforma educacional em NestJS |
| Gateway | A parte do backend que autentica, autoriza, registra e repassa chamadas ao serviço de simulação/IA |
| Porta / adaptador | Interface do domínio e sua implementação concreta (arquitetura hexagonal) |
| Fake | Adaptador falso e determinístico usado enquanto o serviço real não está disponível |
| RBAC | Controle de acesso por papel |
| Posse (ownership) | Regra de que o aluno só acessa o próprio planeta e os próprios dados |
| Tenant | Escola; unidade de isolamento lógico (RNF-013) |
| LTI 1.3 | Padrão de integração com LMS |
| OIDC | OpenID Connect, para identidade federada |
| BNCC | Base Nacional Comum Curricular |
| Trilha | Nível da turma: Fundamental II, Médio ou Técnico (RF-061) |
| Missão | Desafio criado pelo professor, ancorado a habilidades BNCC (RF-062) |
| Stealth assessment | Avaliação embutida no jogo, sem prova explícita (RP-004) |
| Perfil cognitivo | Estimativa de domínio por competência, por aluno |
| Evidência | Registro estruturado de uma ação do aluno ligada a uma competência |
| PII | Informação pessoal identificável |
| EDA | Arquitetura orientada a eventos |
| RFC 7807 | Formato padrão de erro HTTP (Problem Details) |
| ADR | Registro de decisão de arquitetura |
| DoD | Definition of Done |
