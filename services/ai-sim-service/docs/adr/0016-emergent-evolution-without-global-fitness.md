# ADR 0016 — Evolução emergente, sem função de aptidão global

## Status
Aceito. Abre o M3. Supera o **RF-031** (algoritmo genético com fitness global) na
camada de Engines, aplicando a decisão adicional do **ADR-ARCH-0001**. Depende do
**ADR 0013** (que declarou o Biota provisório e a fronteira dura) e do
**ADR 0012** (ciclos fechados). Referências: Dossiê v3 §10.4, Spec §3/§5.1/§5.3,
ADR-ARCH-0002 (Correção 2), ADR 0006.

## Contexto

O M2 fechou os ciclos físicos e entregou um **Biota provisório**, declarado como
tal no ADR 0013: uma curva logística determinística que crescia biomassa contra a
capacidade de suporte, sem espécies, sem genoma e sem seleção. Ele existia para
que a `BiotaSlice` tivesse dono e o ciclo do carbono tivesse sumidouro — não para
representar biologia.

O M3 substitui esse provisório pela biologia de verdade. A questão não é como
implementar um algoritmo evolutivo, e sim **qual** implementar: o RF-031 pedia um
AG com função de aptidão global, e o ADR-ARCH-0001 já havia registrado que esse
desenho é incompatível com o propósito da plataforma.

## Decisão

### 1. Não existe função de aptidão global

A seleção é **local**: cada coorte é avaliada contra o ambiente que encontra, não
contra as concorrentes. Não há número maximizado, torneio, ranking nem população
otimizada geração a geração.

A cadeia da decisão, registrada aqui para que ninguém a desfaça por engano:

```
RF-031 (AG com fitness global)
  → ADR-ARCH-0001 supera o fitness global: ele é TELEOLÓGICO. Um número que a
    população maximiza ensina que a evolução "mira" um ótimo — que é exatamente
    a concepção equivocada que a plataforma existe para desfazer.
  → M3 conclui que, sem fitness global, o DEAP não tem papel. O que ele oferece
    é maquinário de otimização populacional (`selTournament`, `cxBlend`,
    `creator.FitnessMax`), e otimização populacional é justamente o que foi
    proibido. Sobram ~50 linhas puras em `engines/evolution/domain.py`.
```

**Dispensar o DEAP não é economia de dependência, é consequência.** Mantê-lo
convidaria a reintroduzir o fitness pela porta dos fundos: as classes do
`creator` existem para serem maximizadas. Um contrato de import-linter —
*"O Evolution Engine nao usa framework de otimizacao"* — proíbe `deap` e `mesa`
em `engines.evolution`, de modo que a decisão é verificada no build e não
confiada à memória de quem revisa.

O que substitui:

```
excedente  = adequação_local − custo_de_manutenção − peso_predação × pressão
Δpopulação = taxa_de_crescimento × população × excedente
```

`adequação_local` é o **produto** dos fatores limitantes (lei do mínimo, Liebig
1840). Não é comparada entre espécies nem maximizada: é a probabilidade local de
a coorte se sustentar. Duas espécies podem prosperar ao mesmo tempo, ou perecer
ao mesmo tempo. A aptidão é o RESULTADO de sobreviver, não um alvo.

A mutação é **não-direcionada**: o desvio gaussiano não sabe se melhora ou piora
a adequação; o ambiente decide depois. Essa ordem é o ponto pedagógico.

### 2. A `BiotaSlice` da Spec §3 vira DUAS fatias

A Spec §3 lista literalmente uma fatia — `BiotaSlice (evolução/ecologia)`. Nós
dividimos em `BiotaSlice` (Evolution) + `EcologySlice` (Ecology). **É uma
divergência consciente da Spec, e o motivo é a própria moldura:**

- há **dois Engines produtores** (evolução e ecologia são ciências distintas com
  cadências distintas, e juntá-las num Engine só faria um módulo que ninguém
  consegue testar isoladamente);
- a moldura exige **um dono por fatia**, e `validate_graph` recusa no boot duas
  escritas na mesma.

Uma fatia com dois escritores não é uma pequena infração de estilo: o Canal A é
aditivo, e dois deltas sobre o mesmo campo somariam em vez de compor, com o
resultado dependendo silenciosamente da ordem de registro. Preferimos divergir da
letra da Spec a quebrar a invariante que a torna verificável.

`WORLD_STATE_VERSION` sobe 2 → 3, e o comentário de versão em `world_state.py`
registra a divergência no ponto onde alguém a encontraria.

**Por que a composição por espécie não está nas fatias.** `StateDelta.values` é
`Mapping[str, float]` e aditivo — uma lista de espécies não cabe nele. E o
ADR 0006 mantém as espécies fora do world-state deliberadamente, para que a
física seja bit-idêntica com a biologia ligada ou desligada. As fatias carregam
**escalares agregados** (biomassa, riqueza, genoma médio, biomassa por nível
trófico); a composição por espécie viaja pelo **Canal B** e é materializada no
códex a partir dos eventos, que carregam o genoma no `cause_detail`.

**Por que o genoma médio.** `tick()` precisa ser função pura do snapshot — é
disso que o replay bit-a-bit depende. Guardar a lista de espécies num atributo do
Engine o tornaria estatal e quebraria essa pureza. A formulação de genética
quantitativa (a comunidade é seu genoma médio, e a seleção move a média na
direção do ótimo local a uma taxa proporcional ao desvio) é emergente e
não-teleológica: a média **rastreia** o ambiente, não persegue um alvo.

### 3. Capacidade é LIMITE; biomassa é OCUPAÇÃO

O Resource é dono da `carrying_capacity` — o **teto** que o ambiente oferece. A
Evolution é dona da `biomass` — **quanto desse teto está preenchido**. Um é
limite, o outro é preenchimento.

- A Evolution **nunca** redefine capacidade.
- O Resource **nunca** escreve biomassa.

Não há dupla contagem porque as duas grandezas não medem a mesma coisa: contar as
duas não soma nada duas vezes, do mesmo modo que o tamanho de uma sala e o número
de pessoas nela não se somam. O que seria dupla contagem é a comunidade viver
**acima** do orçamento de forma sustentada — gastar um limite que o ambiente não
publicou. Isso é afirmado em teste
(`test_the_community_settles_inside_the_budget_it_was_given`).

A densidade-dependência que faz a biomassa parar de crescer é **emergente**: a
lotação corrói o excedente local até ele cruzar zero perto de `ocupação = 1`.
Nenhuma curva logística é imposta sobre a comunidade — essa era a ciência do
Biota provisório, e é justamente o que sai.

Esta é a fronteira onde um Engine futuro tende a se confundir, e por isso está
escrita aqui e afirmada em
`test_capacity_is_the_limit_and_biomass_is_the_occupancy`.

### 4. A `biota.biomass` troca de dono, e a troca é guardada

A biomassa era escrita pelo Biota provisório; passa a ser escrita pela Evolution.
Ela tem **dois leitores dentro do ciclo do carbono fechado no M2**: o sumidouro
biótico (Atmosphere) e o consumo de recurso (Resource).

Remover o Biota sem dar novo dono à biomassa não seria "uma fatia fica vazia":
seria abrir um buraco no ciclo do carbono **no modo silencioso do `solar_flux`**
(o defeito que o M2 encontrou). O sumidouro iria a zero sem erro algum, o CO₂
passaria a subir sem a absorção da vida, e `test_carbon_is_not_double_counted`
continuaria VERDE — porque a identidade contábil fecha igualmente bem com
`absorbed = 0`.

`tests/integration/test_biomass_reparenting.py` é o análogo do
`test_solar_flux_has_writer` do M2 e cobre as duas travas: **quem escreve** e
**com que defasagem se lê**. Cada guarda foi verificada contra o defeito que
existe para pegar — zerando a biomassa, os oito testes de carbono preexistentes
seguem verdes e só as guardas novas ficam vermelhas.

**A defasagem é DECLARADA, não acidental.** Atmosphere e Resource leem a biomassa
do tick anterior porque a Evolution roda no fim da ordem. Mas "naturalmente" é
acidente de ordenação, e uma reordenação futura quebraria o acoplamento em
silêncio. `test_biomass_read_is_lagged` afirma a **declaração**;
`test_the_declared_lag_matches_the_actual_tick_order` confere a declaração contra
a ordem **construída** (não contra outra constante); e
`test_the_lag_is_observable_in_the_trajectory` verifica o **efeito** na série.

### 5. `ENGINE_ORDER` passa a ser a única fonte da ordem do tick

Descoberto ao verificar a guarda acima: `ENGINE_ORDER` era **documentação**, e
`build_planet_engine` construía o registro a partir de uma lista de construtores
paralela. As duas podiam divergir em silêncio — a constante seguiria descrevendo
uma ordem que o tick deixou de obedecer, e todo teste escrito contra ela passaria
a atestar uma ficção.

O registro passa a ser construído **a partir de** `ENGINE_ORDER`, com conferência
de que cada `engine_id` casa com a posição que o nomeia. Trocar de posição na
constante agora muda o tick de verdade — e, quando a troca é ilegal,
`validate_graph` a recusa no boot.

### 6. A cadência da ecologia muda: `steps_per_tick`, não lote por era

O modelo trófico rodava um lote de 12 passos no fecho da era, sobre um
**instantâneo congelado** do início dela. Como Engine, ele roda no loop do tick,
`steps_per_tick` passos por tick (padrão 1). Com `era_length: 10`, o trabalho
total por era é equivalente — mas a ecologia passa a ler um ambiente
**atualizado entre os passos**.

**É melhor cientificamente e muda a trajetória numérica.** Registramos a
consequência explicitamente: qualquer baseline de replay da ecologia é **novo** a
partir daqui. Como o M3 é o marco que introduz a biota no world-state, não há
baseline anterior a preservar — o custo é zero hoje e seria alto depois, o que é
a razão de fazer a mudança agora e não no M4.

## Consequências

**Ganhamos.** A evolução emerge de interação local, que é o que o Dossiê promete
ensinar. Um estudante que aquece o planeta vê a extinção acontecer *porque* as
coortes especialistas não toleram a nova temperatura — não porque um número caiu
num ranking. O Engine é puro, testável sem framework, e ~50 linhas em vez de um
AG inteiro.

**Perdemos.** A comunidade é representada pelo genoma médio, não por uma lista de
indivíduos: fenômenos que dependem de estrutura populacional (deriva em população
pequena, seleção dependente de frequência) não aparecem. É limitação conhecida e
aceita — o Canal A não comporta a lista, e o códex a reconstrói a partir dos
eventos quando for preciso.

**Divergimos da Spec §3** numa fatia que virou duas, pelo motivo registrado em
(2). Quem for reconciliar a Spec deve mudar a Spec, não juntar as fatias.

**Dívida.** O caminho de biologia por era (`BiologyEngine`, DEAP, fitness global)
ainda existe em `simulation_engine/biology/` e alimenta o códex de espécies. Ele
contradiz esta decisão e precisa ser reparentado sobre os eventos do Evolution
Engine — está registrado no ADR 0017.
