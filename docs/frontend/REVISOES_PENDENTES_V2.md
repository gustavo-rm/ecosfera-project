# Revisões pendentes para a v2

Decisão do dono do projeto em 2026-11-15: as revisões da biologista, da equipe pedagógica e do designer de produto **não acontecem agora**; ficam para a v2. Este documento diz, para cada revisor, o que precisa de revisão e onde está.

Até a revisão, tudo o que está listado aqui continua **marcado como provisório** no código e na interface:

- A interface mostra o selo "Dados sintéticos" em todas as telas.
- Textos pedagógicos passam pelo componente `<Ped>` (`src/ui/kit.tsx`), que os sublinha em modo de desenvolvimento e os marca com `data-placeholder="pedagogical"`.
- No código, os pontos provisórios têm o comentário `PLACEHOLDER`.

Caminhos relativos a `apps/web-client/`.

## 1. Biologista (autoridade de domínio)

Regra do projeto: o frontend não inventa ciência. O que segue é aproximação ou rótulo provisório.

| O que revisar | Onde está | Observação |
|---|---|---|
| Rótulos dos 57 genes (Apêndice A) | `src/core/state/catalogs.ts`, array `GENES` | Transcritos do briefing; a revisão independente os comparou com o briefing e estão iguais. Conferir contra o Apêndice A original. |
| Rótulos de causa de morte e de estágio de vida | `src/i18n/messages/pt-BR/planet.ts`, chaves `cause.*` e `stage.*` | A Especificação não define rótulos em português. |
| Nomes e rótulos dos biomas, e a regra de classificação | `planet.ts`, chaves `biome.*`; `src/core/source/synthetic/engine.ts`, função `classifyBiome` | 13 classes inventadas para a interface, a partir de temperatura, chuva e altitude. |
| Nomes dos papéis tróficos e dos modos de especiação | `src/i18n/messages/pt-BR/common.ts`, chaves `role.*`; `planet.ts`, chaves `speciation.*` | |
| Nomes gerados das linhagens | `engine.ts`, constantes `GENUS` e `EPITHET` | Pseudo-latim gerado; a interface avisa que são provisórios. |
| Nomes e cadeias causais dos eventos | `planet.ts`, chaves `event.*`; `src/core/state/catalogs.ts`, `EVENT_DEFS` (campo `chain`); `pedagogy.ts`, chaves `chain.*` | Inclui dois eventos que o motor não cobre (pandemia e espécie invasora), mostrados como representação abstrata. |
| Instrumentos que "detectam" cada evento | `catalogs.ts`, `EVENT_DEFS` (campo `instrument`) | Escolha de interface. |
| Balanço de energia, efeito estufa, temperatura por latitude e altitude, umidade, gelo | `engine.ts`, método `atmosphereAt` e o laço de clima em `frameAt` | Fórmulas simples só para dar forma aos dados. |
| Luminosidade, cor e tamanho por tipo de estrela | `catalogs.ts`, `STAR_TABLE` | |
| Zona habitável e alertas de combinações inviáveis | `src/features/genesis/GenesisScreen.tsx`, funções `habitableZone` e a lista `warnings` | |
| Paleta de rochas por composição da crosta; cores de vegetação por clima | `catalogs.ts`, `CRUST_COLORS`; `src/core/appearance/appearance.ts` | Representação estilizada. |
| Cor do céu por composição da atmosfera | `appearance.ts`, função `computeUniforms` | Estilizada; a legenda diz isso. |
| Roteiros dos cinco cenários (linhagens, origens, extinções, presas, relações cíclicas) | `src/core/source/synthetic/scenarios.ts` | Só a forma dos dados, não é simulação. |
| Fenótipos gerados para a ficha da espécie | `engine.ts`, método `record` | Valores sorteados dentro dos domínios do Apêndice A. |
| Pirâmide de energia (cerca de 10% por nível) e estoques e fluxos dos ciclos | `engine.ts`, métodos `bioAt` e `cycles` | Unidades relativas. |
| Limiares das métricas de regime | `src/core/state/metrics.ts`, função `classifyRegime` | Faixas do briefing §6. |
| Efeito das intervenções (reflorestar, fertilizar, barreira, introduzir linhagem, suprimir evento) | `engine.ts`, tratamento de `modifiers` | Valores provisórios (ver `DECISOES.md`, D-25 e D-26). |
| Aparência dos organismos a partir do marcador de aparência | `src/render/Organisms.tsx` | Representação abstrata de coortes. |

## 2. Equipe pedagógica

| O que revisar | Onde está | Observação |
|---|---|---|
| **Todos os textos pedagógicos** | `src/i18n/messages/pt-BR/pedagogy.ts` (arquivo inteiro) | Linguagem, faixa etária e correção. |
| Dicas de primeiro uso | `pedagogy.ts`, chaves `onboarding.*`; lógica em `src/features/hud/panels.tsx`, componente `Onboarding` | Seis dicas, uma por vez. |
| Feedback causal e tutor por regras | `src/game/tutor.ts`; textos em `pedagogy.ts`, chaves `tutor.*` e `chain.*` | Cada resposta cita um dado, pergunta antes de explicar e aponta um próximo passo. |
| Explicações de colapso e de planeta sem vida | `pedagogy.ts`, chaves `state.*` e `why.*` | "Colapso é legítimo." |
| Ganho e custo de cada intervenção | `pedagogy.ts`, chaves `intervention.*` | |
| Painel de previsão | `pedagogy.ts`, chave `predict.intro`; `src/features/hud/dialogs.tsx` | |
| Perguntas de reflexão do relatório de era | `pedagogy.ts`, chaves `report.*` | |
| Descrições de conceitos das árvores, de missões e de descobertas | `pedagogy.ts`, chaves `research.*`, `mission.*`, `achievement.*`; regras em `src/game/catalog.ts` | Inclui os códigos BNCC atribuídos a cada missão. |
| Regras de "domínio demonstrado" e balanceamento da economia de ações | `src/game/catalog.ts` (`RESEARCH`, `INTERVENTIONS`) | Provisório (D-13). |
| Regra simulada do nível do jogador | `src/store/gameStore.ts`, fim de `onFrame` | Em produção vem da avaliação. |
| Textos explicativos dos dashboards e da ficha | `pedagogy.ts`, chaves `data.*`, `codex.*`, `genesis.*` | |
| Eventos de evidência e a competência que cada um sustenta | `src/core/evidence/bus.ts`; `docs/frontend/NECESSIDADES_DE_DADOS.md`, seção H | |
| **Painel do professor** | `src/features/teacher/screens.tsx`, `data.ts`; textos em `src/i18n/messages/pt-BR/teacher.ts` | Dez competências, tópicos de dificuldade, texto das recomendações da IA, mapeamento de evidências para habilidades BNCC (provisório), limiar de alerta. |
| Texto de consentimento do responsável | `teacher.ts`, chaves `guardian.*` | Precisa também de revisão jurídica. |

## 3. Designer de produto

| O que revisar | Onde está | Observação |
|---|---|---|
| Tokens de design: cor, tipografia, espaço, raio, sombra, alvos de toque | `src/styles/tokens.css`; `docs/frontend/DESIGN_TOKENS.md` | Contraste já verificado por teste; a escolha estética é proposta. |
| Cores de marca (verde-água, âmbar, azul-noite) e tema padrão | `tokens.css` | |
| Identidade visual: nome grafado, símbolo do globo, ícone do app | `src/features/shell/Menu.tsx`, `src/app/page.tsx`, `public/icons/icon.svg`, `public/manifest.webmanifest` | Proposta. |
| Conjunto de ícones | `src/ui/icons.tsx` | Traços simples desenhados para a entrega. |
| Ilustração | — | Não há ilustrações; o planeta é procedural. Definir se a v2 terá. |
| Componentes-base e classes `.ec-*` | `src/app/globals.css`, `src/ui/kit.tsx` | |
| Composição do HUD e das telas | `docs/frontend/catalogo/` (folhas 09 a 17) | Inclui a versão degradada de celular. |
| Paletas de dados e cores dos biomas | `src/core/appearance/palettes.ts`; `catalogs.ts`, `BIOME_COLORS` | As cores dos biomas não foram testadas sob daltonismo. |
| Direção de arte do planeta | `src/render/shaders/`; `docs/frontend/catalogo/01` a `08` | Nuvens, oceano, limbo, organismos e efeitos de evento. |
| Se os tokens sobem para `packages/ui` | — | Decisão conjunta com a arquitetura. |
