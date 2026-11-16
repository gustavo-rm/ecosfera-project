# 0016 — Federação: OIDC e LTI 1.3 com jose

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

RF-009/TASK-0028. Não há provedor OIDC nem LMS no ambiente; bibliotecas LTI disponíveis trazem MongoDB ou servidor próprio.

## Decisão

- OIDC: código de autorização + PKCE (S256), `state` e `nonce` de uso único no Redis, `id_token` validado pelo JWKS do provedor (iss, aud, exp). Provedor registrado por escola; segredo do cliente só por nome de variável de ambiente.
- LTI 1.3: iniciação de login de terceiros, launch por `form_post`, validação do `id_token` da plataforma (JWKS, aud=client_id, nonce, `deployment_id`, versão 1.3.0, `LtiResourceLinkRequest`). O curso vira turma (`platform.lti_context`); aluno entra matriculado e **menor por padrão** (restrito até o consentimento).
- Minimização: do LMS guardamos só o primeiro nome; o e-mail técnico é não roteável.
- Implementado com `jose`, sem biblioteca LTI.

## Consequências

- **Verificado só contra um provedor local de teste.** Falta validar com Keycloak/Ory e com um LMS real (Moodle/Canvas). NRPS (importação da lista completa da turma) não implementado: os alunos entram à medida que lançam.
