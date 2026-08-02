# Evolution Engine

Seleção natural **emergente**: cada coorte responde ao ambiente que encontra, e a
biomassa é a consequência de ela se sustentar ou não. Substitui o Biota
provisório do M2, que crescia por uma curva logística imposta.

## Documentação científica

### O que este Engine NÃO tem, e por quê

Não há função de aptidão global, nem número maximizado, nem torneio, nem
população otimizada geração a geração. É a decisão central do M3, e a cadeia que
levou a ela está registrada para que ninguém a desfaça por engano:

```
RF-031 (algoritmo genético com fitness global)
  → ADR-ARCH-0001 supera o fitness global: ele é TELEOLÓGICO, e ensinaria que a
    evolução "mira" um ótimo — exatamente a concepção equivocada que a
    plataforma existe para desfazer
  → M3 conclui que, sem fitness global, o DEAP não tem papel: o que ele oferece
    é maquinário de otimização populacional, e otimização populacional é
    justamente o que foi proibido (ADR 0016)
```

O contrato de import-linter *"O Evolution Engine nao usa framework de
otimizacao"* proíbe `deap` e `mesa` neste pacote — a decisão é verificada no
build, não confiada à memória de quem revisa.

### Sobrevivência por condição local

```
excedente   = adequação_local − custo_de_manutenção − peso_predação × pressão
Δpopulação  = taxa_de_crescimento × população × excedente
```

`adequação_local` é o **produto** dos fatores que a coorte de fato enfrenta:

```
adequação = aptidão_térmica × aptidão_hídrica × aptidão_energética × lotação
```

É produto e não soma pela lei do mínimo (Liebig, 1840): um fator nulo inviabiliza
a coorte por mais favoráveis que sejam os outros.

**A diferença entre isto e uma função de fitness não é cosmética.** O número não
é comparado entre espécies nem usado para ordená-las: cada coorte é avaliada
contra o **ambiente**, não contra as concorrentes. Duas espécies podem prosperar
ao mesmo tempo, ou perecer ao mesmo tempo; não há competição por um posto num
ranking. A "aptidão" é o RESULTADO de sobreviver, não um alvo perseguido.

| Fator | Forma | Leitura biológica |
| --- | --- | --- |
| térmico | gaussiana centrada em `temp_optimum`, largura `temp_tolerance` | especialistas despencam com pequenas variações; generalistas resistem |
| hídrico | satura em `water_need` | mais água que o necessário não ajuda |
| energético | satura em `energy_reference`, **só para produtores** | o consumidor come da cadeia trófica, não da irradiância |
| lotação | `1 / (1 + peso × ocupação)` | o orçamento cheio aperta a todos, sem eleger vencedor |

A **densidade-dependência é emergente**: a biomassa para de crescer porque a
lotação corrói o excedente até cruzar zero, não porque uma curva logística a
tenha travado. `crowding_weight` está calibrado para que esse cruzamento ocorra
perto de `ocupação = 1`.

### Mutação não-direcionada

O desvio gaussiano por traço **não sabe** se melhora ou piora a adequação; é o
ambiente, depois, que decide quem se sustenta. Essa ordem é o ponto pedagógico, e
é o oposto de uma busca guiada por objetivo. O sigma é fração da **amplitude** de
cada traço — sem isso, um mesmo valor moveria `metabolism` (faixa 0,05–3) e
`temp_optimum` (faixa −40–80) em escalas incomparáveis.

Quando a linhagem se distancia da ancestral além de `speciation_threshold`, é
**especiação**: uma espécie nova no códex, não um ponto melhor num espaço de
busca.

### Por que a comunidade é o genoma médio

`tick()` precisa ser função pura do snapshot — é disso que o replay bit-a-bit
depende. Guardar a lista de espécies num atributo do Engine o tornaria estatal e
quebraria essa pureza; e a lista não cabe no Canal A, que é aditivo e de floats.

A saída é a formulação de **genética quantitativa**: a comunidade é seu genoma
médio, e a seleção move essa média na direção do ótimo local a uma taxa
proporcional ao desvio. É emergente e não-teleológica — a média **rastreia** o
ambiente, não persegue um alvo, e volta a se mover quando o ambiente muda. A
composição por espécie é materializada no códex a partir dos eventos, que
carregam o genoma no `cause_detail` (ADR 0016).

### Abiogênese

A primeira vida surge quando `carrying_capacity ≥ abiogenesis_capacity` (35,0) —
o mesmo limiar do Biota provisório, que por sua vez veio do `life` determinístico
(a cadeia `h ≥ 0,35` ⟺ `capacidade ≥ 35` continua valendo). O fundador nasce
**adaptado ao mundo que o recebeu**, e não com um genoma arbitrário para um
otimizador consertar depois: a vida não surge ruim e melhora, ela surge de um
ambiente que a comportava.

O marco `LIFE_EMERGED` da linha do tempo passa a ser emitido aqui.

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `evolution` |
| escreve | `BiotaSlice` (`biomass`, `species_richness`, `mean_*` do genoma) |
| lê (mesmo tick) | `ResourceSlice` (`carrying_capacity`, `water_available`, `energy_available`), `ClimateSlice.temperature` |
| lê (defasado) | `EcologySlice.predation_pressure` |
| eventos | `LifeEmerged`, `SpeciationOccurred`, `SpeciesExtinct`, `TraitShift` |
| parâmetros | `params.yaml` (versionado) |
| posição no tick | 8ª — depois do ambiente resolvido, antes da Ecology |

**Fronteira com o Resource.** O Resource é dono da **capacidade** (o teto que o
ambiente oferece); este Engine é dono da **biomassa** (a ocupação desse teto). Um
é limite, o outro é preenchimento. Este Engine nunca redefine capacidade; o
Resource nunca escreve biomassa. É a fronteira onde um Engine futuro tende a se
confundir, e por isso ela é afirmada em teste
(`test_capacity_is_the_limit_and_biomass_is_the_occupancy`).

**Por que a predação é leitura defasada.** A Ecology roda DEPOIS deste Engine —
ela precisa da comunidade já resolvida para reparti-la entre níveis tróficos.
Logo a pressão de predação lida aqui é a do tick anterior. É a mesma técnica de
quebra de ciclo usada em `chemistry ⇄ atmosphere`, declarada em `lagged_reads`
para que o `validate_graph` a aceite.

**Por que duas fatias, e não uma.** A Spec §3 lista literalmente uma
`BiotaSlice (evolução/ecologia)`. Dividimos em `BiotaSlice` + `EcologySlice`
porque há **dois Engines produtores** e a moldura exige um dono por fatia —
`validate_graph` recusa no boot duas escritas na mesma. A divergência está
registrada no ADR 0016 e no comentário de versão do `world_state.py`.
