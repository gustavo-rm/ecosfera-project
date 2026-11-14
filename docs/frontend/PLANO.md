# Plano do frontend (documento vivo)

Estado em 2026-11-14, ao fim da primeira entrega.

| Fase | Estado | Evidência |
|---|---|---|
| 0. Reconhecimento | Feito | `BRIEFING.md`, `DIVERGENCIAS.md`, ADR FE-0001 |
| 1. Fundação | Feito | tokens, i18n, store, porta de dados, fonte sintética, console |
| 2. Fatia vertical | Feito | planeta, HUD, camadas, linha do tempo; medidas em `relatorios/desempenho.md` |
| 3. Vida e eventos | Feito | `catalogo/06-eventos.jpg`, `07-qualidade-e-zoom.jpg`, cinco cenários |
| 4. Telas do estudante | Feito | `catalogo/14-telas-estudante.jpg` |
| 5. Dashboards científicos | Feito | `catalogo/15-dashboards.jpg` |
| 6. Professor, coordenação, responsável | Feito com dados simulados | `catalogo/16-professor.jpg` |
| 7. Acabamento | Feito, com as pendências abaixo | `relatorios/`, `MATRIZ_DE_COBERTURA.md`, `RELATORIO_FINAL.md` |

## Próximos passos, em ordem

1. Medir em Chromebook real e calibrar o governador de qualidade.
2. Teste com leitor de tela e teste de usabilidade com a faixa etária (RNF-022).
3. Revisões pendentes: autoridade de domínio (placeholders científicos), equipe pedagógica (`pedagogy.ts`), designer (marca e ícones).
4. Confirmar com o motor a ordem das células; começar o contrato a partir de `NECESSIDADES_DE_DADOS.md`.
5. Implementar `BackendSource` quando o contrato existir; depois autenticação real e sincronização (ADR FE-0006).
6. Lacunas conhecidas de interface: vegetação e fauna sem animação; chuva em zoom e correntes oceânicas não feitas; comparação lado a lado em 3D; mensagens do professor ainda não aparecem para o aluno; imagens de referência com tolerância ainda não entram no CI.
7. Testar Firefox e Safari.
8. Pendências menores da revisão independente: ordem de foco do jogo, navegação por setas nos grupos de opção, liberação de geometrias, uso do campo `solar_flux`, teste das cores de biomas sob daltonismo, remoção dos atalhos de URL antes de uso com alunos.
9. Artefato visual: anel fino e escuro na borda da casca da atmosfera, visível contra o fundo.
