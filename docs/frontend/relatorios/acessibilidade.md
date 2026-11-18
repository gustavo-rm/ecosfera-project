# Relatório de acessibilidade

## Resumo

| Verificação | Resultado | Como |
|---|---|---|
| Regras automáticas WCAG 2.1 A e AA | **0 violações** em 43 combinações de tela e tema | axe-core 4.14, `scripts/e2e.mjs` (detalhe em `e2e.md`) |
| Contraste dos tokens | Todos os pares de texto ≥ 4,5:1 e de interface ≥ 3:1, nos 4 temas | teste unitário sobre `tokens.css` |
| Paletas sob daltonismo | Sequenciais monotônicas; divergentes e séries separadas sob protanopia, deuteranopia e tritanopia | teste unitário com simulação (Machado et al.) e validador de paletas |
| Teclado | 14 fluxos de ponta a ponta passam | Playwright, sem mouse |
| Descrição textual do planeta | Presente e gerada do estado | teste unitário e checagem no navegador |
| Movimento reduzido | Sem rotação do planeta, sem rotação automática da câmera, tempo dos shaders parado (ondas, nuvens, lava, aurora), sem pulsos, texto do tutor de uma vez | revisão de código. A primeira versão deixava ondas, nuvens e a rotação automática ativas; a revisão independente apontou e foi corrigido. Não há teste automático. |
| Flashes | Nenhum efeito acima de 3 por segundo | por construção (ADR FE-0004); não medido com analisador |
| Erros no console | 0 em todas as telas | `scripts/e2e.mjs` |

**Confiança:** alta para o que é automatizável (contraste, papéis ARIA, nomes acessíveis, foco). **Não verificado:** uso com leitor de tela real (NVDA, ChromeVox, VoiceOver), teste com pessoas com deficiência e teste de usabilidade com crianças (RNF-022). Ferramentas automáticas cobrem só uma parte dos critérios da WCAG.

## O que a auditoria automática encontrou e foi corrigido

| Achado | Onde | Correção |
|---|---|---|
| Região rolável sem foco por teclado | Indicadores do HUD, modo texto, árvore de pesquisa | Contêiner focável com rótulo |
| Contraste 4,08:1 e 2,93:1 | Capacidades ausentes na ficha (opacidade reduzida) | Sem opacidade; estado dito em texto e ícone |
| Contraste 4,26:1 a 4,47:1 | Número sobre a cor do mapa de calor | Número em etiqueta neutra sobre a célula |
| `li` dentro de elemento com papel de painel de aba | Pesquisa | Papel movido para o contêiner |
| Elementos focáveis dentro de `role="img"` | Teia trófica e árvore | Gráficos interativos passam a ser `role="group"` |
| `aria-pressed` em `role="radio"` | Grupos de opção | Só `aria-checked` |
| Laranja e verde confundíveis em deuteranopia; azul e violeta em protanopia | Paleta escura das séries | Paleta trocada; cada série também tem tracejado |

## Como cada requisito é atendido

- **RNF-014 (WCAG 2.1 AA):** ver tabela acima; falta a parte manual.
- **RNF-015 (daltonismo):** três conjuntos de paleta (padrão, cividis, cinza); ícone, forma, rótulo e valor acompanham toda cor; hachura para "não revelado".
- **RNF-016 (baixa visão):** escala de fonte de 100%, 115% e 130%; alto contraste; zoom do navegador funciona (layout em `rem`).
- **RNF-017 (teclado):** câmera, seleção de ponto, camadas, linha do tempo, intervenções, tutor, abas, Códex e dashboards. Link "Pular para o conteúdo" em todas as páginas.
- **RNF-018 (leitor de tela):** descrição do planeta, anúncios de mudanças notáveis, modo texto, resumo em texto e tabela alternativa em cada gráfico.
- **RNF-019 (áudio):** não há áudio. A preferência existe, desligada, e a regra de legenda está registrada.
- **RNF-020 (contraste):** verificado por teste.
- **Alvos de toque:** botões, campos, seletores e controles deslizantes têm pelo menos 44 px (classe `.ec-btn`, `.ec-input`, `.ec-range`); os principais do HUD, 52 px. **Exceções conhecidas:** os links dentro de texto e de tabelas (nomes de alunos e de linhagens) e os rótulos clicáveis da árvore filogenética têm a altura da linha de texto.

## Limitações conhecidas

0. A revisão independente apontou itens que a ferramenta automática não vê. Corrigidos: região `aria-live` do tutor reanunciava a cada fragmento (agora anuncia uma vez, ao fim); linha do tempo com alvo de 28 px e passo inviável por teclado. **Não corrigidos:** o planeta (`role="application"`) captura Espaço e Esc quando focado; o planeta vem antes do cabeçalho na ordem de foco do jogo; nos grupos de opção (previsão, qualidade) não há foco itinerante com setas, cada opção é uma parada de Tab; no celular, os botões que abrem os painéis vêm depois dos painéis na ordem de foco.

1. A seleção por teclado no planeta escolhe o ponto no centro da tela.
2. Os nós da árvore filogenética são links dentro de SVG; a navegação por Tab segue a ordem das linhagens, não a do tempo.
3. **A camada de biomas depende de cor no globo.** São 13 classes; a redundância está fora do globo (legenda nomeada e sonda com o rótulo do ponto). As cores dos biomas não foram testadas sob simulação de daltonismo. É a exceção conhecida a "nunca só cor".
4. Em 390×844 (celular) o HUD é uma versão degradada: os painéis de ações e camadas abrem por botões e cobrem parte do planeta.
