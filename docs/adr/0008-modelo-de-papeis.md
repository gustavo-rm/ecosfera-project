# 0008 — Modelo de papéis: responsável, pesquisador, operador e serviço

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

O RF-002 cita quatro papéis; os contratos citam também responsável, pesquisador e serviço. A baseline já tinha `guardian` no enum.

## Decisão

- Papéis de login (enum `platform.user_role`, valores em inglês como na baseline): `student`, `teacher`, `coordinator`, `admin` (admin **da escola**), `guardian` (responsável, login próprio para consentir e exercer direitos), `researcher` (só dataset anonimizado; nunca dado individual) e `platform_admin` (operador: cria escolas e revisa o catálogo BNCC; não lê dado pedagógico).
- **Serviço** não é papel de usuário: é credencial própria (JWT HS256 com `SERVICE_TOKEN_SECRET`, `typ=service`, `sub` na lista `SERVICE_ALLOWED_NAMES`, validade ≤ 15 min).
- Papel vindo do LMS nunca promove usuário existente; administrador do LMS vira coordenador.

## Consequências

- Migração aditiva (`ALTER TYPE ... ADD VALUE`). Remover valor de enum exigiria migração destrutiva.
