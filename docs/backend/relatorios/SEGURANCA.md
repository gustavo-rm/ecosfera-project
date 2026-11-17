# Relatório de segurança — platform-api

**Data:** 2026-11-16, atualizado em 2026-11-17 após a revisão independente. **Escopo:** só a aplicação local e o ambiente de teste (Testcontainers). Testes defensivos e negativos; nenhuma ferramenta de ataque, nenhum sistema de terceiros.

## Resumo

| Verificação | Método | Resultado |
|---|---|---|
| Toda rota declara autorização e contrato; rotas públicas numa lista fechada (12) | `test/arquitetura/contrato-e-rotas.int-spec.ts` (reflexão sobre os decoradores + comparação com o app) | ✔ 87 rotas |
| Matriz de acesso indevido gerada das declarações | `test/seguranca/matriz-de-acesso.int-spec.ts` | ✔ 188 verificações (76 × 401 sem token, 70 × 403 papel fora da lista, 42 × 404 recurso de outra escola) + credencial de serviço |
| Posse do planeta, turma, missão; aluno × aluno; professor de outra turma | `fluxo-planeta-avaliacao`, `educacao`, testes unitários de política | ✔ |
| Token expirado, assinado com outro segredo, `alg: none` | `autenticacao.int-spec.ts` | ✔ 401 |
| Refresh reutilizado revoga a família (refresh novo e access token da sessão também morrem) | idem | ✔ |
| Logout invalida o access token na hora | idem | ✔ |
| Login: mesma resposta para e-mail inexistente e senha errada; tempo igualado (hash-isca); falha auditada sem e-mail | idem | ✔ |
| Força bruta: 5 falhas por conta → 429 com `Retry-After`, bloqueia até a senha certa durante a janela | idem | ✔ |
| Redefinição de senha: 202 sem enumeração, código de uso único, política de senha, encerra sessões | idem | ✔ |
| LTI 1.3: estado reutilizado, nonce errado, `deployment_id` errado, assinatura de outra chave → 401; admin do LMS não vira admin | `federacao.int-spec.ts` | ✔ (provedor local) |
| OIDC: PKCE S256, callback repetido recusado | idem | ✔ (provedor local) |
| Credencial de serviço: token de usuário e serviço não permitido → 401; resposta interna sem PII | matriz | ✔ |
| `audit_log` imutável: papel da aplicação sem UPDATE/DELETE/TRUNCATE; gatilho barra até o dono | `migracoes.int-spec.ts`, smoke passo 10 | ✔ |
| Papel da aplicação sem acesso ao schema `rag` | `migracoes.int-spec.ts` | ✔ |
| Fakes não ligam em produção | `configuracao.spec.ts` + execução da imagem com `NODE_ENV=production` | ✔ boot recusado |
| HTTPS obrigatório em produção (`X-Forwarded-Proto` só com `TRUST_PROXY`) | execução da imagem | ✔ 400 sem TLS |
| Entrada inválida em parâmetros, query e corpo (UUID malformado vira 404; validação 422 sem ecoar valor) | unitários do guard e do filtro; matriz | ✔ |
| Limite de corpo (256 KiB), JSON malformado (400), corpo grande (413) | filtro + `express.json({limit})` | ✔ unitário |
| Dataset de pesquisa sem PII (varredura de ids, nomes, e-mails) e com supressão k=5 | `fluxo-planeta-avaliacao`, smoke passo 8 (22 linhas, 0 achados) | ✔ |
| Redação de PII antes da IA; texto da IA tratado como dado (SSE em JSON por trecho) | unitários de redação; fluxo SSE | ✔ |
| CSV com proteção contra injeção de fórmula | código (`exportacao.service.ts`) | feito, sem teste dedicado |
| Cabeçalhos de segurança (helmet: CSP, HSTS em produção, nosniff, frame) e CORS restrito à lista | inspeção da resposta no boot | ✔ |
| Dependências: `pnpm audit --prod` (alta/crítica nas dependências do platform-api) | auditoria | ✔ 0 (após subir @nestjs 11.2 e express 5.3) |

## Revisão independente (2026-11-16)

Um agente revisor, sem ter visto o trabalho, leu o diff de autorização, consentimento, federação e migrações. Achados confirmados e o que foi feito (regressões em `test/seguranca/regressoes-da-revisao.int-spec.ts`):

| # | Severidade | Achado | Correção | Teste |
|---|---|---|---|---|
| 1 | Crítica | Admin de escola registrava provedor OIDC com `clientSecretEnv=JWT_ACCESS_SECRET` (ou outro segredo do processo) e o servidor enviava o segredo ao IdP do atacante → forjar token de operador | Só variáveis `OIDC_CLIENT_SECRET_*` (no registro e na leitura) | ✔ |
| 2 | Alta | Professor matriculava aluno de outro professor na própria turma e ganhava acesso aos dados dele | Professor só matricula aluno que não está em turma de outro professor; coordenação/admin sem restrição | ✔ |
| 3 | Alta | `isMinor=false` declarado por professor, ou troca de papel ida e volta, contornava o consentimento parental | Só admin/operador declara maioridade; voltar a aluno marca menor de novo | ✔ |
| 4 | Alta | Conjunto de sessões do usuário expirava antes das sessões renovadas → "revogar todas" falhava | TTL do conjunto renovado na rotação (`EXPIRE NX/GT`) + vida máxima absoluta de 30 dias | ✔ |
| 5 | Média | Admin trocava o e-mail do responsável e assumia a conta que consente | Admin não troca e-mail de responsável; troca de e-mail encerra sessões | ✔ |
| 6 | Média | Corrida no cache do consentimento podia manter "concedido" por até 60 s após a revogação | Cache versionado: gravação atômica só se a versão não mudou | ✔ (lógica); corrida em si não é reproduzida em teste |
| 7 | Média | Aceite sobre texto placeholder não aprovado | Em produção exige texto `approved`; rota para o operador publicar a versão aprovada | ✔ |
| 8 | Média | SSRF por URLs de IdP/LMS definidas pelo admin | Em produção: só https e host que não resolve para IP interno; checado no registro e antes de cada requisição | ✔ unitário |
| 9 | Média/baixa | `assessmentId` do feedback não era conferido | Precisa ser avaliação do mesmo aluno | revisão de código |
| 10 | Baixa | Ações de sincronização sem validação; mensagem interna devolvida | Mesmo schema das rotas; erro só com o tipo | ✔ |
| 11 | Baixa | Baseline reformatada pelo Prettier | Revertida byte a byte; excluída do lint/format | `git diff develop` vazio |
| 12 | Baixa | `down` da migração transformaria aceites de outras finalidades em genéricos | `down` remove as linhas que o schema antigo não representa | revisão de código |
| 13 | Baixa | Sem `NODE_ENV`, a proibição de fakes falhava aberta | `NODE_ENV` obrigatório; `http` exige `AI_SIM_BASE_URL` | ✔ unitário |
| 14 | Baixa | Evento anterior à concessão era projetado | Compara `occurredAt` com `granted_at` | ✔ |
| 15 | Baixa | `contextRef` livre ia sem redação à IA | Restrito a identificador | ✔ |
| S1 | Suspeita confirmada | CSRF de login federado (estado não amarrado ao navegador) | Cookie de vínculo de uso único | ✔ |
| S2 | Suspeita confirmada | OIDC sem `sub` colidiria identidades | Recusado | revisão de código |
| S3 | Suspeita confirmada | `ALTER DEFAULT PRIVILEGES` só para o papel que roda o script | Acrescentado `FOR ROLE platform_migrator` | revisão de código |
| S4 | Suspeita confirmada | Professor lia rascunhos de missões de colegas | Só publicadas ou próprias | ✔ unitário |
| — | Lacuna RF-002 | Sem rota para desativar/reativar conta | `PATCH /users/{id}/status` | ✔ |

Não corrigido (risco residual aceito e registrado): o admin da escola ainda pode criar um responsável e vinculá-lo a um aluno (a escola é controladora dos dados e a ação é auditada); exportações já geradas não são apagadas na exclusão do titular (saem pela retenção em 7 dias).

## O que NÃO foi verificado

- SAST com ferramenta dedicada (SonarQube/CodeQL): não disponível no ambiente; o job de CI proposto (P5) deve incluí-lo.
- OIDC/LTI contra Keycloak/Ory e LMS reais (só provedor local de teste).
- TLS fim a fim (o TLS é terminado no proxy reverso, fora do pacote).
- Teste de intrusão externo.

## Saída da matriz de acesso (execução de 2026-11-17)

```
[matriz-de-acesso] 189 verificações:
sem token        POST   /auth/logout → 401
sem token        GET    /auth/me → 401
sem token        POST   /users → 401
sem token        GET    /users → 401
sem token        GET    /guardians/me/students → 401
sem token        GET    /users/{id} → 401
sem token        PATCH  /users/{id} → 401
sem token        PATCH  /users/{id}/preferences → 401
sem token        PATCH  /users/{id}/role → 401
sem token        PATCH  /users/{id}/status → 401
sem token        POST   /users/{id}/password-reset → 401
sem token        POST   /users/{id}/guardians → 401
sem token        POST   /users/{id}/consent → 401
sem token        POST   /users/{id}/consent/revoke → 401
sem token        GET    /users/{id}/consent → 401
sem token        GET    /consent-texts → 401
sem token        GET    /internal/consent/{id} → 401
sem token        POST   /admin/consent-texts → 401
sem token        POST   /admin/lti/platforms → 401
sem token        POST   /admin/oidc/providers → 401
sem token        POST   /schools → 401
sem token        GET    /schools/{id} → 401
sem token        POST   /classes → 401
sem token        GET    /classes → 401
sem token        GET    /classes/{id} → 401
sem token        POST   /classes/{id}/students → 401
sem token        GET    /classes/{id}/students → 401
sem token        DELETE /classes/{id}/students/{studentId} → 401
sem token        PATCH  /classes/{id}/track → 401
sem token        GET    /tracks → 401
sem token        POST   /missions → 401
sem token        GET    /missions → 401
sem token        GET    /missions/{id} → 401
sem token        POST   /missions/{id}/publish → 401
sem token        GET    /curriculum/competencies → 401
sem token        GET    /curriculum/bncc-skills → 401
sem token        POST   /curriculum/bncc-skills → 401
sem token        PATCH  /curriculum/bncc-skills/{code} → 401
sem token        POST   /planets → 401
sem token        GET    /planets/{id} → 401
sem token        POST   /planets/{id}/validate → 401
sem token        POST   /planets/{id}/tick → 401
sem token        POST   /planets/{id}/interventions → 401
sem token        GET    /planets/{id}/timeline → 401
sem token        POST   /planets/{id}/checkpoints → 401
sem token        GET    /planets/{id}/series → 401
sem token        GET    /planets/{id}/events → 401
sem token        POST   /planets/{id}/events/respond → 401
sem token        POST   /planets/{id}/sync → 401
sem token        POST   /ai/explain → 401
sem token        POST   /ai/hint → 401
sem token        POST   /ai/advisor → 401
sem token        GET    /ai/adaptation/{studentId} → 401
sem token        POST   /assessment/events → 401
sem token        GET    /assessment/students/{id}/profile → 401
sem token        GET    /assessment/students/{id}/evidence → 401
sem token        GET    /assessment/students/{id}/bncc → 401
sem token        POST   /assessment/students/{id}/assessments → 401
sem token        GET    /assessment/students/{id}/assessments → 401
sem token        GET    /dashboard/classes/{id}/overview → 401
sem token        GET    /dashboard/classes/{id}/competencies → 401
sem token        GET    /dashboard/classes/{id}/alerts → 401
sem token        GET    /dashboard/classes/{id}/consents → 401
sem token        GET    /dashboard/schools/{id}/competencies → 401
sem token        GET    /dashboard/schools/{id}/alert-config → 401
sem token        PUT    /dashboard/schools/{id}/alert-config → 401
sem token        POST   /dashboard/students/{id}/feedback → 401
sem token        GET    /feedback/me → 401
sem token        POST   /feedback/{id}/read → 401
sem token        GET    /dashboard/reports/export → 401
sem token        GET    /research/dataset → 401
sem token        GET    /users/{id}/data-export → 401
sem token        POST   /users/{id}/deletion → 401
sem token        GET    /admin/retention/policies → 401
sem token        PUT    /admin/retention/policies/{category} → 401
sem token        POST   /admin/retention/run → 401
papel student        POST   /users → 403
papel student        GET    /users → 403
papel student        GET    /guardians/me/students → 403
papel researcher     GET    /users/{id} → 403
papel student        PATCH  /users/{id} → 403
papel student        PATCH  /users/{id}/role → 403
papel student        PATCH  /users/{id}/status → 403
papel student        POST   /users/{id}/password-reset → 403
papel student        POST   /users/{id}/guardians → 403
papel student        POST   /users/{id}/consent → 403
papel student        POST   /users/{id}/consent/revoke → 403
papel researcher     GET    /users/{id}/consent → 403
papel student        POST   /admin/consent-texts → 403
papel student        POST   /admin/lti/platforms → 403
papel student        POST   /admin/oidc/providers → 403
papel student        POST   /schools → 403
papel student        GET    /schools/{id} → 403
papel student        POST   /classes → 403
papel guardian       GET    /classes → 403
papel guardian       GET    /classes/{id} → 403
papel student        POST   /classes/{id}/students → 403
papel student        GET    /classes/{id}/students → 403
papel student        DELETE /classes/{id}/students/{studentId} → 403
papel student        PATCH  /classes/{id}/track → 403
papel guardian       GET    /tracks → 403
papel student        POST   /missions → 403
papel guardian       GET    /missions → 403
papel guardian       GET    /missions/{id} → 403
papel student        POST   /missions/{id}/publish → 403
papel student        GET    /curriculum/competencies → 403
papel student        GET    /curriculum/bncc-skills → 403
papel student        POST   /curriculum/bncc-skills → 403
papel student        PATCH  /curriculum/bncc-skills/{code} → 403
papel teacher        POST   /planets → 403
papel guardian       GET    /planets/{id} → 403
papel teacher        POST   /planets/{id}/validate → 403
papel teacher        POST   /planets/{id}/tick → 403
papel teacher        POST   /planets/{id}/interventions → 403
papel guardian       GET    /planets/{id}/timeline → 403
papel teacher        POST   /planets/{id}/checkpoints → 403
papel guardian       GET    /planets/{id}/series → 403
papel guardian       GET    /planets/{id}/events → 403
papel teacher        POST   /planets/{id}/events/respond → 403
papel teacher        POST   /planets/{id}/sync → 403
papel teacher        POST   /ai/explain → 403
papel teacher        POST   /ai/hint → 403
papel teacher        POST   /ai/advisor → 403
papel student        GET    /ai/adaptation/{studentId} → 403
papel student        GET    /assessment/students/{id}/profile → 403
papel student        GET    /assessment/students/{id}/evidence → 403
papel student        GET    /assessment/students/{id}/bncc → 403
papel student        POST   /assessment/students/{id}/assessments → 403
papel student        GET    /assessment/students/{id}/assessments → 403
papel student        GET    /dashboard/classes/{id}/overview → 403
papel student        GET    /dashboard/classes/{id}/competencies → 403
papel student        GET    /dashboard/classes/{id}/alerts → 403
papel student        GET    /dashboard/classes/{id}/consents → 403
papel student        GET    /dashboard/schools/{id}/competencies → 403
papel student        GET    /dashboard/schools/{id}/alert-config → 403
papel student        PUT    /dashboard/schools/{id}/alert-config → 403
papel student        POST   /dashboard/students/{id}/feedback → 403
papel teacher        GET    /feedback/me → 403
papel teacher        POST   /feedback/{id}/read → 403
papel student        GET    /dashboard/reports/export → 403
papel student        GET    /research/dataset → 403
papel student        GET    /users/{id}/data-export → 403
papel student        POST   /users/{id}/deletion → 403
papel student        GET    /admin/retention/policies → 403
papel student        PUT    /admin/retention/policies/{category} → 403
papel student        POST   /admin/retention/run → 403
outra escola student     GET    /users/{id} (usuario:ler) → 404
outra escola admin       PATCH  /users/{id} (usuario:gerir) → 404
outra escola student     PATCH  /users/{id}/preferences (usuario:proprio) → 404
outra escola admin       PATCH  /users/{id}/role (usuario:gerir) → 404
outra escola admin       PATCH  /users/{id}/status (usuario:gerir) → 404
outra escola admin       POST   /users/{id}/password-reset (usuario:gerir) → 404
outra escola admin       POST   /users/{id}/guardians (usuario:gerir) → 404
outra escola guardian    POST   /users/{id}/consent (usuario:ler) → 404
outra escola guardian    POST   /users/{id}/consent/revoke (usuario:ler) → 404
outra escola student     GET    /users/{id}/consent (usuario:ler) → 404
outra escola student     GET    /classes/{id} (turma:ler) → 404
outra escola teacher     POST   /classes/{id}/students (turma:gerir) → 404
outra escola teacher     GET    /classes/{id}/students (turma:gerir) → 404
outra escola teacher     DELETE /classes/{id}/students/{studentId} (turma:gerir) → 404
outra escola teacher     PATCH  /classes/{id}/track (turma:gerir) → 404
outra escola student     GET    /missions (turma:ler) → 404
outra escola student     GET    /missions/{id} (missao:ler) → 404
outra escola teacher     POST   /missions/{id}/publish (missao:gerir) → 404
outra escola student     GET    /planets/{id} (planeta:ler) → 404
outra escola student     POST   /planets/{id}/validate (planeta:agir) → 404
outra escola student     POST   /planets/{id}/tick (planeta:agir) → 404
outra escola student     POST   /planets/{id}/interventions (planeta:agir) → 404
outra escola student     GET    /planets/{id}/timeline (planeta:ler) → 404
outra escola student     POST   /planets/{id}/checkpoints (planeta:agir) → 404
outra escola student     GET    /planets/{id}/series (planeta:ler) → 404
outra escola student     GET    /planets/{id}/events (planeta:ler) → 404
outra escola student     POST   /planets/{id}/events/respond (planeta:agir) → 404
outra escola student     POST   /planets/{id}/sync (planeta:agir) → 404
outra escola student     POST   /ai/explain (planeta:agir) → 404
outra escola student     POST   /ai/hint (planeta:agir) → 404
outra escola teacher     GET    /ai/adaptation/{studentId} (usuario:pedagogico) → 404
outra escola teacher     GET    /assessment/students/{id}/profile (usuario:pedagogico) → 404
outra escola teacher     GET    /assessment/students/{id}/evidence (usuario:pedagogico) → 404
outra escola teacher     GET    /assessment/students/{id}/bncc (usuario:pedagogico) → 404
outra escola teacher     POST   /assessment/students/{id}/assessments (usuario:pedagogico) → 404
outra escola teacher     GET    /assessment/students/{id}/assessments (usuario:pedagogico) → 404
outra escola teacher     GET    /dashboard/classes/{id}/overview (turma:gerir) → 404
outra escola teacher     GET    /dashboard/classes/{id}/competencies (turma:gerir) → 404
outra escola teacher     GET    /dashboard/classes/{id}/alerts (turma:gerir) → 404
outra escola teacher     GET    /dashboard/classes/{id}/consents (turma:gerir) → 404
outra escola teacher     POST   /dashboard/students/{id}/feedback (usuario:pedagogico) → 404
outra escola teacher     GET    /dashboard/reports/export (turma:gerir) → 404
serviço: token de usuário → 401; serviço não permitido → 401; ai-sim-service → 200 (resposta sem PII)
```
