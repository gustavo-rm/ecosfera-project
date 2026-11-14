# Relatório final — frontend do ECOSFERA

Data: 2026-11-14. Branch: `feature/frontend-planet-and-dashboards`, criada a partir da `develop`. Commits locais; nada foi enviado ao remoto.

## 1. O que foi feito

Um frontend completo e navegável em `apps/web-client`, que roda sem backend sobre uma fonte de dados sintética local.

- **Planeta 3D** em WebGL 2 (GLSL): relevo com exagero ajustável, oceanos, gelo, atmosfera com limbo, nuvens e tempestades, auroras, estrela, luas, fundo de estrelas, vegetação e florações, organismos instanciados em zoom, nove tipos de evento com telegrafia, 18 camadas de dados com sonda e legenda. Um único pipeline paramétrico produz todos os arquétipos (incandescente, condensação, microbiano, tipo Terra, oceano, deserto, bola de neve, arquipélago, sem atmosfera, estufa, pós-extinção).
- **Arquitetura** nas sete camadas pedidas: estado visual interno, uma única porta de dados (`PlanetStateSource`, com fonte sintética, fonte de fixtures e esboço não implementado do backend), store com buffer circular de instantâneos, render sem re-renderização por quadro, interface com tokens `--ec-*`, camada de acessibilidade e console de laboratório.
- **Estudante:** jogo com HUD, Gênese com prévia ao vivo e zona habitável, intervenções com custo e previsão, árvores científica e tecnológica, Códex com ficha de espécie, missões e descobertas, tutor por regras com cadeia causal, relatório de fim de era, barramento local de evidências.
- **Dashboards:** séries temporais, pirâmide de energia, teia trófica, árvore filogenética, diversidade e estrutura, ciclos biogeoquímicos, painel regional, progresso.
- **Professor, coordenação e responsável:** turma, aluno, BNCC, gestão, criador de desafios, comparação de planetas, exportação em PDF e CSV, mensagens, consentimento; tudo com dados simulados e pseudonimizados.
- **Fundação:** design system inicial (tema escuro, claro e alto contraste), fontes locais, i18n em pt-BR, estrutura de PWA.
- **Documentação:** seis ADRs, decisões, divergências, pedidos a outras frentes, tokens, inventário de necessidades de dados, relatórios, matriz de cobertura e catálogo visual.

## 2. O que foi verificado, e como

| Verificação | Resultado |
|---|---|
| Testes unitários (Vitest) | 50 testes passam. Incluem um teste por linha da tabela "variável → efeito", contraste dos tokens nos 4 temas, paletas sob simulação de daltonismo, descrição textual, métricas de regime, buffer, fixtures, exportações e integridade das chaves de texto. |
| Tipos e lint | `tsc` sem erros; ESLint sem erros (avisos menores). |
| Build de produção | 22 rotas estáticas. |
| Ponta a ponta (Playwright) | 68 checagens passam: axe-core com 0 violações em 43 combinações de tela e tema; 14 fluxos só com teclado; estados carregando, vazio, erro, sem vida e fim de era; 0 erros de console. Relatório legível em `relatorios/e2e.md`. |
| Desempenho | Medido em WebGL por software: 34,8 FPS com qualidade automática em 1366×768 (28,2 FPS com CPU limitada em 4×). Latência da ação ao feedback: p95 de 268 ms. |
| Tamanho do pacote | Dentro dos limites definidos: jogo com 469 KiB comprimidos de JS e CSS. |
| Catálogo visual | 17 folhas de contato, olhadas e criticadas ao longo do trabalho; várias rodadas de correção no planeta. |

A verificação automática encontrou defeitos reais, que foram corrigidos: contraste insuficiente em três lugares, regiões roláveis sem foco, papéis ARIA incorretos, uma paleta de séries confundível em daltonismo, a resolução dinâmica que era desfeita a cada atualização e uma corrida na retomada de sessão.

## 3. O que NÃO foi verificado, e por quê

1. **Chromebook real (RNF-001).** Não tenho o hardware. WebGL por software é um piso pessimista e não representa o alvo.
2. **Leitor de tela real e usuários reais (RNF-018, RNF-022).** Só verificação automática e por código.
3. **Aparelhos de toque.** Gestos de pinça e arrasto foram implementados, mas só exercitados por emulação de viewport.
4. **Firefox e Safari (RNF-023).** Só Chromium.
5. **Fidelidade à Especificação do Evolution Engine.** O documento não está no repositório. Trabalhei pelo briefing; não pude conferir o briefing contra o original, nem a ordem das células da malha.
6. **Instalação como PWA e uso offline.** Só a estrutura.
7. **O PDF exportado aberto em um leitor.** A estrutura do arquivo é testada, não a exibição.
8. **Ciência e pedagogia.** Todas as fórmulas da fonte sintética e todos os textos pedagógicos são provisórios e estão marcados.

## 4. Mudanças de comportamento em algo que já existia

O pacote tinha só o esqueleto do `create-next-app`.

- A página inicial vazia virou a entrada do ECOSFERA.
- As fontes Geist (baixadas do Google no build) foram trocadas por Space Grotesk, Inter e JetBrains Mono locais.
- `globals.css`, `layout.tsx`, `next.config.ts`, `eslint.config.mjs`, `tsconfig.json` (alvo ES2022), `.gitignore` e `package.json` (scripts e dependências) foram reescritos.
- `pnpm-lock.yaml` mudou por causa das dependências.
- Não apaguei `src/app/Login.tsx` (vazio) nem os SVGs de exemplo em `public/`: não são meus. Estão sem uso (pedido P-10).

## 5. Riscos

1. **CI:** `pnpm install` sai com erro enquanto `esbuild` não for declarado em `allowBuilds` na raiz (pedido P-01). Isso deve quebrar o CI desta branch.
2. **Desempenho no hardware-alvo é desconhecido.** Se o nível baixo não bastar em Chromebooks antigos, o próximo passo é simplificar o fragment shader da superfície.
3. **Ordem das células** é hipótese. Se for outra, os campos aparecem embaralhados até ajustar um módulo.
4. **Decisão de shaders** diverge da leitura literal do Dossiê (WebGPU). Está em ADR, com o custo de voltar atrás.
5. **Dados sintéticos convincentes** podem ser confundidos com ciência. Há selo em toda tela; a fonte nunca deve ir a produção.
6. **Balanceamento e regras de jogo** vivem no cliente por enquanto.

## 6. Decisões em aberto (precisam de você ou da equipe)

1. Aceitar ou não o ADR FE-0001 (GLSL em WebGL 2 em vez de WebGPU agora).
2. Declarar `esbuild` em `allowBuilds` (P-01).
3. Onde fica a Especificação do Evolution Engine, e a confirmação da ordem das células.
4. Revisões da biologista, da equipe pedagógica e do designer.
5. Autorizar push e abertura de PR; autorizar a remoção dos arquivos sem uso.
6. Se os tokens sobem para `packages/ui`.

## 7. O que o backend precisa fornecer para substituir a fonte sintética

Está detalhado em `NECESSIDADES_DE_DADOS.md`. Em resumo: os campos por célula e os globais na ordem de células acordada; o quadro de observação da biosfera (linhagens com fenótipo, teia, filogenia, índices, fluxos dos ciclos); eventos com fase, local, telegrafia e cadeia causal; histórico por intervalo; um instante passado sob demanda; a prévia do Gênese; a aceitação dos comandos de ambiente; e o modo e nível de detalhe de cada atualização. No frontend, só muda a implementação de `PlanetStateSource`.
