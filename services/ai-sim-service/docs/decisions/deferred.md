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

---

## Especiação praticamente INALCANÇÁVEL até a Fase 2

**Registrado na Fase 0** (`docs/decisions/PLANO_EVOLUCAO_ECOSFERA.md`, requisito
`BIO-002`; ADR 0023). Não é bug, e não é adiamento de mérito: é a consequência
medida de a Fase 0 ter corrigido o SIGNIFICADO do evento sem tocar na MECÂNICA.

**O número.** `speciation_threshold` vale 0,12; a distância genética de um passo
de mutação vale ~0,02 (σ = 2% da amplitude, seis traços, norma normalizada).
Cruzar o limiar num único tick exige um desvio de ~6 σ. Medido: uma corrida de
200 ticks emite 39 eventos na semente 2027 e 76 na 99 — **nenhum** de
especiação.

**O que ESTÁ entregue.** O evento, quando ocorre, está correto: registra um
ancestral comum e duas linhagens (`BIO-001`), carrega a causa que o disparou
(`BIO-002`, parte pré-M6), é bit-a-bit reproduzível pela semente e atravessa a
persistência sem perda. O que falta não é a descrição, é a frequência.

**Por que não foi corrigido na Fase 0.** Baixar o limiar trataria o sintoma:
tornaria o evento comum sem torná-lo gradual, e mudaria a dinâmica de toda a
biologia dentro do mesmo marco que corrige o envelope — impossibilitando separar
o que quebrou o quê. A correção certa é a **mecânica gradual** do `BIO-002`:
divergência acumulada ao longo de gerações, em vez de exigida de um salto.

**Consequência para o M6, e é a que importa registrar.** "Explicar uma
especiação" será RARO até a Fase 2. Um Tutor que quase nunca fala de especiação é
o comportamento ESPERADO deste modelo, não um defeito de prompt nem de RAG. Quem
for avaliar o Tutor precisa saber disso antes de caçar um bug que não existe.

**Marco:** Fase 2 do Plano de Evolução (espécies e especiação completas), pós-M6.

---

## `GEOGRAPHIC_BARRIER` declarada SEM EMISSOR até a Fase 2

**Registrado na Fase 0** (`BIO-002`; ADR 0023). A causa está no enum
`EvolutionCauseCode` e na guarda `CAUSES_WITHOUT_EMITTER`, e **nada a emite**.

**Por que declarar uma causa que ninguém produz.** A barreira geográfica é a
causa canônica da especiação alopátrica — é o mecanismo que qualquer material
didático apresenta primeiro, e o vocabulário que o Tutor vai precisar. Omiti-la
do enum faria o vocabulário parecer completo quando não é.

**Por que ninguém a produz.** O modelo não tem geografia: toda `location` é
`region_id: global`. Não há região, logo não há barreira a detectar. Emitir a
causa hoje seria inventar um diagnóstico que o estado da simulação não sustenta —
e um `cause_code` sem base no estado é exatamente o que o ADR-ARCH-0002 proíbe ao
exigir que a explicação seja ancorada no observável.

**O que impede o esquecimento.** `CAUSES_WITHOUT_EMITTER` é verificada por teste:
todo membro do enum ou tem emissor no Engine ou está registrado ali, e um código
que ganhe emissor sem sair do registro também falha. O buraco é RUIDOSO — que é a
lição do `solar_flux` do M2, um campo sem escritor que valeu zero em silêncio por
um marco inteiro. Este registro preserva o PORQUÊ da exceção, que o teste sozinho
não conta.

**Marco:** Fase 2 do Plano de Evolução, junto com a mecânica gradual — a barreira
geográfica é um dos gatilhos que a especiação gradual passa a ter para modelar.

---

## A suíte sem o extra `sim`: 26 falhas HERDADAS do caminho dormente

**Registrado na Fase 0**, para que "não piora" deixe de ser afirmação e passe a
ser número reproduzível.

O extra `sim` (`deap`, `mesa`, `scipy`, `networkx`) é opcional por decisão
(ADR 0017, parte 1): os nove Engines importam e rodam sem ele. O que NÃO roda sem
ele é o **caminho de biologia por era** — o AG do DEAP e o ABM do Mesa —, que
está DORMENTE desde o M3 (`biology_enabled=False`) e sai no tempo 3 do ADR 0017.

**Medição, com os dois hashes:**

| | commit | failed | passed | skipped | xfailed |
| --- | --- | --- | --- | --- | --- |
| basal (antes da Fase 0) | `7d80534` | **26** | 643 | 12 | 1 |
| topo da Fase 0 | `fa43623`+ | **26** | 943 | 19 | 1 |

Não só o número: o **conjunto** de testes que falham é idêntico entre os dois
(comparado por node id). Os 26 vivem em sete arquivos, todos do caminho dormente:
`test_advance_era_with_biology`, `test_replay_with_biology`, `test_ecology_cost`,
`test_deterministic_layer_unaffected`, `test_ecology_conserves_biomass`,
`test_ecology_predator_prey`, `test_evolution_determinism`.

Reproduzir:

```
uv sync --extra infra --group dev   # sem --extra sim
uv run pytest
```

**Como ler o DoD.** "Verde com e sem `sim`" significa: **com** `sim`, verde
absoluto; **sem** `sim`, o mesmo conjunto de falhas do basal — herdadas, não
introduzidas. O CI roda com `sim`, então a árvore de merge é verde absoluto.

**Quando isto some.** Quando o caminho B for removido (ADR 0017, tempo 3), que
depende do tempo 2 e da camada de espécies decidida no ADR 0024 — Fase 2 do
Plano. Até lá o número certo é 26, e qualquer outro é achado.
