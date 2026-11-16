# Matriz de autorização do platform-api

> **Gerada do código** (`pnpm authz:matriz`, a partir dos decoradores `@Autorizacao`). Não edite à mão.
> O teste `test/seguranca/matriz-de-acesso.int-spec.ts` percorre esta mesma lista e confere que o código NEGA
> o que a matriz manda negar (sem token → 401; papel fora da lista → 403; recurso de outra escola → 404).

Regras gerais:

- **Negar por padrão**: rota sem `@Autorizacao` é recusada pelo guard central e reprovada pelo teste de arquitetura.
- **Defesa em profundidade**: a regra de posse é avaliada no guard e de novo no caso de uso, com fatos carregados pelo próprio caso de uso.
- **Isolamento por escola** (RNF-013): recurso de outra escola responde **404** (não revela existência); mesma escola sem permissão responde **403**.
- **Consentimento**: além da coluna abaixo (ator menor), todo caso de uso que lê dado de um aluno confere o consentimento **do titular** (`platform_use` para planeta, `learning_assessment` para avaliação).

Regras de posse:

- `usuario:ler`: próprio usuário; responsável vinculado; admin/coordenação da escola; professor só de aluno da sua turma; outra escola → 404
- `usuario:gerir`: admin da mesma escola ou operador; outra escola → 404
- `usuario:pedagogico`: professor do aluno, coordenação/admin da escola; o próprio aluno NÃO (RP-004); outra escola → 404
- `usuario:proprio`: só o próprio usuário
- `turma:ler`: professor da turma; aluno matriculado; coordenação/admin da escola; outra escola → 404
- `turma:gerir`: professor da turma; coordenação/admin da escola; outra escola → 404
- `missao:ler`: equipe da escola; aluno só se publicada para turma dele; outra escola → 404
- `missao:gerir`: autor; coordenação/admin da escola
- `planeta:ler`: dono (aluno); professor de turma do dono; coordenação/admin da escola; outro aluno → 404
- `planeta:agir`: só o dono (aluno)

| Método | Rota | Quem pode | Posse | Consentimento | Implementação |
|---|---|---|---|---|---|
| POST | `/admin/lti/platforms` | admin da escola | — | — | FederacaoController.registrarLti |
| POST | `/admin/oidc/providers` | admin da escola | — | — | FederacaoController.registrarOidc |
| GET | `/admin/retention/policies` | operador da plataforma, admin da escola | — | — | AvaliacaoController.politicas |
| PUT | `/admin/retention/policies/{category}` | operador da plataforma | — | — | AvaliacaoController.definirPolitica |
| POST | `/admin/retention/run` | operador da plataforma | — | — | AvaliacaoController.executar |
| GET | `/ai/adaptation/{studentId}` | professor, coordenador, admin da escola | `usuario:pedagogico` sobre `params.studentId` | — | IaController.adaptacao |
| POST | `/ai/advisor` | aluno | — | `platform_use` se o ator é menor | IaController.conselheiro |
| POST | `/ai/explain` | aluno | `planeta:agir` sobre `body.planetId` | `platform_use` se o ator é menor | IaController.explicar |
| POST | `/ai/hint` | aluno | `planeta:agir` sobre `body.planetId` | `platform_use` se o ator é menor | IaController.dica |
| POST | `/assessment/events` | **credencial de serviço** (ai-sim-service) | — | — | AvaliacaoController.eventos |
| GET | `/assessment/students/{id}/assessments` | professor, coordenador, admin da escola | `usuario:pedagogico` sobre `params.id` | — | AvaliacaoController.avaliacoes |
| POST | `/assessment/students/{id}/assessments` | professor | `usuario:pedagogico` sobre `params.id` | — | AvaliacaoController.registrar |
| GET | `/assessment/students/{id}/bncc` | professor, coordenador, admin da escola | `usuario:pedagogico` sobre `params.id` | — | AvaliacaoController.bncc |
| GET | `/assessment/students/{id}/evidence` | professor, coordenador, admin da escola | `usuario:pedagogico` sobre `params.id` | — | AvaliacaoController.evidencias |
| GET | `/assessment/students/{id}/profile` | professor, coordenador, admin da escola | `usuario:pedagogico` sobre `params.id` | — | AvaliacaoController.perfil |
| POST | `/auth/login` | **público** — login | — | — | AuthController.login |
| POST | `/auth/logout` | aluno, professor, coordenador, admin da escola, responsável, pesquisador, operador da plataforma | — | — | AuthController.logout |
| POST | `/auth/lti/launch` | **público** — launch LTI autenticado pelo id_token assinado do LMS | — | — | FederacaoController.ltiLaunch |
| GET | `/auth/lti/login` | **público** — iniciação de login LTI (o LMS chama) | — | — | FederacaoController.ltiLogin |
| GET | `/auth/me` | aluno, professor, coordenador, admin da escola, responsável, pesquisador, operador da plataforma | — | — | AuthController.eu |
| GET | `/auth/oidc/{slug}/authorize` | **público** — início do login federado | — | — | FederacaoController.oidcAutorizar |
| GET | `/auth/oidc/{slug}/callback` | **público** — retorno do provedor, autenticado por code + state + PKCE | — | — | FederacaoController.oidcCallback |
| POST | `/auth/password/forgot` | **público** — recuperação de senha (sem enumeração) | — | — | AuthController.esqueci |
| POST | `/auth/password/reset` | **público** — redefinição com código de uso único | — | — | AuthController.redefinir |
| POST | `/auth/refresh` | **público** — renovação por refresh token (autenticado pelo próprio refresh) | — | — | AuthController.refresh |
| GET | `/classes` | aluno, professor, coordenador, admin da escola | — | — | EducacaoController.turmas |
| POST | `/classes` | professor, coordenador, admin da escola | — | — | EducacaoController.criarTurma |
| GET | `/classes/{id}` | aluno, professor, coordenador, admin da escola | `turma:ler` sobre `params.id` | — | EducacaoController.turma |
| GET | `/classes/{id}/students` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | EducacaoController.alunos |
| POST | `/classes/{id}/students` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | EducacaoController.matricular |
| DELETE | `/classes/{id}/students/{studentId}` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | EducacaoController.desmatricular |
| PATCH | `/classes/{id}/track` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | EducacaoController.trilha |
| GET | `/consent-texts` | aluno, professor, coordenador, admin da escola, responsável, pesquisador, operador da plataforma | — | — | ConsentimentoController.textos |
| GET | `/curriculum/bncc-skills` | professor, coordenador, admin da escola, pesquisador, operador da plataforma | — | — | EducacaoController.habilidades |
| POST | `/curriculum/bncc-skills` | operador da plataforma | — | — | EducacaoController.criarHabilidade |
| PATCH | `/curriculum/bncc-skills/{code}` | operador da plataforma | — | — | EducacaoController.revisarHabilidade |
| GET | `/curriculum/competencies` | professor, coordenador, admin da escola, pesquisador, operador da plataforma | — | — | EducacaoController.competencias |
| GET | `/dashboard/classes/{id}/alerts` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | AvaliacaoController.alertas |
| GET | `/dashboard/classes/{id}/competencies` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | AvaliacaoController.competencias |
| GET | `/dashboard/classes/{id}/consents` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | AvaliacaoController.consentimentos |
| GET | `/dashboard/classes/{id}/overview` | professor, coordenador, admin da escola | `turma:gerir` sobre `params.id` | — | AvaliacaoController.visao |
| GET | `/dashboard/reports/export` | professor, coordenador, admin da escola | `turma:gerir` sobre `query.classId` | — | AvaliacaoController.exportar |
| GET | `/dashboard/schools/{id}/alert-config` | coordenador, admin da escola, professor | — | — | AvaliacaoController.lerConfig |
| PUT | `/dashboard/schools/{id}/alert-config` | coordenador, admin da escola | — | — | AvaliacaoController.definirConfig |
| GET | `/dashboard/schools/{id}/competencies` | coordenador, admin da escola | — | — | AvaliacaoController.escola |
| POST | `/dashboard/students/{id}/feedback` | professor | `usuario:pedagogico` sobre `params.id` | — | AvaliacaoController.feedback |
| POST | `/feedback/{id}/read` | aluno | — | — | AvaliacaoController.lido |
| GET | `/feedback/me` | aluno | — | — | AvaliacaoController.meusFeedbacks |
| GET | `/guardians/me/students` | responsável | — | — | UsuariosController.alunosDoResponsavel |
| GET | `/health` | **público** — sonda de liveness do orquestrador | — | — | SaudeController.saude |
| GET | `/internal/consent/{id}` | **credencial de serviço** (SERVICE_ALLOWED_NAMES) | — | — | ConsentimentoController.interno |
| GET | `/metrics` | **público** — raspagem do Prometheus; protegida por METRICS_TOKEN | — | — | SaudeController.metricasPrometheus |
| GET | `/missions` | aluno, professor, coordenador, admin da escola | `turma:ler` sobre `query.classId` | — | EducacaoController.missoes |
| POST | `/missions` | professor, coordenador, admin da escola | — | — | EducacaoController.criarMissao |
| GET | `/missions/{id}` | aluno, professor, coordenador, admin da escola | `missao:ler` sobre `params.id` | — | EducacaoController.missao |
| POST | `/missions/{id}/publish` | professor, coordenador, admin da escola | `missao:gerir` sobre `params.id` | — | EducacaoController.publicar |
| POST | `/planets` | aluno | — | `platform_use` se o ator é menor | PlanetasController.criar |
| GET | `/planets/{id}` | aluno, professor, coordenador, admin da escola | `planeta:ler` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.obter |
| POST | `/planets/{id}/checkpoints` | aluno | `planeta:agir` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.checkpoint |
| GET | `/planets/{id}/events` | aluno, professor, coordenador, admin da escola | `planeta:ler` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.eventos |
| POST | `/planets/{id}/events/respond` | aluno | `planeta:agir` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.responder |
| POST | `/planets/{id}/interventions` | aluno | `planeta:agir` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.intervir |
| GET | `/planets/{id}/series` | aluno, professor, coordenador, admin da escola | `planeta:ler` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.series |
| POST | `/planets/{id}/sync` | aluno | `planeta:agir` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.sync |
| POST | `/planets/{id}/tick` | aluno | `planeta:agir` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.tick |
| GET | `/planets/{id}/timeline` | aluno, professor, coordenador, admin da escola | `planeta:ler` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.linha |
| POST | `/planets/{id}/validate` | aluno | `planeta:agir` sobre `params.id` | `platform_use` se o ator é menor | PlanetasController.validar |
| GET | `/ready` | **público** — sonda de readiness do orquestrador | — | — | SaudeController.prontidao |
| GET | `/research/dataset` | pesquisador | — | — | AvaliacaoController.dataset |
| POST | `/schools` | operador da plataforma | — | — | EducacaoController.criarEscola |
| GET | `/schools/{id}` | admin da escola, coordenador, professor, operador da plataforma | — | — | EducacaoController.escola |
| GET | `/tracks` | aluno, professor, coordenador, admin da escola | — | — | EducacaoController.trilhas |
| GET | `/users` | admin da escola, coordenador | — | — | UsuariosController.listar |
| POST | `/users` | admin da escola, professor, operador da plataforma | — | — | UsuariosController.criar |
| GET | `/users/{id}` | aluno, professor, coordenador, admin da escola, responsável, operador da plataforma | `usuario:ler` sobre `params.id` | — | UsuariosController.obter |
| PATCH | `/users/{id}` | admin da escola, operador da plataforma | `usuario:gerir` sobre `params.id` | — | UsuariosController.corrigir |
| GET | `/users/{id}/consent` | aluno, professor, coordenador, admin da escola, responsável | `usuario:ler` sobre `params.id` | — | ConsentimentoController.situacao |
| POST | `/users/{id}/consent` | responsável | `usuario:ler` sobre `params.id` | — | ConsentimentoController.registrar |
| POST | `/users/{id}/consent/revoke` | responsável | `usuario:ler` sobre `params.id` | — | ConsentimentoController.revogar |
| GET | `/users/{id}/data-export` | responsável, admin da escola, professor, coordenador, pesquisador, operador da plataforma | — | — | AvaliacaoController.acesso |
| POST | `/users/{id}/deletion` | responsável, admin da escola | — | — | AvaliacaoController.exclusao |
| POST | `/users/{id}/guardians` | admin da escola | `usuario:gerir` sobre `params.id` | — | UsuariosController.vincular |
| POST | `/users/{id}/password-reset` | admin da escola, operador da plataforma | `usuario:gerir` sobre `params.id` | — | UsuariosController.redefinicao |
| PATCH | `/users/{id}/preferences` | aluno, professor, coordenador, admin da escola, responsável, pesquisador, operador da plataforma | `usuario:proprio` sobre `params.id` | — | UsuariosController.preferencias |
| PATCH | `/users/{id}/role` | admin da escola, operador da plataforma | `usuario:gerir` sobre `params.id` | — | UsuariosController.papel |

WebSocket `GET /planets/{id}/stream`: aluno, professor, coordenação, admin; posse `planeta:ler`; consentimento `platform_use` do dono; conexão fechada (4403) quando o consentimento é revogado e (4401) quando a sessão é revogada.
