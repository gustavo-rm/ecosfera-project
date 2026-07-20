# @ecosfera/api-contracts

Contratos de API do sistema — a **fronteira neutra** entre os serviços. Define o formato das mensagens trocadas via REST/WebSocket/SSE, de forma independente de linguagem.

## Propósito

- Hospedar as **specs OpenAPI/AsyncAPI** e os **schemas** derivados delas.
- Ser a fonte única dos contratos consumidos pelo `web-client` e pelo `platform-api` (TS) e, quando aplicável, pelo `ai-sim-service` (Python, via geração a partir das mesmas specs).

## Por que é um pacote separado

O `platform-api` e o `ai-sim-service` (Python) só se comunicam por contrato, nunca por import direto de código. Este pacote é esse contrato: quem muda a API mexe aqui, e os consumidores se atualizam a partir daqui.

## Escopo

**Contém:** specs de API (OpenAPI/AsyncAPI), schemas de request/response e de eventos, tipos gerados dessas specs.
**Não contém:** tipos de domínio internos (→ `@ecosfera/shared-types`), regra de negócio, código de serviço.

## Consumo

```bash
pnpm --filter <pacote> add @ecosfera/api-contracts@workspace:*
```

> Placeholder inicial: `src/index.ts` está vazio. Popule conforme as specs forem definidas.