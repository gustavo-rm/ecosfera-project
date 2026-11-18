# Decisões tomadas em lacunas da documentação

Cada decisão tem motivo. As de arquitetura têm ADR em `docs/adr/` (0005 a 0017).

| # | Decisão | Motivo |
|---|---|---|
| DEC-01 | Prefixo HTTP `/platform/api/v1` | Briefing pede `/{service}/api/v1`; "platform" é o contexto e o schema |
| DEC-02 | Valores de papel na API iguais ao enum da baseline (`student`, `teacher`...) | Evita tradução e divergência com o banco; o domínio usa nomes em português |
| DEC-03 | Campos do login seguem o Dossiê (`email`, `senha`, resposta com `perfil`) | Contrato do cliente é o do Dossiê |
| DEC-04 | Recurso de outra escola → 404; mesma escola sem permissão → 403; outro aluno no planeta → 404 | Não revelar existência entre escolas e entre alunos |
| DEC-05 | Aluno é menor por padrão (`isMinor=true`) ao ser criado, inclusive via LTI | Na dúvida, aplicar a proteção mais forte (RSK-05) |
| DEC-06 | Conta sem senha local recebe link de ativação; o admin pode definir senha inicial | Alunos de 12 anos muitas vezes não têm e-mail próprio |
| DEC-07 | Sem provedor de e-mail: `ADAPTER_MAILER=disabled` em produção (redefinição pelo admin por outro canal, 501 explícito) | Fakes proibidos em produção; não inventar SMTP |
| DEC-08 | Limites: 5 falhas de login por conta em 15 min; 300 req/min de auth por IP; 3000 req/min geral por IP | Escola atrás de NAT com 40+ alunos (RNF-005) — descoberto no smoke |
| DEC-09 | Missão continua presa à trilha (nível) da baseline; publicação para turmas em `mission_assignment` | Respeita a baseline e atende "publicada para uma turma" |
| DEC-10 | Catálogo BNCC: 28 habilidades e 10 competências semeadas como `pending_validation`; descrições são resumos não oficiais | Códigos conferidos como existentes na BNCC; vínculos tema→competência e textos dependem de especialista (RSK-06) |
| DEC-11 | O operador da plataforma (`platform_admin`) revisa o catálogo; coordenação não altera o catálogo global | Catálogo é compartilhado entre escolas |
| DEC-12 | Professor lê planeta, perfil e evidências só de alunos das próprias turmas; coordenação e admin, da escola inteira | Menor privilégio |
| DEC-13 | Aluno não vê perfil, evidências, mapa BNCC nem pré/pós-teste; vê só o feedback textual do professor | RP-004 (avaliação invisível). Dúvida registrada: se a pedagogia quiser mostrar progresso qualitativo, é uma rota nova |
| DEC-14 | Leitura de dado de menor por outra pessoa gera `minor_data.accessed` no audit_log | Instrução: "acesso de professor a dado de menor" é ação sensível |
| DEC-15 | Dataset de pesquisa inclui só alunos com `research` E `learning_assessment` concedidos explicitamente, inclusive maiores de idade | Não há fluxo de consentimento de adulto; conservador |
| DEC-16 | k-anonimato k=5 por (escola, nível) | Valor usual na literatura; parâmetro a validar com o DPO |
| DEC-17 | Retenção: prazos em `retention_policy` como placeholder (365 dias evidências, 30 dias após revogação, 7 dias exportações, 30 dias datasets, 730 dias contas desativadas) | Mecanismo pronto; prazo é decisão do DPO/jurídico |
| DEC-18 | Exclusão do titular pseudonimiza a conta (não apaga a linha) | `audit_log` é imutável e referencia o usuário |
| DEC-19 | Limiares de alerta padrão 0,4 de domínio, incerteza ≤ 0,35, ≥ 3 evidências, 14 dias de inatividade, por escola | Placeholder pedagógico (`pending_pedagogical_review`) |
| DEC-20 | Tick com mais de `TICK_SYNC_MAX_STEPS` (10) passos vira job assíncrono (202) | Dossiê: pesado → 202 + WebSocket |
| DEC-21 | Feedback do professor cifrado em repouso (AES-256-GCM); demais dados confiam na criptografia de disco/backup da infraestrutura | Texto livre sobre menor é o dado mais sensível que o platform-api guarda; cifrar e-mail quebraria a busca por e-mail |
| DEC-22 | Sincronização offline: `POST /planets/{id}/sync` com `idempotencyKey` por ação, aplicadas em ordem de `clientTimestamp` | Ponto de entrada reservado (RNF-021); last-write-wins é do serviço de simulação |
| DEC-23 | `Idempotency-Key` opcional em intervenções | Reenvio do cliente em rede ruim não gasta pontos duas vezes |
| DEC-24 | OpenTelemetry sem exportador por padrão; exporta OTLP só se `OTEL_EXPORTER_OTLP_ENDPOINT` for definido | Sem telemetria de terceiros por padrão |
| DEC-25 | `/metrics` exige `METRICS_TOKEN` em produção | Métricas revelam volume de uso |
| DEC-26 | Documentação de API como HTML estático gerado (sem Swagger UI) | `swagger-ui-dist` traz telemetria de terceiros (`@scarf/scarf`) |
| DEC-27 | `prom-client` substituído por `@prometheus-io/client` | O primeiro foi descontinuado em favor do segundo (mesma API) |
| DEC-28 | NestJS mantido na major 11 (11.2.10), `express` 5.3 | Corrige avisos de segurança de `multer`, `proxy-addr`, `body-parser` sem subir de major |
| DEC-29 | Cobertura mínima: linhas 80%, statements 78%, funções 70%, ramos 60% (unit + integração) | Medido 82/80/73/64; o gate evita regressão |
| DEC-30 | Professor só matricula aluno que não está em turma de outro professor; coordenação e admin matriculam qualquer aluno da escola | Sem isso, matricular dava ao professor acesso a qualquer aluno (revisão, achado 2) |
| DEC-31 | Maioridade de aluno só é declarada por admin da escola ou operador, e voltar ao papel de aluno marca menor de novo | O consentimento parental não pode ser contornado por quem lida com o aluno no dia a dia (achado 3). Data de nascimento não é coletada (minimização); se a escola precisar, é uma decisão do DPO |
| DEC-32 | Vida máxima absoluta da sessão: 30 dias (`REFRESH_ABSOLUTE_TTL_SECONDS`) | Refresh contínuo não pode tornar a sessão eterna (achado 4) |
| DEC-33 | O e-mail do responsável não é alterável pelo admin da escola | Protege a conta que decide o consentimento (achado 5) |
| DEC-34 | Em produção, aceite só sobre texto `approved` (`CONSENT_REQUIRE_APPROVED_TEXT`); em dev/teste aceita placeholder | Consentimento sobre texto não aprovado é inválido (achado 7). Consequência: em produção nenhum menor usa a plataforma até o DPO aprovar os textos (P9) |
| DEC-35 | Segredo de cliente OIDC só de variáveis `OIDC_CLIENT_SECRET_*` | Evita exfiltração de segredos do servidor (achado 1, crítico) |
| DEC-36 | Em produção, URLs de IdP/LMS precisam ser https e não resolver para IP interno | SSRF (achado 8) |
| DEC-37 | `NODE_ENV` obrigatório | A proibição de fakes não pode falhar aberta (achado 13) |
| DEC-38 | Login federado amarrado ao navegador por cookie de uso único (`SameSite=None; Secure` no LTI) | CSRF de login |
