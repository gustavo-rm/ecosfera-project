# @ecosfera/ui

Design system compartilhado — primitivas de UI reutilizáveis entre aplicações (a princípio o `web-client`, e qualquer futuro app).

## Propósito

Centralizar componentes React agnósticos de domínio (botões, modais, campos, painéis) com suporte a acessibilidade (WCAG, alto contraste, daltonismo), garantindo consistência visual entre apps.

## Escopo

**Contém:** componentes de UI genéricos e reutilizáveis, tokens/temas compartilhados.
**Não contém:** componentes acoplados a um domínio (esses vivem nos `features/` do app), lógica de negócio, chamadas de rede.

> Distinção importante: primitiva reutilizável entre apps → aqui. Componente específico de uma tela/fluxo → `apps/web-client/src/features/<slice>/components`.

## Consumo

```bash
pnpm --filter web-client add @ecosfera/ui@workspace:*
```

`react`/`react-dom` são **peerDependencies** — providos pelo app consumidor, não empacotados aqui, para evitar duplicação de React.

> Placeholder inicial: `src/index.ts` está vazio. Popule conforme os componentes forem extraídos.