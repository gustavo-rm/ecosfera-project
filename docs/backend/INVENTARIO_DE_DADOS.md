# Inventário de dados pessoais do platform-api (RNF-010)

> **Base legal e prazos são PROPOSTAS para revisão do DPO e da assessoria jurídica** (pedido P9). Os prazos vivem em `platform.retention_policy` e mudam sem novo deploy. Nenhum dado entra sem finalidade registrada aqui.

Legenda de acesso: A = aluno (titular), R = responsável vinculado, P = professor da turma, C = coordenação da escola, AD = admin da escola, OP = operador da plataforma, PQ = pesquisador (só anonimizado), S = ai-sim-service (credencial de serviço).

| Tabela.campo | Dado | Finalidade | Base legal proposta | Retenção proposta | Quem acessa |
|---|---|---|---|---|---|
| `app_user.name` | Nome | Identificar o aluno para o professor; saudação | Execução da atividade educacional (art. 7º, V / art. 14 com consentimento do responsável para menor) | Enquanto a conta existir; pseudonimizado na exclusão | A, R, P, C, AD |
| `app_user.email` | E-mail (ou identificador técnico não roteável para contas federadas) | Login e redefinição de senha | Idem | Idem | A, AD, OP |
| `app_user.password_hash` | Hash Argon2id | Autenticação | Idem | Idem; apagado na pseudonimização | ninguém (só verificação) |
| `app_user.role`, `school_id` | Papel e escola | Autorização e isolamento | Idem | Idem | sistema |
| `app_user.is_minor` | Indicador de menor | Exigir consentimento do responsável | Obrigação legal (art. 14) | Idem | sistema, AD |
| `app_user.preferences` | Idioma e acessibilidade | Adaptar a interface (RF-010) | Idem | Idem | A |
| `guardian` | Vínculo responsável↔aluno | Consentimento e direitos do titular | Obrigação legal (art. 14) | Enquanto o vínculo existir; apagado na exclusão | R, AD |
| `consent.*` | Finalidade, situação, versão do texto, datas, quem concedeu/revogou | Prova do consentimento (RF-008) | Obrigação legal | **Mantido** como prova (sem PII além de ids) | R, P, C, AD, S (só sim/não) |
| `enrollment`, `class` | Matrícula e turma | Organização pedagógica | Execução da atividade educacional | Enquanto a matrícula existir | P, C, AD, A (as próprias) |
| `planet_meta` | Dono, missão, era, seed | Posse e vínculo com a missão | Consentimento `platform_use` | Arquivado na exclusão; estado no ai-sim-service | A, P, C, AD |
| `evidence.*` | Ações do aluno ligadas a competências | Acompanhamento pedagógico (RF-076) | Consentimento `learning_assessment` | 365 dias; 30 dias após revogação | P, C, AD |
| `cognitive_profile`, `competency_estimate` | Estimativa por competência | Painel do professor (RF-072/073) | Consentimento `learning_assessment` | 365 dias; 30 dias após revogação | P, C, AD |
| `assessment.*` | Pré/pós-teste e rubricas | RF-074/075 | Consentimento `learning_assessment` | Junto com evidências | P, C, AD |
| `feedback.content` | Texto do professor ao aluno (**cifrado AES-256-GCM**) | RF-067 | Execução da atividade educacional | 365 dias | A, P |
| `external_identity` | (issuer, subject) do LMS/IdP | SSO (RF-009) | Execução | Enquanto a conta existir | sistema |
| `audit_log.*` | Quem fez o quê, quando, traceId; só ids e metadados | Segurança e prestação de contas | Legítimo interesse / obrigação legal | **Imutável**; prazo a definir pelo DPO (não há expurgo automático) | OP, AD (via suporte) |
| `data_subject_request` | Pedidos de acesso/exclusão | Prova do atendimento ao titular (RNF-012) | Obrigação legal | A definir | AD, OP |
| `export_record` + objeto no MinIO | Relatórios e datasets | RF-066, RF-078 | Idem às fontes | Objetos: 7 dias (relatórios), 30 dias (datasets) | quem gerou (URL de 5 min) |
| Redis `session:*` | Sessão (id do usuário, hash do refresh) | Autenticação | Execução | TTL = validade do refresh (7 dias) | sistema |
| Redis `ratelimit:*`, `consent:*` | Contadores (conta pseudonimizada por HMAC) e cache de consentimento | Segurança; desempenho | Legítimo interesse | 15 min / 60 s | sistema |
| Logs (stdout) | traceId, id do ator, rota-modelo | Operação | Legítimo interesse | Política da infraestrutura | operação |

## O que NÃO coletamos

- Data de nascimento (só o indicador `is_minor`), endereço, telefone, CPF, foto, e-mail do LMS.
- Nome, e-mail e texto livre nunca vão para logs (redação no logger), URLs, mensagens de erro ou eventos.
- O contexto enviado ao serviço de IA leva só ids opacos; o texto livre do aluno passa por redação de PII.
- Telemetria bruta não é guardada no platform-api (é do ai-sim-service, sob o gate de consentimento).

## Direitos do titular (RNF-012)

- Acesso: `GET /users/{id}/data-export` (responsável vinculado ou admin da escola).
- Correção: `PATCH /users/{id}` (admin da escola).
- Exclusão: `POST /users/{id}/deletion` — apaga evidências, perfil, feedback, avaliações, matrículas e vínculos; arquiva planetas; pseudonimiza a conta; encerra sessões; publica `TitularExcluido` para o ai-sim-service.
- Revogação do consentimento: `POST /users/{id}/consent/revoke` (efeito imediato).
