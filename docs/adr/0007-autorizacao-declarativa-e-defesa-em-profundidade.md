# 0007 — Autorização declarativa, negar por padrão e defesa em profundidade

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

RF-004, RNF-006, RNF-013 e o princípio "negue por padrão": esquecer um guard vira vazamento.

## Decisão

- Toda rota tem `@Autorizacao(...)`: `publico` (com motivo), `servico`, ou `papeis` + `posse` (regra nomeada) + `consentimento` (finalidade exigida quando o ator é menor).
- Um guard global avalia na ordem: declaração presente (senão nega) → autenticação → papel → posse → consentimento. Regras de posse são registradas pelos contextos (`usuario:*`, `turma:*`, `missao:*`, `planeta:*`).
- Os casos de uso reavaliam a mesma política pura (`decidirAcessoAoUsuario`, `decidirAcessoATurma`, `decidirAcessoAoPlaneta`...) com fatos carregados por eles mesmos.
- Recurso de outra escola responde **404** (não revela existência); mesma escola sem permissão, **403**. ID malformado, 404.
- Teste de arquitetura: toda rota tem contrato e autorização; a lista de rotas públicas é fechada. A matriz `docs/backend/MATRIZ_DE_AUTORIZACAO.md` é gerada do código e um teste gerado confere 401/403/404 para todas as rotas.

## Consequências

- O custo é uma consulta extra por requisição com posse (guard + caso de uso). Aceito pela segurança.
