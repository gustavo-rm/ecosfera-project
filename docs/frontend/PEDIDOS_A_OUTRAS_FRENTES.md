# Pedidos a outras frentes

Nada fora de `apps/web-client` e `docs/frontend` foi alterado por decisão do frontend. Estes itens precisam de quem é dono.

| # | Para quem | Pedido | Por quê |
|---|---|---|---|
| P-01 | Raiz do monorepo / CI | **Resolvido em 2026-11-15, com aprovação do dono do projeto:** `esbuild: true` em `allowBuilds`, em commit separado. Pedido original: declarar `esbuild` em `allowBuilds` no `pnpm-workspace.yaml`. | O Vitest traz o `esbuild`. Sem a declaração, `pnpm install` termina com `ERR_PNPM_IGNORED_BUILDS` e código de saída 1, o que **deve quebrar o passo de instalação do CI**. O pnpm chega a escrever a linha sozinho no arquivo; eu a revertia a cada instalação por estar fora do meu pacote. |
| P-02 | Raiz do monorepo | O `pnpm-lock.yaml` mudou com as dependências novas do frontend. | Efeito inevitável de instalar dependências no pacote. |
| P-03 | Dono do repositório | Trazer para a `develop` a Especificação do Evolution Engine (ou o caminho dela) e o Dossiê. | Hoje a Especificação não está em branch nenhuma e o Dossiê está só em outra branch. |
| P-04 | Motor (`ai-sim-service`) | Definir no contrato a ordem dos vértices da malha geodésica e a regra de `parent`. | A Especificação não as define (D-29). O frontend tem uma convenção travada por teste; se o motor adotar outra, muda só `core/mesh/cellOrder.ts`. |
| P-05 | Motor e plataforma | Usar `docs/frontend/NECESSIDADES_DE_DADOS.md` como insumo dos contratos. | Lista o que a interface consome, com frequência e criticidade. |
| P-06 | Autoridade de domínio (biologia) | **Adiado para a v2** (ver `REVISOES_PENDENTES_V2.md`). Revisar tudo que está marcado como placeholder: biomas, zona habitável, balanço de energia, ciclos, rótulos de causa de morte e estágios, nomes gerados de linhagens. | Não inventar ciência. |
| P-07 | Equipe pedagógica | **Adiado para a v2.** Revisar `src/i18n/messages/pt-BR/pedagogy.ts` (todo texto pedagógico). | São rascunhos para dar forma à interface. |
| P-08 | Designer de produto | **Adiado para a v2.** Revisar a proposta de marca, ícones e cores em `DESIGN_TOKENS.md`. | A identidade visual é proposta. |
| P-09 | `packages/ui` | Decidir se tokens e componentes-base sobem para o pacote compartilhado. | O pacote existe e está vazio. |
| P-10 | Dono do repositório | **Resolvido em 2026-11-15, com aprovação:** removidos em commit separado `src/app/Login.tsx` (vazio) e os cinco SVGs de exemplo em `public/`. `favicon.ico` ficou (o Next o serve por convenção). | A missão exige aprovação para apagar arquivos de terceiros. |
| P-11 | Privacidade / jurídico | Definir retenção e consentimento antes de qualquer envio de eventos de evidência (ADR 0004 da raiz está "Proposto"). | O frontend gera os eventos, mas não envia nada. |
