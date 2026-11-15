# Divergências entre documentos, e entre documentos e repositório

| # | Divergência | Leitura adotada |
|---|---|---|
| V-01 | **A Especificação do Evolution Engine não está no repositório** em nenhuma branch. Foi fornecida como anexo da conversa em 2026-11-15 e consultada só nos trechos da malha geodésica (§6.2). O Dossiê está só na branch `feature/AI-simulation-service-development`. | A malha foi conferida (D-29): estrutura igual, ordem dos vértices não definida pela Especificação. O restante do briefing **não** foi conferido contra o original. |
| V-02 | Pandemia e tempestade solar aparecem no Dossiê; o catálogo de eventos do motor (§20.2) não as tem e §26 diz que epidemias não são representáveis. | Pandemia e espécie invasora são eventos abstratos de interface, marcados como tal no "Por quê?". Tempestade solar não foi feita como evento; a atividade da estrela aparece nas auroras e na erosão da atmosfera. |
| V-03 | A Especificação não define rótulos em português para causas de morte e estágios de vida. | Rótulos provisórios em `planet.ts` (`cause.*`, `stage.*`), marcados para revisão. |
| V-04 | Dossiê e TASK-0034/0066 pedem WebGPU com fallback; TASK-0067/0068/0069 pedem GLSL. O `WebGPURenderer` não aceita GLSL. | ADR FE-0001: GLSL em `WebGLRenderer`. |
| V-05 | Nome do pacote: o repositório tem `apps/web-client`; o backlog fala em `apps/web`. | Vale o repositório: `apps/web-client`. |
| V-06 | O Dossiê marca RF-054, RF-056 e RF-059 como S ou C; a missão os pede completos. | Feitos completos. |
| V-07 | O repositório tem `packages/ui` descrito como design system compartilhado, mas vazio. A missão põe o design system dentro do pacote do frontend. | Tokens e componentes ficam em `apps/web-client`. Mover para `packages/ui` é pedido a outra frente. |
| V-08 | As tarefas do backlog descrevem WebSocket, tRPC e Auth.js. A missão proíbe contrato e login reais agora. | Nada disso foi implementado; fica atrás da porta de dados e da sessão simulada. |
| V-09 | O backlog não tem tarefa de i18n nem de interface para responsável e coordenação. A missão e o Dossiê pedem as três. | Feitas. |
| V-10 | O `README` do pacote descrevia fontes Geist via `next/font/google`. O projeto pede Space Grotesk, Inter e JetBrains Mono e proíbe terceiros em tempo de execução. | Trocado pelas três fontes hospedadas localmente. |
| V-11 | O glossário pede "Marcador" e proíbe "tag" na interface. O Apêndice A usa `*_tag` como identificador. | Interface usa "Marcador"; o código mantém os identificadores do Apêndice A. |
| V-12 | A Era 9 (Civilizações) está na lista de eras, mas fora do MVP. | Tem nome e rótulo; nenhum cenário chega a ela. Cidades são só ponto de extensão, desligado. |
