# 0004 — LGPD: dados pessoais e retenção da coleção telemetry

- Status: Proposto — decisão de retenção ainda pendente de definição pelo time/jurídico
- Data: 2026-07-22

## Contexto

A coleção `telemetry` (MongoDB, ver
`infra/docker/mongo/initdb/01-collections.js`) registra eventos brutos de
sessão para avaliação stealth do aprendizado, indexados por `sessionId` e
`planetId`. Como o produto é educacional e presumivelmente atende menores de
idade, esses eventos são candidatos a dado pessoal (associáveis a um aluno
identificável via `sessionId`) sob a LGPD.

Decidir a política de retenção/anonimização **antes** de a coleção
acumular dados reais é significativamente mais barato do que fazer expurgo
ou anonimização retroativa depois.

## Decisão (a confirmar com o time/responsável por privacidade)

- `telemetry` é tratada como dado pessoal enquanto associada a `sessionId`.
- Definir prazo de retenção (ex.: N meses) após o qual os documentos são
  anonimizados (remoção de `sessionId`/qualquer identificador de aluno) ou
  agregados/expurgados.
- `event_log` (log de eventos da *simulação*, não de acesso) não deve ser
  confundido com auditoria de segurança — caso seja necessário auditoria de
  ações administrativas/acesso no futuro, ela deve viver em uma coleção
  própria, não misturada a `event_log` ou `telemetry`.

## Consequências

- Esta ADR fica em status "Proposto" até o time confirmar o prazo de
  retenção concreto — o objetivo aqui é registrar a necessidade da decisão,
  não impor um número arbitrário.
- Uma vez definido o prazo, a implementação (job de expurgo/anonimização)
  entra como caso de uso do bounded context `simulation` (ver ADR 0001/0002),
  já que é quem possui a coleção `telemetry`.
