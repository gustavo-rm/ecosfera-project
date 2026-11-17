# FE-0004 — Estratégia de acessibilidade do planeta 3D

- Status: Aceito
- Data: 2026-11-14

## Contexto

Um `canvas` WebGL é opaco para tecnologia assistiva. RNF-014 a RNF-020 pedem WCAG 2.1 AA, teclado completo, descrição textual do estado do planeta e modos para daltonismo e baixa visão.

## Decisão

1. **Descrição gerada do estado.** `core/a11y/describe.ts` é uma função pura que transforma o estado em frases (era, temperatura, atmosfera, oceanos, biomas, vida, eventos). Ela alimenta o `aria-describedby` do planeta, o modo texto e os testes.
2. **Anúncios só do que é notável.** Uma região `aria-live` educada anuncia nova era, evento previsto ou em curso, extinção em massa e fim da vida, no máximo uma vez a cada 1,5 s.
3. **Modo texto.** Uma preferência troca o 3D por listas e tabelas com a mesma informação (resumo, regiões por faixa de latitude, linhagens vivas).
4. **Teclado completo no planeta.** O contêiner do canvas é focável e tem `role="application"`: setas giram, `+` e `-` aproximam e afastam, `Home` volta à vista inicial, `Enter` seleciona o ponto no centro, `F` foca a seleção, espaço pausa. Há também botões de câmera para toque.
5. **Nunca só cor (RNF-015).** Indicadores têm ícone, valor e seta de tendência. Camadas têm legenda com unidade e sonda com o valor. Séries de gráfico têm tracejado e rótulo além da cor. Regiões não reveladas são hachuradas.
6. **Paletas.** Sequenciais com luminância monotônica (viridis, cividis, cinza); divergente azul–laranja. Verificadas por simulação de protanopia, deuteranopia e tritanopia em teste unitário.
7. **Movimento e flashes.** `prefers-reduced-motion` e a preferência do app param rotação, ondas e pulsos. Relâmpagos são pulsos suaves com intervalo mínimo de 0,8 s; a onda de choque é um anel único. Nada pisca acima de 3 vezes por segundo.
8. **Diálogos** usam o elemento `<dialog>` nativo: armadilha de foco, `Esc` e retorno de foco vêm da plataforma.

## Consequências

- A seleção por teclado escolhe o ponto no centro da tela, não uma célula arbitrária; para chegar a um lugar, gira-se o planeta.
- Não foi feito teste com leitor de tela real nem com usuários (RNF-022). Ver `relatorios/acessibilidade.md`.
