# @ecosfera/shared-types

Tipos TypeScript **compartilhados** entre os pacotes TS do monorepo (`web-client`, `platform-api` e demais).

## Propósito

Evitar duplicação de definições de tipo usadas em mais de um lugar: modelos de domínio expostos ao cliente, enums, e tipos utilitários comuns.

## Escopo

**Contém:** tipos e interfaces TS reutilizados por múltiplos pacotes.
**Não contém:** contratos de API / schemas de wire (→ `@ecosfera/api-contracts`), componentes de UI (→ `@ecosfera/ui`), regra de negócio.

> Diferença para `api-contracts`: aqui ficam tipos internos do lado TS; lá fica a fronteira neutra de API (que também serve ao serviço Python).

## Consumo

```bash
pnpm --filter <pacote> add @ecosfera/shared-types@workspace:*
```

Uso:

```ts
import { /* tipos */ } from '@ecosfera/shared-types';
```