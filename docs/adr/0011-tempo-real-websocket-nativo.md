# 0011 — Tempo real: WebSocket nativo com fan-out por Redis

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

Dossiê: WebSocket com mensagens tipadas; backlog: Socket.IO. Requisitos: autenticação no handshake, reconexão, backpressure, fan-out, ≥ 40 conexões.

## Decisão

- WebSocket nativo (`ws`) em `/platform/api/v1/planets/{id}/stream`; mensagens `{type: delta|event|tutor|alert, payload, tickId}`.
- Autenticação no handshake: subprotocolos `ecosfera.v1` + `bearer.<jwt>` (navegador) ou cabeçalho `Authorization`; token nunca na URL. Posse e consentimento do dono conferidos antes do upgrade (401/403/404 em RFC 7807).
- Fan-out por Redis pub/sub; replay das últimas N mensagens por `?lastTickId=`; batimento de 30 s derruba conexões mortas e as que perderam sessão ou consentimento; revogação fecha na hora (4403) via canal Redis.
- Backpressure: acima de `WS_MAX_BUFFERED_BYTES`, deltas são coalescidos (fica o mais recente); acima de 4×, fecha com 1013.

## Consequências

- Sem Socket.IO: o cliente usa a API WebSocket do navegador; reconexão é responsabilidade do cliente (com `lastTickId`).
