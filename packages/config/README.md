# @ecosfera/config

Configuração de tooling **compartilhada** por todo o monorepo: base de ESLint (flat config) e Prettier. Fonte única de verdade para o padrão de código — nenhum workspace define regras próprias do zero.

## Conteúdo

- `eslint.config.js` — base flat de ESLint (JS + TypeScript + import order).
- `prettier.config.js` — padrão de formatação (aspas, vírgulas, largura).

## Como consumir

Adicione como dependência de workspace no pacote que vai usar:

```bash
pnpm --filter <pacote> add @ecosfera/config@workspace:*
```

**ESLint** — no `eslint.config.mjs` do workspace, estenda a base e adicione o que for específico (ex.: fronteiras de import da arquitetura):

```js
import base from '@ecosfera/config/eslint';

export default [
  ...base,
  // regras específicas do pacote aqui
];
```

**Prettier** — no `prettier.config.mjs` do workspace:

```js
export { default } from '@ecosfera/config/prettier';
```

## Escopo

**Contém:** apenas configuração de lint/format reutilizável.
**Não contém:** código de aplicação, tipos de domínio (→ `@ecosfera/shared-types`), contratos de API (→ `@ecosfera/api-contracts`).