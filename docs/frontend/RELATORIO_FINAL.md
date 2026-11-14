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
| Testes unitários (Vitest) | 60 testes passam. Incluem um teste por linha da tabela "variável → efeito", contraste dos tokens nos 4 temas, paletas sob simulação de daltonismo, descrição textual, métricas de regime, buffer, fixtures, exportações e integridade das chaves de texto. |
| Tipos e lint | `tsc` sem erros; ESLint sem erros (avisos menores). |
| Build de produção | 22 rotas estáticas. |
| Ponta a ponta (Playwright) | 68 checagens passam: axe-core com 0 violações em 43 combinações de tela e tema; 14 fluxos só com teclado; estados carregando, vazio, erro, sem vida e fim de era; 0 erros de console. Relatório legível em `relatorios/e2e.md`. |
| Desempenho | Medido em WebGL por software: 34,8 FPS com qualidade automática em 1366×768 (28,2 FPS com CPU limitada em 4×). Latência da ação ao feedback: p95 de 268 ms. |
| Tamanho do pacote | Dentro dos limites definidos: jogo com 469 KiB comprimidos de JS e CSS. |
| Catálogo visual | 17 folhas de contato, olhadas e criticadas ao longo do trabalho; várias rodadas de correção no planeta. |

A verificação automática encontrou defeitos reais, que foram corrigidos: contraste insuficiente em três lugares, regiões roláveis sem foco, papéis ARIA incorretos, uma paleta de séries confundível em daltonismo, a resolução dinâmica que era desfeita a cada atualização e uma corrida na retomada de sessão.

## 2.1 Revisão independente

Um agente que não viu o trabalho revisou o diff, os princípios, a tabela "variável → efeito" e os relatórios. Ele confirmou: o escopo do diff (só `apps/web-client`, `docs/frontend` e o lockfile), os 57 rótulos do Apêndice A idênticos ao briefing, a ausência de URL externa ou chamada de rede, o catálogo de intervenções só sobre o ambiente, o barramento de evidências sem dados pessoais e a estrutura do PDF.

Ele também achou defeitos que eu não tinha visto. **Corrigidos:**

1. As estações estavam invertidas na imagem em relação aos dados (o hemisfério em verão ficava na noite polar).
2. A retomada do jogo salvo reconstruía outro planeta fora do cenário Gênese (semente errada).
3. Rolar a linha do tempo repunha pontos de ação e repetia avisos; era possível agir no passado.
4. Suprimir um evento só mudava a imagem, não a mortalidade.
5. No console de laboratório, forçar variáveis de vida não agia com o tempo parado; e o resultado das populações dependia da ordem de consulta.
6. Corrida ao abrir o Gênese com jogo salvo (duas inicializações).
7. O service worker guardava respostas com erro e qualquer GET.
8. A ficha mostrava "ticks" ao estudante.
9. Movimento reduzido deixava ondas, nuvens e a rotação automática da câmera.
10. Linhagem introduzida ignorava o ponto escolhido; no nível baixo de qualidade não havia organismos; a linha do tempo era inviável por teclado; o tutor reanunciava cada fragmento ao leitor de tela; o CSV não neutralizava fórmulas; o PDF trocava "₂" por "?".

**Apontados e não corrigidos** (registrados nos relatórios): o planeta captura Espaço e Esc quando focado; ordem de foco do jogo; grupos de opção sem navegação por setas; geometrias de organismos, efeitos e céu não liberadas; o campo `solar_flux` não alimenta aparência; a camada de biomas depende de cor no globo; os atalhos de URL funcionam para qualquer pessoa.

A revisão também mostrou afirmações minhas que não se sustentavam ("nada é alocado por quadro", "todo controle tem 44 px", "movimento reduzido respeitado", cobertura da tabela descrita como total). Os relatórios e a matriz foram corrigidos; a matriz ganhou uma avaliação linha a linha.

## 3. O que NÃO foi verificado, e por quê

1. **Chromebook real (RNF-001).** Não tenho o hardware. WebGL por software é um piso pessimista e não representa o alvo.
2. **Leitor de tela real e usuários reais (RNF-018, RNF-022).** Só verificação automática e por código.
3. **Aparelhos de toque.** Gestos de pinça e arrasto foram implementados, mas só exercitados por emulação de viewport.
4. **Firefox e Safari (RNF-023).** Só Chromium.
5. **Fidelidade à Especificação do Evolution Engine.** O documento não está no repositório. Trabalhei pelo briefing; não pude conferir o briefing contra o original, nem a ordem das células da malha.
6. **Instalação como PWA e uso offline.** Só a estrutura.
7. **O PDF exportado em um leitor com interface.** A estrutura é testada, e o revisor abriu o arquivo com duas bibliotecas de leitura; não foi visto em tela.
9. **Regras de jogo ao rolar o tempo e retomada de sessão** foram corrigidas após a revisão, mas não têm teste automático próprio.
10. **A imagem final** não tem teste automático: os testes cobrem o mapeamento de estado para canais e uniformes; a imagem foi conferida a olho nas folhas de contato.
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
7. **Atalhos de URL** (`?dev=1`, `?papel=`) dão acesso ao console e ao seletor de papel a qualquer pessoa. São para demonstração e precisam sair antes de uso com alunos.

## 6. Decisões em aberto (precisam de você ou da equipe)

1. Aceitar ou não o ADR FE-0001 (GLSL em WebGL 2 em vez de WebGPU agora).
2. Declarar `esbuild` em `allowBuilds` (P-01).
3. Onde fica a Especificação do Evolution Engine, e a confirmação da ordem das células.
4. Revisões da biologista, da equipe pedagógica e do designer.
5. Autorizar push e abertura de PR; autorizar a remoção dos arquivos sem uso.
6. Se os tokens sobem para `packages/ui`.

## 7. O que o backend precisa fornecer para substituir a fonte sintética

Está detalhado em `NECESSIDADES_DE_DADOS.md`. Em resumo: os campos por célula e os globais na ordem de células acordada; o quadro de observação da biosfera (linhagens com fenótipo, teia, filogenia, índices, fluxos dos ciclos); eventos com fase, local, telegrafia e cadeia causal; histórico por intervalo; um instante passado sob demanda; a prévia do Gênese; a aceitação dos comandos de ambiente; e o modo e nível de detalhe de cada atualização. No frontend, só muda a implementação de `PlanetStateSource`.
