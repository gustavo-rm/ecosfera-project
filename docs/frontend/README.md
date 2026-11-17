# Frontend do ECOSFERA

Pacote: `apps/web-client` (Next.js 16, React 19, TypeScript, Three.js com react-three-fiber, Zustand, Tailwind 4, Recharts, Vitest).

O frontend roda inteiro sem backend. Os dados vêm de uma fonte sintética local, marcada na interface com o selo "Dados sintéticos".

## Como rodar

Requisitos: Node 22 ou mais recente e pnpm 11 (o repositório fixa `pnpm@11.15.1`).

```bash
pnpm install
```

```bash
pnpm --filter web-client dev
```

Abra `http://localhost:3000`. No modo de desenvolvimento a página inicial mostra o seletor de papel (estudante, professor, coordenação, responsável, desenvolvedor).

Observações:

- No Windows com Git Bash, mantenha o store do pnpm no mesmo drive do projeto (por exemplo `pnpm config set store-dir /f/.pnpm-store`) para evitar falha de hardlink.

## Rotas

| Rota | O que é |
|---|---|
| `/` | Entrada: demonstração e, em desenvolvimento, seletor de papel |
| `/jogo` | Jogo principal: planeta 3D e HUD |
| `/jogo/genese` | Criação do planeta, com prévia ao vivo |
| `/jogo/codex` | Códex, ficha da espécie (`?especie=`) e Diário do Mundo |
| `/jogo/pesquisa` | Árvores científica e tecnológica |
| `/jogo/missoes` | Missões, descobertas, previsões e progresso |
| `/jogo/dados` | Dashboards científicos (`?aba=series`, `energy`, `web`, `phylogeny`, `structure`, `cycles`, `progress`) |
| `/professor` e subrotas | Turma, aluno, BNCC, gestão, desafios, comparar, exportar, mensagens, privacidade |
| `/coordenacao`, `/responsavel` | Visões de coordenação e do responsável |
| `/configuracoes` | Acessibilidade e exibição |
| `/lab` | Console de laboratório (só com a flag de desenvolvimento) |
| `/lab/planeta` | Bancada do planeta controlada por URL (capturas e medições) |

Parâmetros de URL úteis: `?dev=1` liga a flag de desenvolvimento (fica salva; `?dev=0` desliga), `?papel=teacher`, `?tema=light`, `?contraste=high`, `?texto=1`, `?movimento=reduced`, `?paleta=cividis`. No jogo: `?cenario=catastrophe&tick=1900&still=1`.

## Verificação

Todos dentro de `apps/web-client`:

```bash
pnpm test
```

```bash
pnpm lint
```

```bash
pnpm typecheck
```

```bash
pnpm build
```

Os scripts abaixo usam o Chromium do Playwright contra o build de produção. Suba o servidor em outra aba (`pnpm start -- -p 3100`) e passe `BASE_URL=http://localhost:3100`:

| Script | O que faz | Saída |
|---|---|---|
| `pnpm e2e` | axe-core em cada tela e tema, fluxos de teclado, estados, latência | `docs/frontend/relatorios/e2e.md` |
| `pnpm perf` | Tempo de quadro por nível de qualidade, com limitação de CPU | `docs/frontend/relatorios/desempenho-medidas.md` |
| `pnpm catalog` | Folhas de contato do catálogo visual | `docs/frontend/catalogo/` |
| `pnpm size` | Tamanho transferido por rota contra o limite | terminal |
| `pnpm fixture` | Regera a fixture embarcada | `public/fixtures/terra-nivel3.json` |

## Mapa do código

```
src/core/         núcleo sem React
  mesh/           malha geodésica; cellOrder.ts é o único dono da ordem das células
  state/          estado visual interno (types.ts), catálogos, métricas de regime
  source/         porta de dados (port.ts), fonte sintética, fixtures, esboço do backend
  appearance/     estado → aparência (função pura), camadas, paletas, contraste
  a11y/           descrição textual do planeta
  evidence/       barramento local de evidências
src/store/        Zustand: planeta, jogo, preferências; buffer de instantâneos; IndexedDB
src/render/       react-three-fiber e shaders GLSL
src/ui/           componentes-base e ícones
src/features/     telas: hud, genesis, codex, research, missions, data, teacher, lab, shell, session
src/game/         catálogos de jogo e tutor por regras
src/i18n/         textos pt-BR; pedagogy.ts concentra os textos pedagógicos provisórios
scripts/          verificação, medição e catálogo
```

## Documentos desta pasta

`BRIEFING.md` (extrato dos documentos de origem), `PLANO.md`, `adr/`, `DECISOES.md`, `DIVERGENCIAS.md`, `PEDIDOS_A_OUTRAS_FRENTES.md`, `DESIGN_TOKENS.md`, `NECESSIDADES_DE_DADOS.md`, `REVISOES_PENDENTES_V2.md`, `ATIVOS.md`, `MATRIZ_DE_COBERTURA.md`, `relatorios/`, `catalogo/`, `RELATORIO_FINAL.md`.
