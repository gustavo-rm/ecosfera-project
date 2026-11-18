# 0005 — Estrutura do platform-api: monólito modular com quatro contextos

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

O `platform-api` era o starter do NestJS. O Dossiê v3 trava monólito modular, DDD, hexagonal e quatro bounded contexts.

## Decisão

- `src/modules/{identity,education,assessment,orchestration}`, cada um com `domain/ application/ infrastructure/ interface/` (ADR 0001; o nome `interface/` é mantido porque já foi aprovado).
- `src/shared/` contém o que atravessa contextos: configuração, kernel (erros, ator, papéis, finalidades, política de acesso), HTTP (contrato, validação, RFC 7807), autorização central, banco, Redis, auditoria, eventos, armazenamento, observabilidade.
- O domínio não importa NestJS nem TypeORM. Portas ficam em `domain/portas.ts`; adaptadores, em `infrastructure/`.
- Tutoria não é contexto próprio: o platform-api só faz proxy autorizado (fica em `orchestration`).
- Consultas de leitura que cruzam contextos (vínculos turma/matrícula/responsável) ficam numa porta única (`VinculosEscolares`) implementada em SQL de leitura.

## Consequências

- Dá para trocar fake por serviço real, e Redis Streams por NATS, sem tocar nas regras.
- Há dependência de aplicação entre contextos (ex.: orchestration usa `ServicoDeEducacao.exigirMissao`), aceitável num monólito modular; se um contexto virar serviço, essa chamada vira porta.
