# Relatório de verificação de ponta a ponta

Gerado por `scripts/e2e.mjs` em 2026-11-15, Chromium headless (WebGL por software), contra o build de produção.

## 1. Acessibilidade automática (axe-core, regras WCAG 2.1 A e AA)

| Tela | Tema | Violações | Regras violadas | Erros no console |
|---|---|---|---|---|
| Início | escuro | 0 | nenhuma | 0 |
| Jogo (HUD) | escuro | 0 | nenhuma | 0 |
| Jogo em modo texto | escuro | 0 | nenhuma | 0 |
| Gênese | escuro | 0 | nenhuma | 0 |
| Códex | escuro | 0 | nenhuma | 0 |
| Ficha de espécie | escuro | 0 | nenhuma | 0 |
| Pesquisa | escuro | 0 | nenhuma | 0 |
| Missões | escuro | 0 | nenhuma | 0 |
| Dados: séries | escuro | 0 | nenhuma | 0 |
| Dados: energia | escuro | 0 | nenhuma | 0 |
| Dados: teia | escuro | 0 | nenhuma | 0 |
| Dados: árvore | escuro | 0 | nenhuma | 0 |
| Dados: estrutura | escuro | 0 | nenhuma | 0 |
| Dados: ciclos | escuro | 0 | nenhuma | 0 |
| Configurações | escuro | 0 | nenhuma | 0 |
| Professor: turma | escuro | 0 | nenhuma | 0 |
| Professor: aluno | escuro | 0 | nenhuma | 0 |
| Professor: BNCC | escuro | 0 | nenhuma | 0 |
| Professor: gestão | escuro | 0 | nenhuma | 0 |
| Professor: desafios | escuro | 0 | nenhuma | 0 |
| Professor: comparar | escuro | 0 | nenhuma | 0 |
| Professor: exportar | escuro | 0 | nenhuma | 0 |
| Professor: mensagens | escuro | 0 | nenhuma | 0 |
| Professor: privacidade | escuro | 0 | nenhuma | 0 |
| Coordenação | escuro | 0 | nenhuma | 0 |
| Responsável | escuro | 0 | nenhuma | 0 |
| Laboratório | escuro | 0 | nenhuma | 0 |
| Jogo (HUD) | claro | 0 | nenhuma | 0 |
| Gênese | claro | 0 | nenhuma | 0 |
| Ficha de espécie | claro | 0 | nenhuma | 0 |
| Missões | claro | 0 | nenhuma | 0 |
| Dados: séries | claro | 0 | nenhuma | 0 |
| Dados: teia | claro | 0 | nenhuma | 0 |
| Professor: turma | claro | 0 | nenhuma | 0 |
| Responsável | claro | 0 | nenhuma | 0 |
| Jogo (HUD) | alto contraste | 0 | nenhuma | 0 |
| Gênese | alto contraste | 0 | nenhuma | 0 |
| Ficha de espécie | alto contraste | 0 | nenhuma | 0 |
| Missões | alto contraste | 0 | nenhuma | 0 |
| Dados: séries | alto contraste | 0 | nenhuma | 0 |
| Dados: teia | alto contraste | 0 | nenhuma | 0 |
| Professor: turma | alto contraste | 0 | nenhuma | 0 |
| Responsável | alto contraste | 0 | nenhuma | 0 |

Resumo: 43 combinações de tela e tema, 0 violações, 0 erros de console.

## 2. Fluxos só com teclado

- OK: O primeiro Tab leva ao link “Pular para o conteúdo”
- OK: Início → “Começar demonstração” com Tab e Enter abre o jogo
- OK: Planeta focado aceita setas e zoom por teclado sem erro
- OK: Enter seleciona o ponto no centro e abre a sonda com valores (Posição 34°, 73° Biomas Deserto Temperatura 7 °C Elevação 1.429 m)
- OK: Descrição textual do planeta presente para leitor de tela (Colonização Terrestre, ano 1.050. O planeta é um mundo temperado.  Temperatura média de 16 °C.  Atmosfera com 21,0% de oxigênio, 400 ppm de CO₂ e pres…)
- OK: Camada de temperatura ligada por teclado (aria-pressed)
- OK: Linha do tempo rola para o passado com a seta esquerda (mês 12600 → 12540)
- OK: Diálogo de intervenção recebe o foco ao abrir
- OK: Varredura confirmada por teclado fecha o diálogo
- OK: Esc fecha o diálogo
- OK: Tutor: a pergunta vem antes; a cadeia causal aparece só ao pedir a explicação (Pergunta no ano 1.045 · O que aconteceu com as espécies?  Há 17 linhagens vivas em 4 níveis tróficos. Há 1045 anos eram 0. O que acontece quando um espaço fica vazio e populações ficam separadas por m)
- OK: Códex: seleção de espécie por teclado abre a ficha
- OK: Abas dos dashboards mudam com as setas (padrão WAI-ARIA)

## 3. Estados das telas

- OK: Planeta sem vida: aviso com “Por quê?” (Não há vida no planeta agora. Isso pode acontecer, e tem uma causa. Por quê?)
- OK: Erro da fonte de dados: mensagem com “Tentar de novo”
- OK: Carregando: indicador com texto
- OK: Sem erros de console nesses estados
- OK: Fim de era: aviso com acesso ao relatório
- OK: Relatório de fim de era abre com três perguntas de reflexão
- OK: Vazio: Códex sem linhagens explica o motivo
- OK: Vazio: teia trófica sem vida explica o motivo
- OK: Cenário Sem Decompositores chega ao colapso por matéria presa (matéria presa = 1.00)
- OK: Console de laboratório fechado sem a flag de desenvolvimento
- OK: Guarda de papel (provisória) barra o estudante no painel do professor

## 4. Latência da ação ao feedback visual (RNF-002)

| Medida (12 ações de reflorestar) | p95 |
|---|---|
| Disparo da ondulação no ponto (síncrono ao gesto) | 0.4 ms |
| Ondulação desenhada (dois quadros depois) | 356 ms |
| Novo estado do planeta recebido da fonte | 131 ms |

- OK: Feedback visual local em até 1 s no p95, em WebGL por software (p95 = 356 ms)

**Total de falhas: 0.**
