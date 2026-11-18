# 0013 — Avaliação: projeção idempotente como modelo de leitura

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

As tabelas `evidence`, `competency_estimate`, `cognitive_profile` estão no schema `platform`, mas o cálculo é do `ai-sim-service`.

## Decisão

- O platform-api consome os eventos e projeta, de forma idempotente (eventId) e ordenada (estimativa mais antiga não sobrescreve a mais nova).
- Sem consentimento `learning_assessment` válido, o evento é descartado (só fica o registro de que foi descartado).
- Após revogação, o já projetado é apagado no prazo da política de retenção (`assessment_after_consent_revocation`, placeholder 30 dias); enquanto isso o painel nega acesso (o gate vale na leitura também).
- `POST /assessment/events` (credencial de serviço) é alternativa síncrona ao stream.

## Consequências

- O painel funciona e é testável sem o serviço de IA, com dados sintéticos marcados.
