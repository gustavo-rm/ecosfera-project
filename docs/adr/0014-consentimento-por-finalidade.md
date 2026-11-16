# 0014 — Consentimento do responsável por finalidade e gate reutilizável

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

RF-008/RNF-009: sem consentimento, sem coleta. O `ai-sim-service` também precisa consultar.

## Decisão

- Finalidades: `platform_use` (usar a plataforma: planetas, missões, tutor), `learning_assessment` (evidências e perfil), `research` (dataset anonimizado). Um registro por (aluno, finalidade) com responsável, versão do texto e datas; histórico no `audit_log`.
- Gate `ServicoDeConsentimento.permite(usuário, finalidade)` com cache Redis de 60 s invalidado a cada mudança; maior de idade não depende do responsável.
- Conta de menor sem `platform_use` fica **restrita**: pode logar, ver perfil e preferências e a situação do consentimento; não cria nem acessa planeta, tutor, WebSocket ou sincronização. Sem `learning_assessment`: nada é projetado, o painel não mostra dados pedagógicos dele, e ele fica fora de relatórios e exportações. Sem `research`: fica fora do dataset.
- Para outros serviços: `GET /internal/consent/{id}` (credencial de serviço, resposta sem PII) e evento `ConsentimentoRevogado`.
- Textos legais são placeholders versionados em `platform.consent_text` (`pending_legal_review`).

## Consequências

- Pedido P6 ao `ai-sim-service`: consultar o endpoint interno e assinar o evento de revogação.
