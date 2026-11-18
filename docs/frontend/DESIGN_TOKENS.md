# Tokens de design do ECOSFERA (definição inicial)

Fonte única: `apps/web-client/src/styles/tokens.css`. Os tokens são propriedades CSS com o prefixo `--ec-`. Os temas e modos são classes `.ec-*` aplicadas ao elemento `<html>`. O Tailwind enxerga os tokens por `@theme` em `globals.css` (por exemplo `bg-ec-surface`, `text-ec-muted`). Componentes-base usam classes `.ec-*` (`.ec-btn`, `.ec-panel`, `.ec-card`, `.ec-chip`, `.ec-input`, `.ec-table`, `.ec-meter`).

Não havia tokens `.ec-*` no repositório em nenhuma branch. Esta é a primeira definição.

> **Proposta sujeita à revisão do designer de produto:** as cores de marca (verde-água primário, âmbar de destaque, azul-noite de fundo), o conjunto de ícones e o símbolo do globo. São funcionais e cumprem os critérios abaixo, mas não são identidade visual aprovada.

## Temas e modos

| Classe | Efeito |
|---|---|
| `.ec-theme-dark` (padrão) | Fundo azul-noite. É o padrão porque o planeta é o protagonista e o espaço é escuro; painéis claros ofuscariam o globo. |
| `.ec-theme-light` | Para telas de leitura (professor, relatórios) e ambientes muito iluminados. |
| `.ec-contrast-high` | Combina com qualquer tema. Fundo e texto em preto e branco puros, bordas em contraste total, sem transparência nem desfoque nos painéis. |
| `.ec-motion-reduced` / `.ec-motion-system` | Remove animações e transições. O modo "system" segue `prefers-reduced-motion`. |
| `--ec-font-scale` | 1, 1,15 ou 1,3. Escala o `rem` inteiro (RNF-016). |

## Cor

| Token | Escuro | Claro | Uso |
|---|---|---|---|
| `--ec-bg` | `#070b16` | `#f3f5fa` | Fundo da página |
| `--ec-surface`, `-2`, `-3` | `#101726`, `#182135`, `#24304a` | `#ffffff`, `#e9edf5`, `#d9e0ec` | Painéis, controles, estado pressionado |
| `--ec-border` | `#62759a` | `#66758f` | Contorno de controles (precisa de 3:1) |
| `--ec-border-subtle` | `#2c3a55` | `#c3ccdb` | Divisores decorativos (sem exigência de contraste) |
| `--ec-text`, `--ec-text-muted` | `#eef2fa`, `#aebad0` | `#0f1626`, `#45526b` | Texto principal e secundário |
| `--ec-primary`, `--ec-on-primary` | `#3ddc97`, `#04231a` | `#08714e`, `#ffffff` | Ação principal, seleção |
| `--ec-accent`, `--ec-on-accent` | `#ffb454`, `#2b1700` | `#8f5200`, `#ffffff` | Destaque secundário |
| `--ec-info`, `--ec-success`, `--ec-warning`, `--ec-danger` | `#6cb6ff`, `#3ddc97`, `#f2cc60`, `#ff8078` | `#0b5cad`, `#08714e`, `#7a5600`, `#b3261e` | Estados. Sempre com ícone e texto. |
| `--ec-focus` | `#ffd866` | `#0b3fbf` | Anel de foco de 3 px |
| `--ec-synthetic` | `#f2cc60` | `#7a5600` | Selo "dados sintéticos" e sublinhado de texto provisório |
| `--ec-chart-grid` | `#33425f` | `#c3ccdb` | Grade recessiva dos gráficos |

**Contraste medido** (teste `core/__tests__/misc.test.ts`, que falha se algum par cair abaixo do mínimo; a lista completa fica em `apps/web-client/.reports/contrast.txt`):

| Par | Escuro | Claro | Alto contraste escuro | Alto contraste claro | Mínimo |
|---|---|---|---|---|---|
| texto / fundo | 17,5 | 16,6 | 21,0 | 21,0 | 4,5 |
| texto secundário / superfície 2 | 8,2 | 6,7 | 15,6 | 14,7 | 4,5 |
| texto sobre primário | 9,4 | 6,0 | 16,4 | 10,0 | 4,5 |
| aviso / superfície | 11,6 | 6,7 | 16,4 | 11,4 | 4,5 |
| perigo / superfície | 7,3 | 6,5 | 12,0 | 9,8 | 4,5 |
| borda / superfície | 3,9 | 4,7 | 21,0 | 21,0 | 3,0 |
| foco / superfície | 13,0 | 8,5 | 19,6 | 10,7 | 3,0 |

Justificativas:

- **Verde-água como primário:** remete à biosfera e tem contraste alto sobre azul-noite. No tema claro ele escurece para manter 4,5:1 com texto branco.
- **Duas bordas:** `--ec-border` é a única que carrega informação (limite de um controle) e por isso cumpre 3:1. `--ec-border-subtle` é decoração.
- **Cores de estado nunca sozinhas (RNF-015):** todo selo tem ícone e texto; tendências usam seta; alertas usam ícone e a palavra.

## Cor em dados

| Uso | Paleta | Por quê |
|---|---|---|
| Camadas sequenciais | viridis (padrão), cividis, cinza | Luminância monotônica: a ordem se lê mesmo sem matiz. Cividis foi desenhada para daltonismo. |
| Camadas divergentes (temperatura, elevação, pH) | azul → neutro claro → laranja; azul → amarelo | Dois polos e meio neutro. Azul e laranja se distinguem nos três tipos comuns de daltonismo. |
| Biomas (categórica) | 13 cores estilizadas | Com 13 classes a cor não basta: a legenda nomeia cada uma e a sonda mostra o rótulo do ponto. |
| Séries de gráfico, tema claro | Okabe–Ito (6) | Validada pelo validador de paletas (faixa de luminosidade, croma, separação sob daltonismo). |
| Séries de gráfico, tema escuro | azul, laranja, água, amarelo, magenta, cinza claro | A simulação mostrou verde e laranja confundíveis, e azul e violeta também; a sexta cor virou cinza. |

Toda série tem também um padrão de tracejado e legenda. Barras de extinção têm hachura. Células de mapa de calor trazem o número em uma etiqueta neutra, porque o tom médio da viridis não dá 4,5:1 com tinta preta nem branca.

## Tipografia

| Token | Valor | Uso |
|---|---|---|
| `--ec-font-display` | Space Grotesk | Títulos, nome da era |
| `--ec-font-body` | Inter | Texto e controles |
| `--ec-font-mono` | JetBrains Mono, algarismos tabulares | Valores, para que números não "dancem" ao mudar |
| `--ec-text-xs` a `--ec-text-3xl` | 0,75 / 0,875 / 1 / 1,125 / 1,375 / 1,75 / 2,25 rem | Escala |

As três fontes são servidas pelo próprio app (pacotes `@fontsource-variable`, licença OFL). O menor texto é 12 px e só aparece em rótulos auxiliares.

## Espaço, raio, sombra, alvo de toque

| Token | Valor |
|---|---|
| `--ec-space-1` a `-8` | 4, 8, 12, 16, 24, 32, 48, 64 px (base de 4 px) |
| `--ec-radius-sm`, `-md`, `-lg`, `-pill` | 6, 10, 16, 999 px |
| `--ec-shadow-1`, `-2` | sombra curta; sombra de painel flutuante |
| `--ec-target` | 44 px: altura e largura mínimas de todo controle (WCAG 2.5.5) |
| `--ec-target-lg` | 52 px: controles principais do HUD, para toque em Chromebook e tablet |
| `--ec-focus-width` | 3 px |
| `--ec-duration-fast`, `--ec-duration` | 120 ms, 220 ms (zeram com movimento reduzido) |

## O que falta decidir com o designer

- Marca, logotipo e ilustrações.
- Se o tema padrão das telas do professor deve ser o claro.
- Ícones definitivos (hoje são traços simples desenhados para a entrega).
- Se os tokens sobem para `packages/ui`.
