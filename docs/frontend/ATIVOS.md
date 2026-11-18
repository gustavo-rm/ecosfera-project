# Ativos externos

O planeta, o céu, os organismos e os efeitos são 100% procedurais. Não há modelos GLB, texturas de imagem nem áudio.

| Ativo | Uso | Licença | Origem |
|---|---|---|---|
| Space Grotesk (variável) | Títulos | SIL Open Font License 1.1 | pacote `@fontsource-variable/space-grotesk` |
| Inter (variável) | Texto | SIL Open Font License 1.1 | pacote `@fontsource-variable/inter` |
| JetBrains Mono (variável) | Números e dados | SIL Open Font License 1.1 | pacote `@fontsource-variable/jetbrains-mono` |
| Ícones | Interface | Desenhados para este projeto (`src/ui/icons.tsx`) | Proposta, sujeita à revisão do designer |
| Paletas viridis e cividis | Mapas | CC0 / domínio público (pontos de controle) | Matplotlib; cividis de Nuñez, Anderton e Renslow (2018) |
| Paleta Okabe–Ito | Séries (tema claro) | Uso livre | Okabe e Ito (2008) |
| Matrizes de simulação de daltonismo | Testes | Publicação científica | Machado, Oliveira e Fernandes (2009) |

Dependências de execução, todas com licença permissiva (MIT, salvo indicação): `next`, `react`, `react-dom`, `three`, `@react-three/fiber`, `@react-three/drei` (declarada antes desta entrega; não é importada hoje), `zustand`, `recharts`. De desenvolvimento: `vitest`, `playwright` (Apache-2.0), `axe-core` (MPL-2.0, só em testes), `sharp` (Apache-2.0), `eslint`, `tailwindcss`, `typescript`.
