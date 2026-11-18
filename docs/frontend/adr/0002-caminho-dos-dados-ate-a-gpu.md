# FE-0002 — Caminho dos dados até a GPU: canais por célula como atributos de vértice, com fusão na GPU

- Status: Aceito
- Data: 2026-11-14

## Contexto

O motor trabalha em malha geodésica (DEC-04, §6.2): no nível 5 são 10 242 células, e cada célula coincide com um vértice de uma icosfera de subdivisão 5. O planeta precisa reagir a dezenas de campos por célula, com transição suave (0,5 a 1,5 s), sem re-renderizar React por quadro e sem alocar memória no laço de render.

Opções: (1) texturas de dados amostradas no fragment shader; (2) atributos de vértice na própria malha geodésica.

## Decisão

1. **Uma célula é um vértice.** A malha de render tem a mesma topologia da malha de dados. A ordem das células é definida em um único módulo, `core/mesh/cellOrder.ts`, marcado com `TODO(contract)`.
2. **Quatro canais de 4 floats por célula** (`A`, `B`, `C`, `D`), produzidos por `computeAppearance` (função pura): altura, gelo, lava, nuvem; cor estilizada e vegetação; valor da camada de dados, revelado, floração, fogo; seca, tempestade, matéria escura, destaque. Mais um gradiente de relevo para as normais.
3. **Fusão na GPU.** Cada canal existe em dois atributos (anterior e alvo). Um uniforme `uBlend` vai de 0 a 1 em 0,9 s (1,6 s em saltos entre eras). Quando chega um estado novo no meio da transição, o estado visível é "assado" no atributo anterior e a fusão recomeça. Não há trabalho por quadro na CPU.
4. **Atualização parcial.** Um canal só é reenviado se o conteúdo mudou. Campos que não mudam (elevação, máscaras de evento vazias) são reutilizados por referência desde a fonte de dados.
5. **Nível de detalhe pela propriedade de prefixo.** Os vértices do nível L são os primeiros do nível L+1. Uma malha de render mais grossa lê um prefixo dos dados; uma mais fina faz a média dos dois vértices-pais.
6. **Detalhe sem custo de dados.** O fragment shader soma ruído procedural determinístico por semente, que cresce com o zoom.

## Consequências

- 8 atributos de canal + gradiente + posição = 10 atributos (o WebGL 2 garante 16).
- No nível 5, os atributos ocupam cerca de 1,5 MiB. Um envio completo acontece no máximo 5 vezes por segundo no nível médio.
- Camadas categóricas (biomas) usam a cor do canal `B`; nas bordas entre classes a cor é interpolada. A sonda mostra sempre o rótulo exato.
- Se o motor passar a enviar campos em outra ordem de células, muda só `cellOrder.ts` (ou uma tabela de permutação ali).
