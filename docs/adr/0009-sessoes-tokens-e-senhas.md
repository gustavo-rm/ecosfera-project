# 0009 — Sessões, tokens e senhas

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

TASK-0026 pede JWT curto, refresh rotativo em cookie httpOnly e revogação em Redis; o Dossiê devolve o refresh no corpo.

## Decisão

- Access token JWT HS256, 10 min, com `sid` da sessão. A cada requisição o guard confere se a sessão existe no Redis: logout e revogação valem na hora.
- Refresh opaco `sid.segredo`; o Redis guarda só o hash. Rotação atômica em Lua; reapresentar um refresh já usado **revoga a família** (sessão) e é auditado.
- Entrega: navegador recebe cookie `ecosfera_refresh` (`httpOnly`, `Secure` em produção, `SameSite=Strict`, `Path=/platform/api/v1/auth`); cliente sem navegador pede `X-Refresh-Transport: body` e recebe no corpo (campo opcional, aditivo ao contrato do Dossiê).
- Senhas com Argon2id (19 MiB, t=2, p=1, parâmetros OWASP). Login inexistente verifica um hash-isca (tempo igual). Mensagem única de erro.
- Limites: falhas por conta (5 em 15 min, contadas só em falha, zeradas no sucesso) e por IP (300/min em auth; 3000/min geral — escola atrás de NAT).
- Mudança de papel, redefinição de senha e exclusão encerram todas as sessões do usuário.

## Consequências

- HS256 exige o mesmo segredo nas réplicas (cofre). Se outro serviço precisar validar tokens de usuário, trocar por EdDSA com JWKS publicado.
