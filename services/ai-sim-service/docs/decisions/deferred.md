# Decisões ADIADAS — camada instrucional, não motor

Correções validadas pela especialista que pertencem ao **Tutor / conteúdo (M6)**,
não ao motor de simulação. Registradas aqui para não se perderem entre marcos.

Nenhuma delas é rejeição: todas foram acatadas, e o adiamento é de LUGAR, não de
mérito. Implementá-las no motor seria pôr sequência didática dentro da física.

| # | Questão | O que foi validado | Onde pertence | Marco |
| --- | --- | --- | --- | --- |
| Q3 | Sequência adaptação ↔ cladogênese ao longo das eras | A ordem em que os dois fenômenos são APRESENTADOS ao aluno importa: adaptação primeiro, cladogênese depois, senão a especiação parece mágica | Currículo do Tutor / roteiro de eras | M6 |
| Q15 | Pequeno e grande ciclo da água | A narrativa deve distinguir o ciclo curto (evaporação↔precipitação) do longo (oceano↔gelo↔subterrâneo). O motor já modela os quatro reservatórios; o que falta é a NARRAÇÃO | Regras causais / texto do Tutor | M6 |
| Q12 | Progressão cadeias → teias alimentares por era | O aluno deve ver a teia se adensar ao longo do tempo, não recebê-la pronta. É progressão de APRESENTAÇÃO — a Ecology já resolve três níveis | Currículo do Tutor | M6 |
| Q2 | Linhagem como eixo de biodiversidade | Atada à decisão de coortes (P-01): sem identidade por espécie não há linhagem a narrar | Bloqueada por P-01 | pós-P-01 |

**Q2 depende de P-01** e não pode ser desatada antes dela.

---

## Oxigenação atmosférica / Grande Evento de Oxigenação — CIÊNCIA AUSENTE

**Registrado no M5.** O campo `atmosphere.oxygen` existia no world-state desde o
M1 e **nunca teve escritor**: nenhum Engine o produzia, a ponte não o mapeava, e
ele valia 0,0 em toda corrida. Foi REMOVIDO no M5 (`WORLD_STATE_VERSION` 4 → 5),
depois de varredura confirmar que não havia um único leitor no monorepo.

A remoção não é um recuo científico — é a recusa de fingir. Um campo zerado
permanente é pior que a ausência: sugere que o oxigênio está modelado e vale
zero, quando ele simplesmente não está modelado.

**O que falta, e por que importa.** O Grande Evento de Oxigenação (~2,4 Ga) é um
dos episódios mais pedagógicos da história do planeta: a fotossíntese oxigênica
transforma a atmosfera, extingue boa parte da vida anaeróbia que a produziu, e
abre o caminho para a vida complexa. É o exemplo canônico de a **vida mudar o
planeta**, e não só se adaptar a ele — o inverso da narrativa habitual, e
exatamente o tipo de reviravolta que a plataforma existe para ensinar.

Modelá-lo exige: produção de O₂ acoplada à biomassa fotossintética (nível
trófico produtor), sumidouros (oxidação de ferro e de metano), e o acoplamento ao
clima pelo metano — porque a queda do metano no GOE é o que dispara a glaciação
Huroniana. Nada disso é pequeno, e nenhum pedaço isolado ensina o fenômeno.

**Marco:** científico, próprio, junto ou depois do termostato de carbono (P-02),
com o qual compartilha a estrutura de reservatórios e fluxos.
