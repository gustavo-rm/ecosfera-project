# ECOSFERA — ai-sim-service

Serviço Python/FastAPI de **simulação científica** e **IA** do projeto ECOSFERA.
Respeita a fronteira **determinístico × IA** (Dossiê PD&I §8, GDD §10): a IA medeia
contexto, ritmo e explicação; **nunca** falsifica a ciência que o aluno precisa entender.

## O que já roda
Base do MVP / Inc 1 (walking skeleton) + **núcleo de simulação determinístico**
com **linha do tempo, replay e persistência real** + **ecossistemas emergentes**
(evolução por AG e ecologia por ABM). Prefixo da API: `/ai/api/v1`.

| Método | Rota | Descrição | RF |
| --- | --- | --- | --- |
| POST | `/simulation/planets` | Cria e configura um planeta a partir de uma semente | RF-011/012 |
| POST | `/simulation/planets/{planet_id}/tick` | Avança 1 tick determinístico: novo estado + cadeia causal | RF-013/014/023 |
| GET | `/simulation/planets/{planet_id}` | Estado atual do planeta | RF-016 |
| POST | `/simulation/planets/{planet_id}/advance-era` | Avança uma **era** inteira: checkpoint append-only + marcos + cadeia causal | RF-013/014/016 |
| GET | `/simulation/planets/{planet_id}/timeline` | Lista as eras e seus metadados | RF-016 |
| GET | `/simulation/planets/{planet_id}/eras/{era}` | **Reconstrói** o estado da era por replay determinístico | RF-016/023 |
| GET | `/simulation/planets/{planet_id}/species` | **Códex** de espécies do planeta (GDD §11) | RF-031 |
| GET | `/simulation/planets/{planet_id}/species/{species_id}` | **Genoma inspecionável** de uma espécie | RF-031 |
| GET | `/simulation/planets/{planet_id}/ecology` | Snapshot populacional + capacidade de suporte | RF-032 |
| GET | `/simulation/jobs/{job_id}` | Status do job de evolução (backend assíncrono) | RF-031 |
| POST | `/ai/explain` | Explicação causal por **regras determinísticas** (vira LLM+RAG no Inc 6) | RF-033/039 |
| POST | `/assessment/events` | Ingestão de **telemetria** com bloqueio de **consentimento** LGPD | RF-071 / RNF-009 |
| GET | `/health` | Liveness do serviço | — |
| GET | `/metrics` | Métricas Prometheus (fora do prefixo `/ai/api/v1`) | — |

Tick e era compõem o motor de simulação (que **produz** as observações) com o motor
de feedback causal existente (que **explica** o delta) — mesmo contrato de
`/ai/explain` (`source="rules"`, `grounded=true`).

**Determinismo (RF-023) é verificável em produção:** `GET .../eras/{era}` reexecuta o
motor a partir do checkpoint anterior e responde `matches_checkpoint`, indicando se a
reconstrução bateu com o estado gravado na época.

### Ordem do tick
Desde o M4 o tick roda por **dez Engines**, sem adaptador nem fatia órfã
(ADR 0012/0013/0014/0016/0018):

```
astronomy -> geology -> chemistry -> atmosphere -> climate -> hydrology
          -> resource -> evolution -> ecology -> event
```

`ENGINE_ORDER` é a **única** fonte dessa ordem: o registro é construído a partir
dela, então trocar de posição muda o tick de verdade.

A ordem original do núcleo monolítico (`physics -> chemistry -> climate ->
geology -> ocean -> life`, ADR 0004) deixou de existir junto com o
`TickOrchestrator`. Detalhes da nova ordem, e a razão física de cada posição, na
seção da moldura abaixo.

### Camada emergente — biologia (Inc 3)
Evolução (**AG/DEAP**) e ecologia (**ABM/Mesa**) vivem em
`simulation_engine/biology/`, não em `ai_engine/`: são emergentes, mas são
subsistemas de simulação (ADR 0006). Regra de ouro (Dossiê §8, GDD §10):

> a IA governa o **emergente**, mas **nunca falsifica a ciência**.

Na prática isso é uma regra de escrita — a biologia **lê** o `PlanetState` e a
capacidade de suporte que o **Resource Engine** publica, e **nunca os escreve**.
Desde o M2 a capacidade chega pelo campo `carrying_capacity` do estado, e não de
um subsistema de vida instanciado à parte: existe UM número, calculado num lugar
só, e é o mesmo que a biologia consome (ADR 0013). Ligar ou desligar `ECOSFERA_BIOLOGY_ENABLED` não muda um bit da
física, química, clima ou geologia para a mesma semente (verificado em
`tests/unit/test_deterministic_layer_unaffected.py`).

O comportamento é **emergente porém reproduzível por seed** (RF-023): cada era
deriva sua semente de (semente do planeta, era), então o replay reconstrói o
mesmo códex e as mesmas populações. As explicações causais dos resultados
biológicos saem do **motor de regras** de sempre — sem LLM, que só chega no Inc 6.

## Moldura de Engines — o único caminho de simulação (M0 → M3)
A arquitetura de Engines do Dossiê v3 §10.4 (ADR-ARCH-0001) foi adotada de dentro
para fora. O M0 entregou a moldura; o M1 entregou os três primeiros Engines
científicos e o primeiro feedback físico real; o M2 fechou os ciclos
determinísticos e aposentou o caminho legado (ADR 0012/0013/0014); o **M3 trocou
o Biota provisório por evolução emergente e dinâmica trófica** (ADR 0016/0017).

```
shared_kernel/         world-state e deltas (§3), envelope de evento (§4), porta
                       Engine + contexto de tick (§5.2), RNG semeado, contrato de
                       observabilidade (§6), replay (§7)
engines/planet/        Planet Engine — orquestra, e não conhece Engine algum
engines/composition.py registra os nove Engines na ordem de acoplamento
engines/bridge.py      tradução PlanetState <-> WorldStateSnapshot
engines/astronomy/     órbita (Verlet) e irradiância incidente          (M2)
engines/geology/       vulcanismo, relevo e a FONTE de carbono          (M1)
engines/chemistry/     troca ar<->oceano, pH, nutrientes e N/P/S        (M2)
engines/atmosphere/    estoque de CO2 e forçamento radiativo log        (M1)
engines/climate/       temperatura a partir do forçamento               (M1)
engines/hydrology/     quatro reservatórios de água e a criosfera       (M2)
engines/resource/      capacidade de suporte (lei do mínimo de Liebig)  (M2)
engines/evolution/     seleção local emergente, sem fitness global      (M3)
engines/ecology/       níveis tróficos e predação (pirâmide de Elton)    (M3)
engines/event/         eventos extraordinários + o Diretor determinístico (M4)
engines/noop/          Engine trivial que prova a moldura (critério do M0, §8)
```

### Ordem de acoplamento
```
astronomy → geology → chemistry → atmosphere → climate → hydrology
          → resource → evolution → ecology → event
```
Cada posição tem razão física: a insolação é a entrada de energia de tudo abaixo,
a geologia desgaseifica, a química publica a troca com o oceano, a atmosfera
integra o carbono já debitado, o clima converte forçamento em temperatura, a água
se move com o calor recém-resolvido, o recurso traduz o ambiente em capacidade de
suporte, a evolução decide quanto dele a comunidade ocupa, a ecologia reparte
essa ocupação entre níveis tróficos, e o **Event** fecha o tick decidindo se um
acontecimento extraordinário cabe no mundo que acabou de se resolver.

A ordem é **verificada no boot**, não apenas documentada: `validate_graph` recusa
qualquer leitura para trás que não esteja declarada em `lagged_reads`.

### Os feedbacks modelados
```
vulcanismo (geology) → +CO2 (atmosphere) → +forçamento → +temperatura (climate)
                            ↕ troca ar<->oceano (chemistry)
temperatura → evaporação/degelo (hydrology) → albedo → temperatura   [defasado]
água + nutriente + energia + calor → capacidade (resource) → biomassa (evolution)
biomassa → repartição trófica e predação (ecology)
predação → custo de sobrevivência (evolution)                        [defasado]
biomassa → absorção de carbono (atmosphere)                          [defasado]
```
Cada seta cruza fronteira de Engine **somente pelo world-state**. Nenhum Engine
importa outro nem lê seu estado interno — verificado por teste e por
`import-linter`. Nada disso está programado como regra: **emerge** da composição.

Ciência de referência (detalhada no README de cada Engine):

| Fenômeno | Formulação | Referência |
| --- | --- | --- |
| Fonte de CO₂ | desgaseificação ∝ vulcanismo | Walker, Hays & Kasting (1981) |
| Termostato | intemperismo ∝ estoque | Walker, Hays & Kasting (1981) |
| Forçamento | ΔF = 5,35·ln(C/C₀) | Myhre et al. (1998) |
| Temperatura | balanço de energia de caixa única | Budyko (1969); Sellers (1969) |
| Troca ar–oceano | lei de Henry linearizada | Sabine et al. (2004) |
| Evaporação | Clausius–Clapeyron linearizada | — |
| Nutriente limitante | lei do mínimo | Liebig (1840) |
| Crescimento da vida | logístico até a capacidade | Verhulst (1838) |

### Os dois ciclos fechados (M2)
**Água.** Os cinco fluxos apenas MOVEM massa entre `ocean`, `ice`, `vapour` e
`freshwater`; a soma é conservada dentro da tolerância declarada. É invariante de
runtime (`ConservedTotal`) e **não repara**: saber que a soma se moveu não diz de
qual reservatório tirar a diferença, e escolher um esconderia o defeito.

**Carbono.** Um fluxo, dois livros, sinais opostos: `air_sea_flux > 0` significa
que o oceano absorve, a química soma ao próprio reservatório e a atmosfera
subtrai o mesmo número. Não é invariante de runtime — a identidade atravessa duas
fatias com donos diferentes, e verificá-la no Planet Engine exigiria que ele
contivesse ciência. Vive em `tests/integration/test_closed_cycles.py` (ADR 0012).

**Dois canais**, nunca misturados: world-state + deltas por tick (Canal A,
acoplamento físico contínuo) e domain events append-only (Canal B, ocorrências
notáveis). Consumidores assinam **apenas** o Canal B. O Canal B registra
TRAVESSIA de patamar, nunca o contínuo — testar o valor corrente contra um limiar
emitiria evento em todo tick, porque uma fatia nasce zerada.

**O loop é síncrono; a borda de I/O é assíncrona** (ADR 0008). A fronteira
síncrono/assíncrono é a mesma fronteira determinístico/observável — `async` no
loop traria a ordem de escalonamento como variável oculta e o replay bit-a-bit
deixaria de valer.

**A observabilidade é lateral e nunca realimenta a simulação** (ADR 0009): o sink
é acionado depois de o tick estar composto e fechado, e estourar o orçamento por
tick emite um `DiagnosticEvent` sem alterar um bit do resultado.

| Variável | Valores | Efeito |
| --- | --- | --- |
| `ECOSFERA_TRACING_ENABLED` | `false` (default) / `true` | spans da moldura (OTel adiado) |

### Não há mais flag, nem rollback — e é deliberado
`ECOSFERA_ENGINES_FRAMEWORK` foi **removida** no M2 junto com o
`LegacySubsystemAdapter` e os seis subsistemas migrados. Não existe um segundo
motor para uma flag escolher.

Isso custou o rollback para a ciência anterior ao M1, e a perda é consciente
(ADR 0014): a flag nunca foi um modo equivalente — o efeito estufa linear não
satura, e "voltar" sempre significou rodar ciência que sabemos ser pior. **A
reversibilidade que importa é o replay determinístico**, que continua íntegro:
dada uma semente e um checkpoint, a trajetória se recompõe bit a bit.

### Onde ficam os parâmetros
Cada Engine carrega o próprio `params.yaml` versionado, co-locado com o código
que o consome. `configs/simulation_params.yaml` guarda só o que NÃO pertence a
Engine algum: condições iniciais, faixas físicas, progressão de eras, orçamento
da moldura e os parâmetros da camada emergente.

```bash
uv run lint-imports    # fronteiras: Engine não importa Engine (6 contratos)
make run               # sobe pela moldura — o único caminho
```

### A evolução EMERGE — não há função de aptidão global (M3)
`engines/evolution/` implementa seleção **local**: cada coorte é avaliada contra o
ambiente que encontra, nunca contra as concorrentes. Não há número maximizado,
torneio, ranking nem população otimizada geração a geração.

A cadeia da decisão: o **RF-031** pedia um AG com fitness global; o
**ADR-ARCH-0001** o superou por ser teleológico (ensinaria que a evolução "mira"
um ótimo, que é a concepção equivocada que a plataforma existe para desfazer); e
o **M3** concluiu que, sem fitness global, o **DEAP não tem papel** — o que ele
oferece é maquinário de otimização populacional, justamente o que foi proibido.
Sobram ~50 linhas puras (ADR 0016).

Um contrato de import-linter proíbe `deap` e `mesa` em `engines.evolution`, e
`tests/unit/test_no_global_fitness.py` audita a FORMA do cálculo: nenhum
vocabulário de otimização sobrevive, `local_suitability` não tem parâmetro por
onde uma população pudesse entrar, e duas coortes não disputam posto em ranking
algum.

A `BiotaSlice` da Spec §3 virou **duas** fatias (`BiotaSlice` + `EcologySlice`)
porque há dois Engines produtores e a moldura exige um dono por fatia. A
divergência está registrada no ADR 0016.

**Dívida do M3:** o caminho de biologia por era (`simulation_engine/biology/`,
com AG e aptidão escalar) ainda existe, mas está **DORMENTE** desde o M4
(`biology_enabled=False`, guardado por `test_path_b_is_dormant`). O que fazer com
o códex está registrado em `docs/decisions/pending.md` — e **coortes por espécie
(DEC-04) estão explicitamente FORA de escopo** até essa decisão.

## Event Engine e o Diretor (M4)

O décimo Engine traz os acontecimentos extraordinários — meteoro, seca, incêndio,
era glacial, tempestade, supervulcanismo — e o **Diretor** que decide quais e
quando.

**A perturbação não é escrita onde cai.** Um meteoro esfria o clima, uma seca
seca a hidrologia — fatias que já têm dono, e a moldura admite um escritor por
fatia. Então o Event Engine possui a `EventSlice` e publica ali a perturbação
como escalar; cada Engine afetado **lê** e a incorpora à própria dinâmica. O
Event descreve a causa; quem decide o efeito é quem detém a grandeza (ADR 0018).

**O Diretor é puro e não aprende.** Decide a partir do world-state e de um RNG
semeado — nunca de logs, métricas ou do Event Store. Ler a trilha tornaria o
replay impossível, porque a trilha é efeito da execução e não entrada dela. Sem
RL, e a ausência é decisão registrada.

**Os eventos são TELEGRAFADOS** (RF-019/020): anunciados com antecedência pelo
`EventForecast` e expostos na `EventSlice` para a interface avisar o jogador. Um
evento sem aviso não ensina antecipação — ensina azar. O horizonte é por evento:
a era glacial avisa muito, o incêndio quase nada.

### A cadeia meteoro → extinção

```
MeteorImpact ─┬─ (EventSlice.dust/cooling) → Climate  → TemperatureShift
              └─ (EventSlice.catastrophic_mortality)  → SpeciesExtinct
                                                        cause=CATASTROPHIC_EVENT
```

Os dois braços fecham por `causation_id`, e a relação é **derivada** do Event
Store depois do fato — o `MeteorImpact` não declara consequências que podem não
acontecer.

### As três correções da especialista em Biologia

| # | Correção | Onde |
| --- | --- | --- |
| **Q5** | A aptidão é **CONTEXTUAL**, não inexistente. Nega-se a aptidão ABSOLUTA — o número único que ordenaria espécies fora de contexto | ADR 0019 §5 |
| **Q8** | Extinção **catastrófica** é independente de aptidão: uma espécie bem adaptada pode morrer num evento extremo, e o `cause_code` diz isso | ADR 0019 §1–§4 |
| **Q11** | Capacidade de suporte em **todos** os níveis tróficos, não só produtores | ADR 0019 §6 |

Rastreabilidade completa em `docs/decisions/tassia-validation.md`.

### Horizonte de jogo válido: ~500 ticks

**Dívida HERDADA, descoberta no M4 e anterior a ele (ADR 0020).** Não existe
equilíbrio de CO₂: além de ~500 ticks o carbono vira rampa — passa de 870 ppm e
ainda sobe em t=3000 — e em parte das sementes a biosfera colapsa sem retornar.

O M3 é igual ou pior, e a Q11 **não** é a causa (ela melhora a semente 99).
Ficou invisível porque nenhum teste passava de ~600 ticks: a suíte verifica
correção POR TICK, e o sistema derrapa com cada passo correto. Faltava a classe
de teste de **trajetória longa**.

Hipótese: falta a dependência TÉRMICA do intemperismo de silicatos, que fecha o
laço negativo (Walker/Hays/Kasting 1981). É marco científico próprio.

`test_baseline_planet_is_quasi_stationary` afirma o que é verdade — quase-
estacionariedade dentro do horizonte, em quatro sementes — e
`test_carbon_stable_long_horizon` fica como **`xfail` anotado**, para que a
dívida apareça no relatório de teste a cada execução em vez de sumir.

## Camada de Plataforma (M5)

Persistência e observabilidade deixaram de ser versão mínima. O que muda para
quem usa o serviço:

### Exportar e importar uma simulação

Uma simulação vira **arquivo** — atravessa máquinas. Carrega seed, versão dos
params, versão do world-state, checkpoints por era e o Canal B com o envelope §4
íntegro; serializa de forma determinística (dois exports da mesma corrida dão o
mesmo arquivo byte a byte, então dá para comparar por hash).

```python
from ecosfera_ai.shared_kernel.portable import SimulationExport

Path("planeta.json").write_text(artefato.to_json(indent=2))
recarregado = SimulationExport.from_json(Path("planeta.json").read_text())
```

Importar de uma versão de esquema diferente **falha alto**, em vez de degradar:
um import silenciosamente degradado daria um planeta parecido com o original, e a
diferença só apareceria como divergência de replay muito depois (ADR 0021).

### Exportar uma série temporal (e ver a dívida de carbono)

```python
from ecosfera_ai.shared_kernel.timeseries import collect

serie = collect(trilha_de_snapshots)
Path("carbono.csv").write_text(serie.to_csv())   # abre em qualquer planilha
```

Os termos do ciclo do carbono vêm **separados** — desgaseificação, estoque
atmosférico, oceano, solo, troca ar↔oceano, sumidouro biótico — porque ver o CO₂
subir diz QUE o carbono escapa, não ONDE.

> **A instabilidade de carbono segue DÍVIDA ABERTA** (ADR 0020), agora
> **instrumentada**: o M5 não a corrige, torna-a visível. O horizonte de jogo
> cientificamente válido continua ~500 ticks.

### As três projeções

Científica (o fenômeno) e técnica (o diagnóstico) **particionam** a trilha; a
educacional é do M6, e o M5 garante que o envelope já carrega tudo de que ela
precisará. O contrato de query — por planeta, era, correlação, causação,
`cause_code` — está pronto para o M6 assinar, sem consumidores (ADR 0022).

> O M6.0 **assinou** esse contrato: `ContextAssembler` o consome sem renegociar o
> formato e sem uma segunda leitura paralela (ADR 0025, seção abaixo). A visão
> educacional continua sendo renderizada acima do dossiê — não por ele.

### Pureza

A simulação **não lê** store, logs, métricas nem traces. Afirmado
estruturalmente (nenhum Engine importa a plataforma) e funcionalmente (rodar com
e sem sink dá trajetórias bit-a-bit idênticas).

### Smoke test

```bash
uv run python scripts/smoke_m4.py                    # com o extra `sim`
uv run --no-extra sim python scripts/smoke_m4.py     # só física
```

## Camada de Consumidores (M6.0) — a fundação factual, sem LLM

A camada de consumidores da Spec §1 **começa aqui**. O M6 introduz um LLM, e com
ele um defeito que nenhum marco anterior tinha: não determinístico, sem invariante
de correção, e que falha sem quebrar `assert` algum. Um planeta que perde massa
reprova um teste de conservação; um Tutor que narra uma extinção que não aconteceu
soa bem e é aceito.

Por isso o M6 roda em subetapas e o LLM entra o mais tarde possível. O princípio
que vale para todas elas:

> A verdade sobre o planeta do aluno é o **Event Store**. Um consumidor está
> **correto** quando o que ele afirma é derivável da trilha de eventos, e
> **alucina** quando não é.

### O que o M6.0 entrega

O **`FactualContext`**: dado um planeta e um recorte, o dossiê estruturado do que
de fato aconteceu — linha do tempo ordenada com os campos §4 íntegros, cadeias
causais nas duas direções, especiações, extinções e marcadores de era.

```python
from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.domain.consumers.factual_context import ContextSlice

dossie = await ContextAssembler(event_query).execute(planet_id, ContextSlice.of_era(2))

dossie.consequences_of(meteoro.event_id)   # descendo: causa -> consequências
dossie.ancestry                            # subindo: efeito -> raiz
dossie.extinctions[0].nature               # catastrophic | ecological (ADR 0019)
dossie.speciations[0].lineages             # duas linhagens IRMÃS de um ancestral
dossie.to_dict()                           # JSON inspecionável, sem uma linha de prosa
```

Três recortes: **por era**, **por janela de ticks** e **o contexto de um evento**
(ele, o que o causou e o que dele decorreu). Fatia vazia devolve dossiê vazio
**explícito** — nunca erro.

### O que ele deliberadamente NÃO faz

Nem uma frase, nem `cause_code` traduzido, nem faixa etária, nem BNCC. A prosa é
do consumidor de cima (ADR-ARCH-0002, Correção 1). A partir do momento em que o
dossiê narra, some a fronteira entre *o que aconteceu* e *como se conta* — e com
ela some o único critério que separa o Tutor certo do que inventa.

| Subetapa | Acrescenta | Não pode |
| --- | --- | --- |
| **M6.0** (feito) | o fato verificável | narrar |
| **M6.1** (feito) | frase por template — o **piso** que o LLM terá de bater | inventar fato |
| **M6.2** (feito) | RAG pedagógico: de onde vem o REGISTRO | inventar fato |
| M6.3 | LLM (Ollama) reescreve | decidir o que aconteceu |
| M6.4 | avaliação adversarial + guardrails | — |

### O que o M6.2 entrega — recuperação, e não geração

De onde o Tutor tira a VOZ. O corpus existe para ele **soar** como um professor
alinhado ao currículo, não para ele **saber** mais ciência — o fato continua
vindo do Event Store, e é inviolável.

```python
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase

# o atalho central: dado o cause_code de um evento REAL do planeta,
# quais regras de linguagem governam a forma de contá-lo
passagens = await retriever.for_cause_code("CATASTROPHIC_EVENT")
# -> VAL-Q8  "catástrofe é independente de aptidão" (Tássia, Q8)
#    VOC-006 "as duas famílias de extinção não se misturam" (ADR 0019)

passagens[0].source      # o documento de onde a regra saiu — auditoria
passagens[0].similarity  # o M6.4 vai calibrar confiança com isto
```

**Uma passagem recuperada NÃO é um fato**, e a garantia é de forma:
`RetrievedPassage` não tem `event_id`, `occurred_at` nem `cause_code`, não tem
parentesco com `DomainEvent`/`FactualContext`, e o `mypy` recusa passar uma onde
um fato é esperado — afirmado **rodando** o verificador, não deduzido.

Sem isso, no M6.3 uma passagem dizendo *"extinções catastróficas são independentes
de aptidão"* poderia ser lida como *"houve uma extinção catastrófica neste
planeta"*: fluente, pedagogicamente correta em tese, e falsa sobre o planeta da
criança.

### Como acrescentar uma entrada ao corpus

Edite `configs/pedagogical_corpus.yaml` — é YAML de propósito, para ser revisável
por quem entende de pedagogia **sem rodar código**. Toda entrada exige:

| Campo | Obrigatório | Por quê |
| --- | --- | --- |
| `source` | sempre | "por que o Tutor falou assim?" precisa de resposta documental |
| `license` | se `external_reference` | na dúvida sobre a procedência, o material fica de fora |
| `code_verified` | se `curriculum_objective` | preserva o "(conferir)" do Dossiê — código não conferido não vira certeza |

O banco recusa o que o YAML deixar passar: `NOT NULL` + `CHECK` na
migration 0006. **Nenhum conteúdo curricular se inventa** — os códigos BNCC são
conferidos, um a um, contra o texto do Dossiê.

Prioridade do corpus (ADR 0027): regras de linguagem da Fase 0 → correções
validadas pela especialista → objetivos BNCC citados no Dossiê → referências
externas com licença. Livros-texto gerais foram **rejeitados** como fonte
primária: empurram o registro para a voz de um manual universitário.

### O embedder é porta, e a de referência é a que roda no CI

O CI sincroniza sem o extra `ai`, então um teste de pgvector que dependesse de
`sentence-transformers` pularia justamente onde precisa rodar.
`DeterministicEmbedder` (léxico, `blake2b`, determinístico entre processos) é a
implementação de referência; `SentenceTransformerEmbedder`
(`paraphrase-multilingual-mpnet-base-v2`, 768-dim, multilíngue) é a de produção.

O nome do modelo entra na chave primária e no `WHERE` de toda consulta:
similaridade entre vetores de modelos diferentes não significa nada.

> **Limitação medida.** O embedder de referência é LÉXICO, não semântico, e o
> cosseno favorece entradas curtas — foi o roteiro de fumaça que mostrou, e a
> correção foi encurtar a entrada no corpus, não mexer no algoritmo. A
> similaridade é comparável DENTRO de uma consulta, não entre consultas de
> formatos diferentes; quem calibrar um limiar no M6.4 precisa saber disso.

```bash
uv run python scripts/smoke_m6_2.py    # imprime as passagens antes de afirmar
```

### O que o M6.1 entrega — a explicação, sem LLM

O dossiê vira português. É a Correção 1 do ADR-ARCH-0002 finalmente cumprida por
inteiro: o Engine dá o esqueleto causal como dado, o M6.0 o organiza, e aqui ele
vira frase.

```python
from ecosfera_ai.application.consumers.render_explanation import ExplainSliceUseCase
from ecosfera_ai.domain.consumers.explanation import Register

explicacao = await ExplainSliceUseCase(event_query, renderer).execute(
    planet_id, ContextSlice.of_era(2), Register.STANDARD
)

explicacao.summary          # a prosa, em ordem cronológica
explicacao.facts[0].text    # uma frase
explicacao.facts[0].grounding  # de onde CADA afirmação dela saiu
```

Exemplo de saída real (corrida de 400 ticks com meteoro):

> No ciclo 357, a queda de um meteoro eliminou a comunidade de uma só vez, por
> mais bem adaptada que ela estivesse ao ambiente em que vivia: um evento extremo
> como esse não escolhe quem sobrevive.
>
> No ciclo 315, uma população ancestral se dividiu em duas linhagens porque as
> populações passaram a viver de maneiras diferentes. As duas compartilham um
> ancestral comum e seguem caminhos separados a partir dele: são irmãs, e nenhuma
> das duas é a versão antiga da outra.

**A prosa é DADO versionado** (`configs/explanation_templates.yaml`): quem entende
de pedagogia corrige uma palavra sem abrir um módulo Python.

### Por que o piso vem antes do gerador

Quando o M6.3 puser um LLM neste caminho, *"o modelo está ajudando?"* precisa ter
resposta — e ela só existe se houver um ANTES contra o qual comparar. Sem piso,
qualquer saída fluente pareceria progresso.

E há um efeito colateral que vale mais que o piso: explicar por template é o teste
mais duro que o dossiê do M6.0 podia receber. **Nenhum template precisou de um
campo que o dossiê não tivesse** — o que é a evidência de que o M6.0 acertou o
escopo. Um buraco ali teria aparecido agora, com um template, em vez de duas
subetapas adiante, onde a mesma falta apareceria como "o LLM inventou".

### Um template também alucina

Não ter modelo generativo não é imunidade. Um template que dissesse "a espécie não
conseguiu se adaptar" numa extinção catastrófica afirma algo que o dossiê **não
contém** — e a criança fica com a concepção equivocada exatamente como ficaria se
um modelo o tivesse escrito. A diferença é a facilidade de auditar, não a
existência do risco.

Por isso cada frase carrega um `Grounding`, e o teste de ancoragem verifica, sem
depender do julgamento de ninguém: todo fato aponta para um evento do dossiê; todo
campo declarado resolve; todo número da frase veio de um slot derivável do dossiê;
e o `summary` é EXATAMENTE a junção dos fatos — um resumo que sintetizasse teria
de afirmar algo que nenhum fato isolado afirma.

### Um só narrador de eventos

`ExplainFromEventsUseCase` (vivo desde o M1) **evoluiu** em vez de ganhar um irmão.
Ele narrava propagando variáveis (`co2↑ ⇒ temperatura↑`), o que descartava a
identidade do evento e afirmava efeitos que o log pode não conter. Agora narra pelo
dossiê, com a atribuição causal saindo do `causation_id` real.

O motor de regras continua onde projetar é o serviço prestado — `/ai/explain`
(o cliente manda observações, não há trilha) e o recuo por delta agregado do
`advance-era`. Nenhum dos dois é narração de trilha (ADR 0026).

### Registro de leitura: a costura, não o sistema

`Register.STANDARD` e `Register.SIMPLE`. O `SIMPLE` existe hoje só para os três
fatos de maior risco pedagógico (as duas extinções e a especiação); nos demais o
renderizador **cai para o padrão** e declara o registro realmente usado. O M6.3
acrescenta registros linha a linha no YAML, sem tocar em assinatura — e sem
improvisar simplificação em tempo de execução, que é onde a frase erra.

Diferenciação etária de verdade é produto, depende do M6.2/M6.3 e **não** foi
construída aqui.

```bash
uv run python scripts/smoke_m6_1.py    # a explicação de uma corrida real
```

### Três garantias travadas na forma, e não na disciplina

* **Especiação é ancestral comum.** `SpeciationFact` tem um ancestral e **duas**
  linhagens irmãs, e recusa qualquer outra forma — inclusive a disfarçada, em que o
  ancestral reaparece como uma das linhagens. "A espécie A deu origem à B" é
  **inexprimível** (BIO-001, ADR 0023) — e continua sendo na PROSA: o template de
  especiação não tem slot de linhagem, então a frase A→B não tem onde encaixar os
  dois sujeitos que precisaria (ADR 0026).
* **Catastrófica ≠ ecológica.** A família da causa atravessa como dado, junto com o
  elo causal, que numa catástrofe aponta para o EVENTO e não para o clima do mesmo
  tick (ADR 0019).
* **Um planeta só.** O recorte passa pelo `EventStoreQuery` com `planet_id` sem
  default (ADR 0023). Um vazamento aqui faria o Tutor narrar, citando eventos reais,
  a catástrofe do planeta de outro aluno — ancorado, e inteiramente errado.

### Onde vive

`domain/consumers/` (modelo puro: dossiê, floresta causal, templates, narração) e
`application/consumers/` (casos de uso: montar o dossiê, renderizar a explicação),
na estratificação hexagonal que este serviço usa — e não num pacote `consumers/`
paralelo. O que a Spec §1 pede é a **fronteira**, e ela é barrada por
`import-linter`: o consumidor não alcança Engine, world-state nem infraestrutura, e
**não depende de LLM nem de RAG** — proibição que, desde o M6.1, cobre o caminho
inteiro de evento até prosa, inclusive `application/feedback`, que seria o atalho
mais curto para um gerador entrar sem ninguém notar.

> **Especiação é rara e isso é normal.** Até a Fase 2 o limiar exige ~6 σ de um
> passo de mutação: zero especiações em 200 ticks nas sementes 2027 e 99
> (`docs/decisions/deferred.md`). Uma era sem especiação alguma é o comportamento
> ESPERADO — quem for avaliar o Tutor precisa saber disso antes de caçar um bug que
> não existe.

```bash
uv run python scripts/smoke_m6_0.py                  # dossiê de uma corrida real
uv run --no-extra sim python scripts/smoke_m6_0.py
```

## Camada de Geração (M6.3) — o LLM reescreve, e não decide

O primeiro componente não-determinístico do serviço. Tudo o que veio antes existe
para que o trabalho dele seja estreito: **reescrever o piso do M6.1 no registro
que o M6.2 recupera.** Ele não decide o que aconteceu, não acrescenta fato e não
sobrepõe o Event Store (ADR 0028).

```
Event Store → FactualContext (M6.0) → Explanation (M6.1) ─┐
                                      ^ o QUE aconteceu   ├→ prompt → LLM → verificação → aluno
corpus      → RetrievedPassage (M6.2) ────────────────────┘            │        │
              ^ COMO se diz                                            └ falhou ┴→ piso do M6.1
```

### O contrato de ancoragem

O prompt entrega as duas metades ROTULADAS — `<fatos>` e `<registro>` — e declara
em texto qual delas é verdade. Um modelo que receba dois blocos sem hierarquia
declarada trata os dois como igualmente autoritativos, e a passagem que diz
"extinções catastróficas são independentes de aptidão" vira "houve uma extinção
catastrófica neste planeta".

A instrução vive em `configs/generation_prompt.yaml`, como dado versionado. Ajustar
a redação é a manutenção mais comum desta camada; se exigisse mexer na lógica de
geração, cada correção de palavra arriscaria o caminho de recuo.

### A verificação fica ENTRE a geração e o aluno

Não há caminho em que texto não verificado chegue lá. Confere-se:

* **números** — todo numeral da saída tem de aparecer no piso (omitir pode,
  acrescentar não);
* **formulação proibida** — as listas canônicas do BIO-005 e da aptidão absoluta;
* **acontecimento inventado** — falar de meteoro num planeta sem `MeteorImpact`.

Cobertura **parcial e declarada**: só tipos de evento com termo concreto próprio.
`TemperatureShift`, `PopulationDeclined` e `SpeciationOccurred` ficam de fora
porque o vocabulário deles é o vocabulário comum da explicação — está escrito no
próprio YAML, com o motivo.

### Como o recuo se comporta

Qualquer falha — rede, tempo esgotado, JSON malformado, corpo vazio, exceção do
adaptador, ou reprovação na verificação — entrega **o piso do M6.1 inteiro**, e
não uma versão degradada dele. Nenhuma exceção sobe: o comportamento correto
quando o modelo falha não é estourar, é entregar a explicação correta que já
existe.

`GeneratedExplanation` registra o que aconteceu: `fell_back`, `fallback_reason`, e
um veredito de **três** estados — passou, reprovado, e *não avaliado* (não houve
geração). Somar queda de rede à taxa de alucinação faria o M6.4 medir a
infraestrutura achando que mede o modelo.

### Arbitragem por categoria

O ADR 0027 mediu que a similaridade não distingue uma regra de vocabulário da
correção validada que diz o mesmo. Entre irmãs, **a regra de vocabulário entra
primeiro**; dentro da mesma categoria a similaridade continua mandando. O ganho é
reprodutibilidade: sem isso, trocar de embedder mudaria o prompt sem que nada de
factual tivesse mudado.

### Rodar

```bash
uv run python scripts/smoke_m6_3.py                  # sem Ollama: mostra o RECUO
ECOSFERA_OLLAMA_BASE_URL=http://localhost:11434 uv run python scripts/smoke_m6_3.py
docker compose --profile ai up -d ollama && docker compose exec ollama ollama pull llama3.1:8b
```

Os testes de geração real exigem um daemon Ollama. Sem ele PULAM; com
`ECOSFERA_REQUIRE_OLLAMA=1` (o job `generation-gate` do CI) a ausência vira
**FALHA** — mesma política que a persistência tem desde o M5.

## O arco M6, fechado (M6.4)

O Tutor tem, ponta a ponta, uma cadeia em que cada elo é verificável:

| Marco | Entrega | Garantia |
| --- | --- | --- |
| M6.0 | `FactualContext` | a verdade é o Event Store, escopada no planeta |
| M6.1 | explicação por template | piso auditável frase a frase, sem LLM |
| M6.2 | RAG pedagógico | registro, estruturalmente separado de fato |
| M6.3 | geração ancorada | o modelo reescreve; recuo ao piso em qualquer falha |
| M6.4 | avaliação adversarial | detecção fechada, cobertura declarada, taxa medida |

### O que o M6.4 acrescentou

**Fechou a lacuna do ADR 0028.** `SpeciationOccurred` passou a ser conferida por
identificador estrutural — o modelo nunca recebe id de linhagem, então um id na
prosa é invenção por construção. `TemperatureShift` e `PopulationDeclined` são
conferidas pelo par (assunto, direção) contra o delta do log, o que distingue
inventar o evento de contradizer a direção dele.

**Tornou a cobertura parte da resposta.** Cinco tipos seguem sem checagem de
invenção, e `DetectionCoverage` os nomeia em todo veredito: um aprovado parcial
diz "cobertura parcial", e não "passou".

**Passou a registrar as tentativas.** `var/generation_attempts.jsonl` acumula, em
append, cada geração — aprovada, reprovada ou sem geração. É de onde a taxa sai.

```bash
uv run python scripts/evaluate_m6_4.py                       # sem Ollama: só o registro
ECOSFERA_EVAL_MODELS=llama3.2:1b,llama3.1:8b   ECOSFERA_OLLAMA_BASE_URL=http://localhost:11434   uv run python scripts/evaluate_m6_4.py
```

### Como ler a taxa de aprovação

Três ressalvas, e nenhuma é opcional:

* **falhas de infraestrutura ficam fora do denominador** — recuo por rede não é
  alucinação, e somá-lo faria a taxa piorar quando o Ollama cai;
* **aprovação com cobertura parcial é contada à parte** da completa;
* **a cascata sai separada** — o piso dela é um parágrafo repetitivo de cinco
  frases (ADR 0028), e numa média única ninguém distingue "o modelo é pior" de "o
  texto que ele recebeu é difícil".

A medição **não é portão**: o CI exige que o relatório seja produzido e legível,
e não que ele alcance um número. Cobrar um limiar convidaria a ajustar o prompt
até alcançá-lo, que é otimizar a métrica em vez do sistema.

### O que o Tutor explicitamente NÃO faz

Não há interface do aluno: `apps/web-client` é esqueleto, nenhuma rota alcança a
geração, e não existe entrada de texto livre. Não há ajuste fino de modelo, nem
camada de espécies com identidade, nem defesa contra injeção de prompt — esta
última porque não há de onde injetar. O que a avaliação mede é FUNDAMENTAÇÃO, e
não qualidade pedagógica: passar significa que a prosa não inventou nada, e não
que ela ensina melhor que o piso do M6.1 (ADR 0029).

## Rodar
```bash
uv sync            # cria .venv e instala deps (modo inmemory, sem banco)
make run           # API em http://localhost:8000/docs
make check         # lint + fmt + mypy + import-linter + testes
make imports       # só as fronteiras da moldura de Engines
docker compose up  # infra local (postgres+pgvector, mongo, redis)
```

## Persistência
O backend é escolhido por **feature flag**; a porta `PlanetRepository` é a mesma
nos dois casos (ADR 0005), então nenhuma camada acima muda.

| `ECOSFERA_PERSISTENCE_BACKEND` | Uso |
| --- | --- |
| `inmemory` (default) | testes e dev — sobe **sem** o extra `infra` instalado |
| `postgres` | staging/prod — exige `uv sync --extra infra` |

```bash
# 1. Suba o banco e aplique as migrations (schema `simulation`)
docker compose up -d postgres
uv sync --extra infra
export DATABASE_URL="postgresql+asyncpg://ecosfera:ecosfera@localhost:5432/ecosfera"
uv run python -m alembic upgrade head     # NUNCA o binário direto (evita conda)
uv run python -m alembic upgrade head --sql   # opcional: só gera o SQL, sem banco

# 2. Suba a API apontando para o Postgres
ECOSFERA_PERSISTENCE_BACKEND=postgres \
ECOSFERA_DATABASE_URL="$DATABASE_URL" \
  uv run uvicorn ecosfera_ai.main:app --app-dir src
```
## Camada emergente e fila de jobs
| Variável | Valores | Efeito |
| --- | --- | --- |
| `ECOSFERA_BIOLOGY_ENABLED` | `true` (default) / `false` | liga/desliga evolução e ecologia |
| `ECOSFERA_JOB_BACKEND` | `inline` (default) / `arq` | onde o job pesado de evolução roda |

Com `inline`, o `advance-era` resolve a biologia na hora e responde **200** com o
resumo. Com `arq`, ele enfileira o job e responde **202** com a referência,
consultável em `GET /simulation/jobs/{job_id}` (ADR 0007).

```bash
# Produção/staging: Redis + worker ARQ em outro processo
docker compose up -d postgres redis
uv sync --extra sim --extra infra
uv run arq ecosfera_ai.infrastructure.jobs.worker.WorkerSettings   # o worker

ECOSFERA_JOB_BACKEND=arq ECOSFERA_PERSISTENCE_BACKEND=postgres \
  uv run uvicorn ecosfera_ai.main:app --app-dir src
```

As migrations do serviço vivem numa **única árvore** (`migrations/`) cobrindo os
schemas `rag` (Inc 6) e `simulation`. Os testes de integração da persistência real
usam Testcontainers e são **pulados automaticamente** quando não há Docker.

## Estrutura (hexagonal — ADR 0001 — + moldura de Engines — ADR 0008)
```
domain/            regra pura (motor de regras causais, modelos de telemetria)
shared_kernel/     moldura comum a todo Engine (world-state, eventos, replay, sink)
engines/           camada de Simulação: os OITO Engines + planet/ (orquestrador),
                   composition.py (registro), bridge.py (tradução), noop/
simulation_engine/ estado, linha do tempo e replay (os subsistemas saíram no M2)
  biology/         camada EMERGENTE: genoma, aptidão, evolução (AG), ecologia (ABM), códex
application/       casos de uso + portas (Protocols)
infrastructure/    adaptadores de saída (persistência, mensageria, filas inline/ARQ, LLM)
interfaces/        adaptadores de entrada (HTTP v1) + composition root
configs/           regras causais, parâmetros e tradução evento->observação (dados)
                   cada Engine tem AINDA o seu params.yaml co-locado (Spec §5.1)
migrations/        Alembic — uma árvore para os schemas `rag` e `simulation`
```
Desde o M2 **toda a física vive em `engines/`**. O que restou em
`simulation_engine/` é o que não é ciência de domínio: o `PlanetState` que a borda
persiste, a linha do tempo, o replay e a camada emergente do Inc 3 — que é
subsistema de simulação, não Engine (ADR 0014). O `platform/` da Spec §1 nasceu no
M5 como `infrastructure/persistence`; os `consumers/` nasceram no M6.0 como
`domain/consumers` + `application/consumers` — mesma fronteira, dentro da
estratificação hexagonal deste serviço (ADR 0025).

Pastas `rag/ embeddings/ agents/ evaluation/ models/ pipelines/` estão vazias por
design — cada uma é ativada em seu incremento (ver ROADMAP e ADR 0002).

## Decisões arquiteturais
Duas séries, separadas por escopo (ADR-ARCH-0001, sem fusão):

| Série | Onde | Cobre |
| --- | --- | --- |
| projeto | `docs/architecture/adr/ADR-ARCH-*.md` | decisões transversais entre Engines/serviços |
| serviço | `docs/adr/000N-*.md` | decisões internas a este serviço (0001…0015) |

Os do M2:

| ADR | Decisão |
| --- | --- |
| 0012 | ciclos fechados: fronteiras do carbono e da água |
| 0013 | `physics` → Astronomy Engine, e a fronteira do Biota provisório |
| 0014 | aposentadoria do legado, e a perda deliberada do rollback |
| 0015 | dívida de rehidratação do world-state, **vigiada** até o M5 |

### Três guardas que valem conhecer antes de mexer

| Arquivo | O que impede |
| --- | --- |
| `test_snapshot_roundtrip.py` | Engine novo cuja fatia não seja mapeada na ponte — o campo voltaria a zero a cada tick, **em silêncio** (ADR 0015) |
| `test_baseline_is_physics.py` | condição inicial que deixe de ser física: carbono aparecendo sem fonte, planeta derivando sem causa, ou o gap inicial→equilíbrio crescendo |
| `test_solar_flux_has_writer.py` | fatia órfã de escritor — o Climate recairia numa constante de referência e o planeta perderia estações sem quebrar teste algum (ADR 0013) |

Os três protegem a mesma classe de defeito: **o sintoma é ausência**, e ausência
não se denuncia sozinha. Nada estoura, e um número fica parado, plausível, errado.

A especificação da moldura vive em
`docs/architecture/ECOSFERA_Engine_Framework_Spec.md`.
