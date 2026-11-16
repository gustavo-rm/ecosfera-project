# 0010 — Eventos: outbox transacional e Redis Streams atrás de portas

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

Dossiê: Redis Streams no MVP, NATS depois. Backlog: NATS. Eventos não podem se perder nem duplicar efeito.

## Decisão

- Publicação: o evento nasce no `platform.outbox_event` na mesma transação do fato; um relay (seguro com várias réplicas: `FOR UPDATE SKIP LOCKED`) publica no stream `ecosfera.events.platform`. Porta `EventPublisher`.
- Consumo: porta `AssessmentEventSource`; adaptador Redis Streams com grupo `platform-api`, ACK após o tratamento, reivindicação de pendentes e fila `<stream>.dlq` após 5 entregas.
- Idempotência do consumidor por `eventId` (`platform.processed_event`, na mesma transação da projeção).
- Contrato dos eventos em AsyncAPI 3.0 (`packages/api-contracts/asyncapi`).

## Consequências

- Trocar por NATS é escrever dois adaptadores. Entrega é pelo menos uma vez.
