# Engines de simulação — a camada onde a ciência mora

> Espinha factual extraída do commit `7d80534` por `scripts/generate_reference.py`; prosa curada.
> Índice: [`README.md`](README.md) · Parâmetros: [`00-mesa-de-calibracao.md`](00-mesa-de-calibracao.md)

Esta página segue a **ordem de tick real** (`ENGINE_ORDER` em `engines/composition.py`), não a
ordem alfabética: o guia espelha o fluxo de dados.

## A ordem do tick, e a razão física de cada posição

| # | Engine | Escreve | Lê no MESMO tick | Lê DEFASADO (`lagged_reads`) | Por que aqui |
|---|---|---|---|---|---|
| 1 | `astronomy` | `ASTRONOMY` | — | — | A irradiância é a ENTRADA DE ENERGIA de tudo abaixo; não depende de ninguém |
| 2 | `geology` | `GEOLOGY` | — | `HYDROLOGY`, `EVENT` | Desgaseifica o CO₂ e expõe relevo ao intemperismo |
| 3 | `chemistry` | `CHEMISTRY` | `GEOLOGY` | `ATMOSPHERE`, `HYDROLOGY` | Consome o relevo recém-exposto e publica a troca ar↔oceano |
| 4 | `atmosphere` | `ATMOSPHERE` | `GEOLOGY`, `CHEMISTRY` | `BIOTA` | Integra o estoque de carbono já debitado da troca com o oceano |
| 5 | `climate` | `CLIMATE` | `ATMOSPHERE`, `ASTRONOMY` | `HYDROLOGY`, `EVENT` | Converte forçamento e insolação em temperatura |
| 6 | `hydrology` | `HYDROLOGY` | `CLIMATE` | `EVENT` | Move a água segundo o calor recém-resolvido |
| 7 | `resource` | `RESOURCE` | `ASTRONOMY`, `CLIMATE`, `HYDROLOGY`, `CHEMISTRY` | `BIOTA` | Traduz o ambiente fechado em capacidade de suporte |
| 8 | `evolution` | `BIOTA` | `RESOURCE`, `CLIMATE` | `ECOLOGY`, `EVENT` | A comunidade se sustenta (ou não) e gasta o orçamento |
| 9 | `ecology` | `ECOLOGY` | `BIOTA`, `RESOURCE` | `EVENT` | Reparte a biomassa entre níveis tróficos e resolve a predação |
| 10 | `event` | `EVENT` | `CLIMATE`, `RESOURCE`, `BIOTA` | — | O Diretor observa o mundo JÁ RESOLVIDO e decide se um evento cabe |

> **Os dois laços fechados por defasagem deliberada.**
> `chemistry ↔ atmosphere` (o fluxo ar↔oceano deste tick usa o CO₂ do tick anterior) e
> `climate ↔ hydrology` (o clima lê o gelo com um tick de atraso). Sem a defasagem haveria
> ciclo no grafo; com ela, o acoplamento sobrevive e `validate_graph` aceita. A `EventSlice` é
> lida defasada por todos os afetados porque o Event fecha o tick.

## Anatomia comum de um Engine

Todo Engine de domínio tem os mesmos cinco arquivos, e a repartição é sempre a mesma:

| Arquivo | Contém | Nunca contém |
|---|---|---|
| `contracts.py` | `ENGINE_ID`, `READS`, `LAGGED_READS`, `WRITES`, a dataclass de parâmetros e `load_params()` | fórmula |
| `params.yaml` | a ciência como **dado versionado** (Spec §5.1) | código |
| `domain.py` | física pura: funções sem I/O, sem RNG próprio, sem evento | acesso ao snapshot |
| `service.py` | a porta `Engine`: lê o snapshot, chama o `domain`, monta delta + eventos | fórmula nova |
| `events.py` | vocabulário do Canal B: `event_type` (str) e `CauseCode` (enum) | prosa pedagógica |
| `observability.py` | um sink que projeta os EVENTOS em contadores Prometheus | chamada de dentro de `tick()` |

Os `observability.py` seguem todos o mesmo molde (`record_metrics` no-op, `emit` incrementa
`engine_domain_events` quando o `event_type` bate, `log` no-op) e por isso são documentados
uma vez só, [ao fim desta página](#os-sinks-de-observabilidade-por-engine).

## Nesta página

- [Planet Engine — o orquestrador](#planet-engine--o-orquestrador)
- [`composition.py` — a montagem do planeta](#compositionpy--a-montagem-do-planeta)
- [`bridge.py` — `PlanetState` ↔ world-state](#bridgepy--planetstate--world-state)
- [1. Astronomy](#1-astronomy-engine) · [2. Geology](#2-geology-engine) · [3. Chemistry](#3-chemistry-engine)
  · [4. Atmosphere](#4-atmosphere-engine) · [5. Climate](#5-climate-engine) · [6. Hydrology](#6-hydrology-engine)
  · [7. Resource](#7-resource-engine) · [8. Evolution](#8-evolution-engine) · [9. Ecology](#9-ecology-engine)
  · [10. Event](#10-event-engine)
- [`noop` — o Engine que prova a moldura](#noop--o-engine-que-prova-a-moldura)
- [Os sinks de observabilidade por Engine](#os-sinks-de-observabilidade-por-engine)

---
## Planet Engine — o orquestrador (`planet/service.py`)

### Visão geral

**Arquivo:** `src/ecosfera_ai/engines/planet/service.py` · 282 linhas

**Docstring de topo (extraída):** Planet Engine — o orquestrador do tick (Spec §5.3, ADR-ARCH-0001 Emenda 3).


**Propósito.** O antigo `TickOrchestrator` promovido: mesma responsabilidade, contrato novo.
**Não contém regra científica alguma** — se um dia contiver, é sinal de que uma regra ficou
sem Engine dono.

**As cinco fases de um tick:**

1. publica o snapshot read-only ao Engine da vez;
2. o Engine calcula delta (Canal A) e eventos (Canal B) lendo só o que declarou;
3. o Planet compõe o delta aplicando as invariantes e **republica** o snapshot ao seguinte;
4. fecha o tick avançando o contador;
5. **só então** aciona o `ObservabilitySink`.

A fase 5 vir por último não é estilo: é a invariante do ADR-ARCH-0002. Enquanto o cálculo
acontece, nada é medido nem registrado de forma que possa voltar para dentro dele.



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `EngineContractError` | classe | Exception | Um Engine devolveu delta fora do que declarou — erro de programação, não de dado. |
| `PlanetTickOutcome` | dataclass | — | Snapshot fechado + eventos + amostras de custo + violações. |
| `EraOutcome` | dataclass | — | Checkpoint que FECHA a era `era` e carrega esse número no cabeçalho; promover à era seguinte é decisão da borda assíncrona. |
| `PlanetEngine` | classe | — | Orquestra os Engines registrados em ordem determinística. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__init__` | `def __init__(self, registry: EngineRegistry, *, invariants: Sequence[Invariant] = (), budget: TickBudget \| None = None, sink: ObservabilitySink \| None = None, clock: Callable[[], float] = time.perf_counter) -> None` | — | Relógio INJETÁVEL: o tempo é medida lateral e precisa ser substituível em teste sem tocar no cálculo. |
| `registry` | `def registry(self) -> EngineRegistry` | — | Trivial. |
| `engine_ids` | `def engine_ids(self) -> tuple[str, ...]` | — | Trivial: a ordem de execução, testável. |
| `tick` | `def tick(self, snapshot: WorldStateSnapshot, *, publish: bool = True) -> PlanetTickOutcome` | Executa um tick e devolve o snapshot fechado. | `publish=False` roda o mesmo cálculo sem tocar a observabilidade — o modo do replay. |
| `run_era` | `def run_era(self, snapshot: WorldStateSnapshot, ticks: int, *, publish: bool = True) -> EraOutcome` | Roda uma era inteira e devolve o checkpoint append-only + eventos. | Roda `ticks` passos; o checkpoint é PRODUZIDO aqui e GRAVADO na borda (o loop não faz I/O). |
| `open_next_era` | `def open_next_era(checkpoint: WorldStateSnapshot) -> WorldStateSnapshot` | Promove um checkpoint fechado ao início da era seguinte. | Promove um checkpoint fechado ao início da era seguinte. |
| `stepper` | `def stepper(self) -> Callable[[WorldStateSnapshot], StepOutcome]` | Função pura de avanço, no formato que `shared_kernel.replay` consome. | Adapta `tick` ao formato que `shared_kernel.replay` consome — já com `publish=False`. |
| `_assert_contract` | `def _assert_contract(self, engine: Engine, result: TickResult, snapshot: WorldStateSnapshot) -> None` | Confere que o Engine escreveu exatamente a fatia que declarou. | Confere fatia escrita, autoria do delta e tick. Falha alta, não silenciosa. |
| `_diagnose` | `def _diagnose(self, snapshot: WorldStateSnapshot, samples: Sequence[PerfSample], breaches: Sequence[InvariantBreach]) -> tuple[DomainEvent, ...]` | Traduz orçamento estourado e invariante recortada em eventos §4. | Traduz orçamento estourado e invariante recortada em eventos §4. Construído DEPOIS de `closed`. |
| `_publish` | `def _publish(self, events: Sequence[DomainEvent], samples: Sequence[PerfSample]) -> None` | Único ponto de contato com a observabilidade — sempre pós-cálculo. | Único ponto de contato com a observabilidade — sempre pós-cálculo. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `PLANET_ENGINE_ID` | — | `'planet'` | — |

### `planet/registry.py` — registro ordenado, sem descoberta mágica

**Arquivo:** `src/ecosfera_ai/engines/planet/registry.py` · 56 linhas

**Docstring de topo (extraída):** Registro ordenado de Engines — sem descoberta mágica (Spec §5.3).


A ordem de execução é **dado explícito**, não efeito colateral de import ou de varredura de
diretório. Um Engine só participa do tick se alguém o registrou, e o grafo é validado no boot.



| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__post_init__` | `def __post_init__(self) -> None` | — | Chama `validate_graph` — a validação acontece na CONSTRUÇÃO, isto é, no boot. |
| `of` | `def of(cls, engines: Sequence[Engine]) -> EngineRegistry` | Constrói o registro na ordem recebida (a ordem É a decisão). | Constrói na ordem recebida (a ordem É a decisão). |
| `engine_ids` | `def engine_ids(self) -> tuple[str, ...]` | Identificadores na ordem de execução — torna a ordem testável. | Trivial. |
| `owned_slices` | `def owned_slices(self) -> dict[SliceRef, str]` | Mapa fatia -> Engine dono, útil para diagnóstico e documentação. | Mapa fatia → Engine dono; útil para diagnóstico e para esta documentação. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `CANONICAL_ORDER` | `tuple[str, ...]` | `('physics', 'chemistry', 'atmosphere', 'climate', 'geology', 'hydrology', 'resource', 'evolution', 'ecology', 'event')` | **Referência histórica da Spec §5.3, não a ordem em vigor.** Quem manda é `ENGINE_ORDER` em `composition.py` — ver *Achados* nº 9. |

**Cuidados.**
- O Planet Engine **não conhece Engine algum**: um contrato de `import-linter` faz disso erro
  de build (`O Planet Engine nao conhece Engine algum`).
- Estourar o orçamento emite `DiagnosticEvent` e **não altera um bit** do resultado. Pular um
  Engine lento faria a trajetória depender da carga da máquina.
- A proveniência entra e sai pelo snapshot, o que mantém `tick()` puro: o Planet não guarda
  estado entre ticks.

---

## `composition.py` — a montagem do planeta

### Visão geral

**Arquivo:** `src/ecosfera_ai/engines/composition.py` · 261 linhas

**Docstring de topo (extraída):** Montagem do planeta: registra os oito Engines e costura com os casos de uso.


**Propósito.** Registra os dez Engines na ordem canônica e costura a moldura com os casos de
uso. Mora aqui, e não em `engines/planet/`, de propósito: o Planet Engine não conhece Engine
algum. Este módulo é o oposto — ele conhece todos, e é o **único** dentro de `engines/` que
conhece.



| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `_engines_in_order` | `def _engines_in_order() -> list[Engine]` | Instancia os Engines na ordem canônica, conferindo os identificadores. | Confere no boot que o `engine_id` de cada Engine casa com a chave da ordem: um rename silencioso desmontaria a correspondência entre nome e posição. |
| `planet_invariants` | `def planet_invariants(bounds: StateBounds, *, water_tolerance: float) -> tuple[Invariant, ...]` | Invariantes por fatia (Spec §3), com as faixas físicas versionadas. | Monta as invariantes por fatia com as faixas físicas versionadas. A tolerância da água vem do `params.yaml` da Hydrology, não de um bloco global. |
| `build_planet_engine` | `def build_planet_engine(params: SimulationParams, *, budget: TickBudget \| None = None, sink: ObservabilitySink \| None = None) -> PlanetEngine` | Registra os Engines na ordem canônica de acoplamento (`ENGINE_ORDER`). | Ponto de montagem do caminho de produção. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__init__` | `def __init__(self, planet: PlanetEngine, bounds: StateBounds, *, publish: bool = True) -> None` | — | — |
| `for_replay` | `def for_replay(self) -> FrameworkTickOrchestrator` | Variante que NÃO publica no Canal B — usada pela reconstrução de eras. | Variante que NÃO publica no Canal B. Sem ela, cada `GET /eras/{era}` reemitiria a trilha inteira daquela era. |
| `bounds` | `def bounds(self) -> StateBounds` | — | Trivial. |
| `subsystem_names` | `def subsystem_names(self) -> tuple[str, ...]` | Ordem de execução real — Engines, não mais subsistemas. | Ordem de execução real — Engines, não mais subsistemas. |
| `planet` | `def planet(self) -> PlanetEngine` | Acesso ao orquestrador da moldura (usado por replay e diagnóstico). | Trivial. |
| `tick` | `def tick(self, state: PlanetState) -> TickResult` | — | Faz o ciclo `PlanetState → snapshot → Engines → PlanetState` e filtra o diagnóstico técnico: só a visão CIENTÍFICA chega ao consumidor. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ORDER` | `tuple[str, ...]` | `('astronomy', 'geology', 'chemistry', 'atmosphere', 'climate', 'hydrology', 'resource', 'evolution', 'ecology', 'event')` | **A única fonte da ordem.** `build_planet_engine` instancia a partir dela; trocar de posição aqui muda o tick de verdade. |
| `_ENGINE_FACTORIES` | `Mapping[str, Callable[[], Engine]]` | `{'astronomy': AstronomyEngine, 'geology': GeologyEngine, 'chemistry': ChemistryEngine, 'atmosphere': AtmosphereEngine, 'climate': ClimateEngine, 'hydrology': HydrologyEngine, 'resource': ResourceEngine, 'evolution': EvolutionEngine, 'ecology': EcologyEngine, 'event': EventEngine}` | — |

### As invariantes efetivamente instaladas em produção

| Invariante | Fatias/campos | Comportamento |
|---|---|---|
| `NonNegativeStocks` | astronomy(`solar_flux`), atmosphere(`co2`,`pressure`), geology(`volcanism`,`co2_flux`), climate(`energy`), hydrology(4 reservatórios + `salinity`), chemistry(6 estoques), resource(4), biota(2), ecology(4) | recorta em 0 e registra |
| `BoundedFraction` | hydrology(`ice_fraction`), geology(`relief`), hydrology(`ocean_circulation`) | recorta na faixa de `bounds` e registra |
| `ConservedTotal` | hydrology(`ocean`+`ice`+`vapour`+`freshwater`) | **não repara** — só registra a deriva |

**Por que não há invariante de carbono aqui.** O carbono NÃO é conservado tick a tick: tem
fonte (desgaseificação) e sumidouro (absorção biótica) legítimos. O que precisa valer é a
identidade contábil da troca ar↔oceano — e ela atravessa DUAS fatias com donos diferentes.
Uma invariante que roda por delta, sobre uma fatia, não a enxerga; fazer o Planet Engine
distinguir fonte de troca seria pôr ciência no orquestrador. A verificação vive em
`test_carbon_is_not_double_counted` (ADR 0012).

**Ganchos de calibração.** `ENGINE_ORDER` (Mesa → *Constantes de módulo*); as faixas de
`bounds` (Mesa → *Núcleo*); a tolerância da água (Mesa → *Hidrologia*).

---

## `bridge.py` — `PlanetState` ↔ world-state

### Visão geral

**Arquivo:** `src/ecosfera_ai/engines/bridge.py` · 244 linhas

**Docstring de topo (extraída):** Tradução entre o `PlanetState` persistido e o world-state da moldura.


**Propósito.** Traduz entre o `PlanetState` persistido e o `WorldStateSnapshot` da moldura.
Desde o M2 a tradução é uma **bijeção nas fatias novas**: o que entra volta idêntico.

**Por que o `PlanetState` cresceu.** `FrameworkTickOrchestrator.tick()` faz o ciclo
`snapshot → tick → PlanetState` a CADA tick, porque é o `PlanetState` que a borda HTTP e a
persistência guardam. Um campo sem lugar nele **volta a zero uma vez por tick** — o que
apagaria metade da ciência do M2 antes que ela realimentasse qualquer coisa (ADR 0012/0015).



| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `_hydrology_of` | `def _hydrology_of(state: PlanetState) -> HydrologySlice` | Reparte a água nos quatro reservatórios, hidratando estados agregados. | Reidrata os quatro reservatórios a partir dos agregados UMA ÚNICA VEZ, por `gelo = água·cobertura/(1−cobertura)`. A partir daí o detalhe viaja no próprio `PlanetState`. |
| `_ice_fraction` | `def _ice_fraction(ice: float, total: float) -> float` | — | Trivial. |
| `snapshot_of` | `def snapshot_of(state: PlanetState, *, era: int = 0) -> WorldStateSnapshot` | Reparte um `PlanetState` pelas fatias dos seus Engines donos. | `co2_flux`, `greenhouse_forcing` e `pressure` nascem em ZERO: são taxas e derivadas, recalculadas idênticas no primeiro tick (ADR 0011 §4b). |
| `planet_state_of` | `def planet_state_of(snapshot: WorldStateSnapshot) -> PlanetState` | Junta as fatias no `PlanetState` que a borda HTTP e a persistência esperam. | Publica os AGREGADOS `water` (oceano+doce) e `ice_cover` (fração congelada) — o contrato HTTP não mudou; quem ganhou detalhe foi o modelo. |

**Cuidados.**
- É aqui que se vê a **dívida de rehidratação** (ADR 0015) com nitidez: o world-state ainda não
  é o objeto persistido. Substituir o `PlanetState` pelo `WorldStateSnapshot` continua sendo
  trabalho futuro; o que o M2 fez foi impedir que a truncagem comesse a ciência nova.
- Um campo de fatia novo **precisa** de campo correspondente no `PlanetState` e de mapeamento
  nos dois sentidos aqui, senão ele zera a cada tick sem erro algum.
- Os campos da `EventSlice` são prefixados com `event_` no `PlanetState` para não colidirem.

---

## 1. Astronomy Engine

**Escreve** `ASTRONOMY` · **Lê** nada · **Defasado** nada · **Posição 1 (abre o tick)**

**Propósito.** Órbita e irradiância — o antigo subsystem `physics` (ADR 0013). Abre o tick
porque a insolação é a entrada de energia de tudo abaixo: sem ela o clima recairia numa
constante e o planeta perderia estações.

A órbita é integrada por **velocity Verlet**, um integrador **simplético**: ao contrário de
Euler, conserva a energia orbital ao longo de milhares de passos — a órbita não decai nem
escapa. É 100% determinístico e **não consome o RNG**.

#### `astronomy/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/astronomy/contracts.py` · 52 linhas

**Docstring de topo (extraída):** Fatias e parâmetros do Astronomy Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'astronomy'` | — |
| `WRITES` | — | `SliceRef.ASTRONOMY` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset()` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset()` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`AstronomyEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `gravitational_parameter` | `float` | — | — |
| `timestep` | `float` | — | — |
| `luminosity` | `float` | — | — |
| `orbital_radius` | `float` | — | — |
| `eccentricity_kick` | `float` | — | — |
| `insolation_shift_threshold` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> AstronomyEngineParams` | — | — |

#### `astronomy/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/astronomy/domain.py` · 59 linhas

**Docstring de topo (extraída):** Física pura da órbita: velocity Verlet e irradiância incidente.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `acceleration` | `def acceleration(x: float, y: float, params: AstronomyEngineParams) -> tuple[float, float]` | Aceleração gravitacional newtoniana apontando para a estrela na origem. | Newtoniana, apontando para a estrela na origem; devolve (0,0) no ponto singular. |
| `solar_flux_at` | `def solar_flux_at(x: float, y: float, params: AstronomyEngineParams) -> float` | Irradiância recebida: lei do inverso do quadrado da distância. | Lei do inverso do quadrado — a entrega deste Engine ao resto do motor. |
| `orbital_energy` | `def orbital_energy(x: float, y: float, vx: float, vy: float, params: AstronomyEngineParams) -> float` | Energia orbital específica (cinética + potencial) — invariante do Verlet. | Cinética + potencial: a INVARIANTE que o Verlet conserva e que o teste verifica. |
| `integrate` | `def integrate(x: float, y: float, vx: float, vy: float, params: AstronomyEngineParams) -> tuple[float, float, float, float]` | Um passo de velocity Verlet: meio passo de v, passo de x, meio passo de v. | Meio passo de v, passo de x, meio passo de v. |

#### `astronomy/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/astronomy/service.py` · 88 linhas

**Docstring de topo (extraída):** Astronomy Engine — órbita e irradiância (o antigo subsystem `physics`).




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | Emite `InsolationShift` por variação RELATIVA (a estação de um planeta distante não é menos estação por ser pequena em valor absoluto). O zero de abertura não conta como travessia. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EPS` | — | `1e-09` | Piso da referência na variação relativa — protege a divisão quando `solar_flux` ainda é zero. |


#### `astronomy/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `INSOLATION_SHIFT` | — | `'InsolationShift'` | — |

**`AstronomyCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `ORBITAL_ECCENTRICITY` | — | `'ORBITAL_ECCENTRICITY'` | — |

**Ganchos de calibração.** Todos os seis parâmetros de `astronomy/params.yaml` (Mesa → *Astronomia*).

**Cuidados.** `eccentricity_kick` é lido **só na criação do planeta** (`simulation_engine/params.initial_state`),
não no tick — alterá-lo não afeta planetas já persistidos. A velocidade circular inicial é
derivada de `gravitational_parameter` e `orbital_radius`: mudar um sem o outro cria condição
inicial incoerente com a gravidade que o integrador de fato usa.

---

## 2. Geology Engine

**Escreve** `GEOLOGY` · **Lê** nada · **Defasado** `HYDROLOGY`, `EVENT` · **Posição 2**

**Propósito.** Vulcanismo, relevo e a **fonte de carbono do planeta**. Publica o fluxo de CO₂
desgaseificado na própria fatia; a atmosfera o lê pelo Canal A. Em nenhum momento escreve na
`AtmosphereSlice` — é isso que faz a seta vulcanismo→CO₂ respeitar a regra de ouro da Spec §2.

O vulcanismo é **pulsante**: relaxa para uma linha de base e recebe pulsos tectônicos. O relevo
é um estoque disputado por soerguimento (∝ vulcanismo) e erosão (∝ água × relevo). A
desgaseificação é o braço "fonte" do ciclo carbonato-silicato (Walker, Hays & Kasting, 1981).

#### `geology/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/geology/contracts.py` · 65 linhas

**Docstring de topo (extraída):** Fatias lidas/escritas e parâmetros científicos do Geology Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'geology'` | — |
| `WRITES` | — | `SliceRef.GEOLOGY` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset()` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.HYDROLOGY, SliceRef.EVENT})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`GeologyEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `tectonic_activity` | `float` | — | — |
| `volcanism_baseline` | `float` | — | — |
| `volcanism_decay` | `float` | — | — |
| `uplift_coeff` | `float` | — | — |
| `erosion_coeff` | `float` | — | — |
| `outgassing_base` | `float` | — | — |
| `supervolcanic_multiplier` | `float` | — | — |
| `volcanism_sensitivity` | `float` | — | — |
| `eruption_threshold` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> GeologyEngineParams` | Lê os parâmetros do YAML co-locado ao Engine. | — |

#### `geology/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/geology/domain.py` · 54 linhas

**Docstring de topo (extraída):** Física pura da geologia: vulcanismo, relevo e desgaseificação de carbono.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `volcanism_change` | `def volcanism_change(volcanism: float, pulse: float, params: GeologyEngineParams) -> float` | Variação do vulcanismo: relaxação para a base mais o pulso tectônico. | O pulso entra em **módulo**: não existe vulcanismo negativo. Consequência de calibração — aumentar a variância aumenta a MÉDIA. |
| `relief_change` | `def relief_change(volcanism: float, relief: float, water: float, params: GeologyEngineParams) -> float` | Variação do relevo: soerguimento vulcânico menos erosão hídrica. | Soerguimento menos erosão hídrica. |
| `outgassing_flux` | `def outgassing_flux(volcanism: float, params: GeologyEngineParams) -> float` | Fluxo de CO2 desgaseificado neste tick, em ppm. | Escala linearmente com o vulcanismo sobre um fluxo de base. |
| `is_eruption` | `def is_eruption(volcanism: float, params: GeologyEngineParams) -> bool` | Se o vulcanismo deste tick caracteriza uma erupção notável (Canal B). | Predicado de observabilidade (Canal B), não de física. |

#### `geology/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/geology/service.py` · 105 linhas

**Docstring de topo (extraída):** Geology Engine — vulcanismo, relevo e a FONTE de carbono do planeta.




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | A erosão responde à água LÍQUIDA (oceano + doce): vapor e gelo não erodem rocha nesta escala. O supervulcanismo multiplica o fluxo AQUI, num termo só — a fronteira basal × catastrófico do ADR 0018. |


#### `geology/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `VOLCANIC_ERUPTION` | — | `'VolcanicEruption'` | — |

**`GeologyCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `TECTONIC_PULSE` | — | `'TECTONIC_PULSE'` | — |

**Ganchos de calibração.** Os nove parâmetros de `geology/params.yaml` (Mesa → *Geologia*), com destaque para `outgassing_base` e `supervolcanic_multiplier`.

**Cuidados.** **Este Engine é a única fonte de carbono vulcânico do mundo.** A alternativa — o Event
publicar um pulso de CO₂ que a atmosfera somasse ao lado de `geology.co2_flux` — criaria DUAS
entradas de carbono vulcânico, e a dupla contagem passaria a depender de disciplina em vez de
estrutura. `co2_flux` é um **valor do tick**, não um acumulado: o delta o reposiciona
substituindo o do tick anterior.

---

## 3. Chemistry Engine

**Escreve** `CHEMISTRY` · **Lê** `GEOLOGY` · **Defasado** `ATMOSPHERE`, `HYDROLOGY` · **Posição 3**

**Propósito.** Fecha o ciclo do carbono que o M1 abriu pela metade. A Atmosphere é dona do
estoque **atmosférico**; este Engine é dono do **oceânico** e do sedimento, e publica o
`air_sea_flux` que liga os dois.

**O sinal do fluxo é a decisão que evita dupla contagem:** `air_sea_flux > 0` significa "o
oceano absorve da atmosfera". Este Engine SOMA esse número ao próprio reservatório; a
Atmosphere o SUBTRAI do dela. **Um fluxo, dois livros, sinais opostos** (ADR 0012).

A troca é a **lei de Henry** linearizada; a acidificação é logarítmica porque o pH é, por
definição, o logaritmo negativo da concentração de H⁺ (Sabine et al. 2004).

#### `chemistry/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/chemistry/contracts.py` · 60 linhas

**Docstring de topo (extraída):** Fatias e parâmetros do Chemistry Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'chemistry'` | — |
| `WRITES` | — | `SliceRef.CHEMISTRY` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.GEOLOGY})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.ATMOSPHERE, SliceRef.HYDROLOGY})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`ChemistryEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `solubility` | `float` | — | — |
| `reference_co2` | `float` | — | — |
| `ocean_carbon_capacity` | `float` | — | — |
| `burial_coeff` | `float` | — | — |
| `weathering_nutrient_yield` | `float` | — | — |
| `nutrient_recycling` | `float` | — | — |
| `nitrogen_yield` | `float` | — | — |
| `phosphorus_yield` | `float` | — | — |
| `sulfur_yield` | `float` | — | — |
| `element_burial` | `float` | — | — |
| `reference_ph` | `float` | — | — |
| `ph_sensitivity` | `float` | — | — |
| `reference_ocean_carbon` | `float` | — | — |
| `acidification_threshold` | `float` | — | — |
| `nutrient_depletion_threshold` | `float` | — | — |
| `carbon_tolerance` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> ChemistryEngineParams` | — | — |

#### `chemistry/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/chemistry/domain.py` · 94 linhas

**Docstring de topo (extraída):** Química pura: ciclos do carbono não-atmosférico, de N/P/S e do pH.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `ocean_partial_pressure` | `def ocean_partial_pressure(ocean_carbon: float, params: ChemistryEngineParams) -> float` | Pressão parcial equivalente do carbono dissolvido. | pCO₂ equivalente do carbono dissolvido. |
| `air_sea_flux` | `def air_sea_flux(atmospheric_co2: float, ocean_carbon: float, params: ChemistryEngineParams) -> float` | Troca ar<->oceano. Positivo = o oceano ABSORVE da atmosfera (Henry). | A **saturação** impede que um oceano cheio absorva indefinidamente — sem ela o reservatório viraria sumidouro infinito. |
| `carbon_burial` | `def carbon_burial(ocean_carbon: float, params: ChemistryEngineParams) -> float` | Sequestro para o sedimento — a única SAÍDA do sistema acoplado. | A ÚNICA saída do sistema acoplado ar+oceano. |
| `ocean_ph` | `def ocean_ph(ocean_carbon: float, params: ChemistryEngineParams) -> float` | pH oceânico: cai logaritmicamente com o carbono dissolvido. | pH cai logaritmicamente com o carbono dissolvido. |
| `weathering_release` | `def weathering_release(relief: float, volcanism: float, yield_coeff: float) -> float` | Liberação de elementos pelo intemperismo do relevo exposto. | Liberação de elementos pelo intemperismo do relevo exposto. |
| `nutrient_change` | `def nutrient_change(nutrients: float, relief: float, volcanism: float, params: ChemistryEngineParams) -> float` | Variação do estoque de nutrientes: intemperismo menos reciclagem. | Intemperismo menos reciclagem. |
| `element_change` | `def element_change(stock: float, relief: float, volcanism: float, yield_coeff: float, params: ChemistryEngineParams) -> float` | Variação de N, P ou S: intemperismo menos soterramento. | Intemperismo menos soterramento (N, P ou S). |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EPS` | — | `1e-09` | — |

#### `chemistry/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/chemistry/service.py` · 222 linhas

**Docstring de topo (extraída):** Chemistry Engine — carbono não-atmosférico, N/P/S, nutrientes e pH (M2).




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | O soterrado vira `soil_carbon` — contabilizá-lo é o que torna a conservação de carbono VERIFICÁVEL; sem este livro o teste confundiria sumidouro com vazamento. |
| `_notable` | `def _notable(self, ctx: TickContext, *, ph_before: float, ph_after: float, nutrients_before: float, nutrients_after: float, flux_before: float, flux_after: float, ocean_carbon: float) -> tuple[DomainEvent, ...]` | Só a TRAVESSIA de patamar vira evento — nunca o estado contínuo. | As três regras comparam ANTES e DEPOIS. Testar o valor corrente emitiria `NutrientDepletion` em todo tick de todo planeta, porque uma fatia nasce zerada. O `CarbonFluxShift` só dispara quando o fluxo TROCA DE SENTIDO. |


#### `chemistry/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `NUTRIENT_DEPLETION` | — | `'NutrientDepletion'` | — |
| `OCEAN_ACIDIFICATION` | — | `'OceanAcidification'` | — |
| `CARBON_FLUX_SHIFT` | — | `'CarbonFluxShift'` | — |

**`ChemistryCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `CARBON_DISSOLUTION` | — | `'CARBON_DISSOLUTION'` | — |
| `CARBON_OUTGASSING` | — | `'CARBON_OUTGASSING'` | — |
| `NUTRIENT_EXHAUSTION` | — | `'NUTRIENT_EXHAUSTION'` | — |

**Ganchos de calibração.** Os dezesseis parâmetros de `chemistry/params.yaml` (Mesa → *Química*).

**Cuidados.** **`reference_ocean_carbon` precisa casar com `initial_state.ocean_carbon`** e
**`reference_co2` com `initial_state.co2`**: é isso que faz o oceano partir como TAMPÃO e não
como sumidouro. O defeito medido quando não casavam foi o CO₂ caindo de 280 para 234 ppm em 60
ticks, com leitura pedagógica invertida (ADR 0012 §7). O `carbon_tolerance` declarado aqui
**não é consumido por invariante alguma** — ver *Achados* nº 5.

---

## 4. Atmosphere Engine

**Escreve** `ATMOSPHERE` · **Lê** `GEOLOGY`, `CHEMISTRY` · **Defasado** `BIOTA` · **Posição 4**

**Propósito.** Dono ÚNICO do carbono atmosférico desde o M1 (ADR 0010). Integra o estoque e
publica o forçamento que o clima consome:

    dC/dt = desgaseificação − intemperismo(C) − absorção_biótica(biomassa) − troca_ar↔oceano

**Forçamento radiativo logarítmico** (Myhre et al. 1998): `ΔF = α·ln(C/C₀)`, α = 5,35 W/m².
Por que logarítmica e não linear: as bandas de absorção do CO₂ **saturam** — cada duplicação
acrescenta aproximadamente o MESMO forçamento (~3,7 W/m²), não o dobro. O subsystem legado
usava `coeficiente × CO₂`, que não satura e ensinaria ao aluno uma resposta climática que a
física não tem.

#### `atmosphere/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/atmosphere/contracts.py` · 56 linhas

**Docstring de topo (extraída):** Fatias lidas/escritas e parâmetros do Atmosphere Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'atmosphere'` | — |
| `WRITES` | — | `SliceRef.ATMOSPHERE` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.GEOLOGY, SliceRef.CHEMISTRY})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.BIOTA})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`AtmosphereEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `reference_co2` | `float` | — | — |
| `weathering_coeff` | `float` | — | — |
| `carbon_uptake_coeff` | `float` | — | — |
| `forcing_coefficient` | `float` | — | — |
| `base_pressure` | `float` | — | — |
| `co2_to_pressure` | `float` | — | — |
| `forcing_bands` | `tuple[float, ...]` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> AtmosphereEngineParams` | Lê os parâmetros do YAML co-locado ao Engine. | — |

#### `atmosphere/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/atmosphere/domain.py` · 89 linhas

**Docstring de topo (extraída):** Física pura da atmosfera: ciclo do carbono e forçamento radiativo.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `carbon_sinks` | `def carbon_sinks(co2: float, biomass: float, params: AtmosphereEngineParams) -> float` | Remoção de CO2 no tick: intemperismo (∝ estoque) + absorção biótica. | Intemperismo (∝ estoque) + absorção biótica (∝ biomassa). |
| `co2_change` | `def co2_change(co2: float, inflow: float, biomass: float, air_sea_flux: float, params: AtmosphereEngineParams) -> float` | Variação do estoque: o que entra da geologia menos tudo o que sai. | `air_sea_flux` chega PRONTO da química com a convenção de sinal dela; calcular a troca aqui seria dupla contagem. |
| `radiative_forcing` | `def radiative_forcing(co2: float, params: AtmosphereEngineParams) -> float` | Forçamento radiativo em W/m² relativo ao CO2 de referência (Myhre 1998). | Myhre et al. (1998). |
| `pressure` | `def pressure(co2: float, params: AtmosphereEngineParams) -> float` | Pressão atmosférica: base mais a contribuição parcial do CO2. | Base + contribuição parcial do CO₂ (diagnóstico; nenhum Engine a lê). |
| `forcing_band` | `def forcing_band(forcing: float, params: AtmosphereEngineParams) -> int` | Faixa de forçamento em que o planeta está (0 = abaixo da primeira). | Trabalhar em FAIXAS, não em variação por tick, é o que impede a explosão de eventos. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_CO2_FLOOR` | — | `1e-06` | — |

#### `atmosphere/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/atmosphere/service.py` · 114 linhas

**Docstring de topo (extraída):** Atmosphere Engine — estoque de carbono e forçamento radiativo.




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | A faixa ANTERIOR é derivada do ESTOQUE, não do forçamento gravado na fatia: na borda HTTP o `PlanetState` não tem campo para o forçamento, e comparar contra um zero recém-nascido detectaria travessia em TODO tick. |


#### `atmosphere/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `GREENHOUSE_FORCING_CHANGED` | — | `'GreenhouseForcingChanged'` | — |

**`AtmosphereCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `CO2_ACCUMULATION` | — | `'CO2_ACCUMULATION'` | — |
| `CO2_DRAWDOWN` | — | `'CO2_DRAWDOWN'` | — |

**Ganchos de calibração.** Os sete parâmetros de `atmosphere/params.yaml` (Mesa → *Atmosfera*).

**Cuidados.** `reference_co2` aparece aqui, na Chemistry e em `initial_state.co2` — os três precisam
concordar, senão o planeta nasce com forçamento não-nulo. `_CO2_FLOOR` é piso **numérico**
(`ln(0) = −∞`), não físico, e por isso mora no código e não no YAML. A absorção biótica é a
**única seta vida→física** do modelo: zerar `carbon_uptake_coeff` desfaz a lição de que a vida
muda o planeta.

---

## 5. Climate Engine

**Escreve** `CLIMATE` · **Lê** `ATMOSPHERE`, `ASTRONOMY` · **Defasado** `HYDROLOGY`, `EVENT` · **Posição 5**

**Propósito.** Resolve a temperatura por um balanço de energia de caixa única (Budyko 1969;
Sellers 1969) — o modelo mais simples que ainda é fisicamente coerente:

    absorvida   = irradiância · (1 − albedo(gelo))
    equilíbrio  = offset + k_energia · absorvida + λ · ΔF
    dT/dt       = inércia · (equilíbrio − T) + tempo + oceano

**O clima não calcula efeito estufa.** O forçamento chega pronto da atmosfera pelo Canal A; se
recalculasse, o CO₂ teria dois donos (ADR 0010). O **albedo do gelo** é a retroalimentação
positiva clássica, explícita porque é um dos raciocínios que o aluno precisa reconstruir; o
**sequestro de calor oceânico** é a negativa, herdada do subsystem `ocean` (mudou de dono, não
de física — `temperature` precisa de um escritor único).

#### `climate/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/climate/contracts.py` · 73 linhas

**Docstring de topo (extraída):** Fatias lidas/escritas e parâmetros do Climate Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'climate'` | — |
| `WRITES` | — | `SliceRef.CLIMATE` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.ATMOSPHERE, SliceRef.ASTRONOMY})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.HYDROLOGY, SliceRef.EVENT})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`ClimateEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `insolation` | `float` | — | — |
| `base_albedo` | `float` | — | — |
| `ice_albedo_coeff` | `float` | — | — |
| `energy_to_temp` | `float` | — | — |
| `climate_sensitivity` | `float` | — | — |
| `equilibrium_offset` | `float` | — | — |
| `thermal_inertia` | `float` | — | — |
| `weather_variability` | `float` | — | — |
| `ocean_heat_uptake` | `float` | — | — |
| `ocean_reference_temperature` | `float` | — | — |
| `temperature_bands` | `tuple[float, ...]` | — | — |
| `shift_threshold` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> ClimateEngineParams` | Lê os parâmetros do YAML co-locado ao Engine. | — |

#### `climate/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/climate/domain.py` · 76 linhas

**Docstring de topo (extraída):** Física pura do clima: balanço de energia de caixa única.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `albedo` | `def albedo(ice_cover: float, params: ClimateEngineParams) -> float` | Refletividade planetária: base mais a contribuição da criosfera. | Base + contribuição da criosfera. |
| `incident_flux` | `def incident_flux(solar_flux: float, params: ClimateEngineParams) -> float` | Irradiância no topo da atmosfera, com recuo para a insolação de referência. | Recuo para `params.insolation` quando `solar_flux ≤ 0` — existe para exercitar o clima isolado em teste. |
| `absorbed_energy` | `def absorbed_energy(solar_flux: float, ice_cover: float, params: ClimateEngineParams) -> float` | Energia solar efetivamente absorvida pelo planeta. | Irradiância × (1 − albedo). |
| `equilibrium_temperature` | `def equilibrium_temperature(absorbed: float, forcing: float, params: ClimateEngineParams) -> float` | Temperatura de equilíbrio: energia absorvida mais o forçamento da estufa. | Offset + energia + λ·forçamento. |
| `ocean_heat_flux` | `def ocean_heat_flux(temperature: float, ocean_circulation: float, params: ClimateEngineParams) -> float` | Calor retirado da superfície pela circulação — sempre amortecedor. | Sempre amortecedor: puxa a superfície para `ocean_reference_temperature`. |
| `temperature_band` | `def temperature_band(temperature: float, params: ClimateEngineParams) -> int` | Faixa climática do planeta (0 = abaixo do primeiro limiar). | Faixa climática (0 = abaixo do primeiro limiar). |

#### `climate/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/climate/service.py` · 146 linhas

**Docstring de topo (extraída):** Climate Engine — resolve a temperatura a partir do forçamento radiativo.




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | Soma o resfriamento por evento AQUI (`forcing = estufa − event.cooling_forcing`), e não escrevendo na fatia da Atmosphere: o Event descreve a causa, o Climate decide o efeito (ADR 0018). |
| `_notable` | `def _notable(self, ctx: TickContext, before: float, after: float, change: float, forcing: float) -> tuple[DomainEvent, ...]` | Traduz o tick em ocorrências notáveis — nunca em todo tick. | Dois gatilhos distintos: variação grande em um tick (`TemperatureShift`, para quem investiga transiente) e travessia de patamar (`ClimateThresholdCrossed`, para o aluno). O segundo herda `causation_id` do primeiro quando ambos ocorrem. |


#### `climate/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `TEMPERATURE_SHIFT` | — | `'TemperatureShift'` | — |
| `CLIMATE_THRESHOLD_CROSSED` | — | `'ClimateThresholdCrossed'` | — |

**`ClimateCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `RADIATIVE_FORCING` | — | `'RADIATIVE_FORCING'` | — |
| `ALBEDO_FEEDBACK` | — | `'ALBEDO_FEEDBACK'` | — |

**Ganchos de calibração.** Os doze parâmetros de `climate/params.yaml` (Mesa → *Clima*), com destaque para `climate_sensitivity` e `equilibrium_offset`.

**Cuidados.** A criosfera é **publicada** pela Hydrology (`ice_fraction`) e lida daqui — derivar a mesma
grandeza em dois lugares seria ciência duplicada, e importar o outro Engine é proibido. Existe
uma lacuna CONHECIDA de ~3,6 °C entre `initial_state.temperature` (14,0) e o equilíbrio (~17,6),
pinada em `KNOWN_EQUILIBRIUM_GAP_C`. `params.insolation` é recuo de teste e, em produção, código
morto benigno (*Achados* nº 8).

---

## 6. Hydrology Engine

**Escreve** `HYDROLOGY` · **Lê** `CLIMATE` · **Defasado** `EVENT` · **Posição 6**

**Propósito.** O ciclo da água e a criosfera. Substitui o subsystem `ocean` e absorve o ciclo
gelo↔água que estava embutido no `chemistry` legado (ADR 0012).

    evaporação   : oceano  → vapor      (cresce com a temperatura)
    precipitação : vapor   → água doce
    escoamento   : doce    → oceano
    degelo       : gelo    → oceano     (acima do limiar térmico)
    congelamento : oceano  → gelo       (abaixo do limiar térmico)

**Nenhum fluxo cria nem destrói água** — cada um só move massa entre reservatórios, e é isso
que torna a conservação uma invariante verificável. A dependência real da evaporação com a
temperatura é de Clausius–Clapeyron; na faixa habitável (~0–40 °C) a curva é bem aproximada
por uma reta, e é essa linearização que se usa — explicitamente, para que o modelo não finja
uma precisão que não tem.

#### `hydrology/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/hydrology/contracts.py` · 65 linhas

**Docstring de topo (extraída):** Fatias e parâmetros do Hydrology Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'hydrology'` | — |
| `WRITES` | — | `SliceRef.HYDROLOGY` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.CLIMATE})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.EVENT})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`HydrologyEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `evaporation_coeff` | `float` | — | — |
| `evaporation_reference_temperature` | `float` | — | — |
| `precipitation_coeff` | `float` | — | — |
| `melt_coeff` | `float` | — | — |
| `freeze_coeff` | `float` | — | — |
| `melt_threshold` | `float` | — | — |
| `freeze_threshold` | `float` | — | — |
| `runoff_coeff` | `float` | — | — |
| `salt_content` | `float` | — | — |
| `salinity_relaxation` | `float` | — | — |
| `reference_salinity` | `float` | — | — |
| `reference_temperature` | `float` | — | — |
| `salinity_sensitivity` | `float` | — | — |
| `temperature_sensitivity` | `float` | — | — |
| `tidal_forcing` | `float` | — | — |
| `circulation_baseline` | `float` | — | — |
| `circulation_relaxation` | `float` | — | — |
| `circulation_variability` | `float` | — | — |
| `ice_event_threshold` | `float` | — | — |
| `conservation_tolerance` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> HydrologyEngineParams` | — | — |

#### `hydrology/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/hydrology/domain.py` · 107 linhas

**Docstring de topo (extraída):** Física pura do ciclo da água: quatro reservatórios e os fluxos entre eles.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `water_fluxes` | `def water_fluxes(ocean: float, ice: float, vapour: float, freshwater: float, temperature: float, params: HydrologyEngineParams) -> WaterFluxes` | Calcula os fluxos, cada um limitado pelo reservatório de origem. | Cada fluxo é limitado pelo reservatório de ORIGEM — é o que garante não-negatividade ANTES da invariante. |
| `apply_fluxes` | `def apply_fluxes(ocean: float, ice: float, vapour: float, freshwater: float, fluxes: WaterFluxes) -> tuple[float, float, float, float]` | Move a massa entre reservatórios. A SOMA não muda — só a distribuição. | Move massa entre reservatórios. A SOMA não muda, só a distribuição. |
| `total_water` | `def total_water(ocean: float, ice: float, vapour: float, freshwater: float) -> float` | A grandeza conservada: a soma dos quatro reservatórios. | A grandeza conservada. |
| `target_salinity` | `def target_salinity(ocean: float, params: HydrologyEngineParams) -> float` | Salinidade de equilíbrio: sal conservado diluído na água líquida. | Sal CONSERVADO diluído na água líquida. |
| `target_circulation` | `def target_circulation(salinity: float, temperature: float, params: HydrologyEngineParams) -> float` | Circulação de equilíbrio pelo contraste de densidade mais as marés. | Água fria e salgada afunda e fortalece a circulação; o aquecimento a enfraquece; as marés somam mistura constante. |
| `ice_fraction` | `def ice_fraction(ice: float, ocean: float, vapour: float, freshwater: float) -> float` | Fração da hidrosfera aprisionada em gelo — o que o albedo enxerga. | Fração da hidrosfera aprisionada em gelo — o que o albedo enxerga. |

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `WaterFluxes` | dataclass | — | Os cinco fluxos do tick, cada um movendo massa entre dois reservatórios. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EPS` | — | `1e-09` | — |

#### `hydrology/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/hydrology/service.py` · 156 linhas

**Docstring de topo (extraída):** Hydrology Engine — o ciclo da água e a criosfera (M2).




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | A SECA suprime uma FRAÇÃO da precipitação, aplicada aqui (na fatia de quem detém a água). Suprimir precipitação NÃO destrói água: o que não chove permanece vapor — por isso a conservação continua valendo com seca ativa. |
| `_notable` | `def _notable(self, ctx: TickContext, ice_before: float, ice_after: float, ocean: float, vapour: float, freshwater: float, temperature: float) -> tuple[DomainEvent, ...]` | Só a travessia de patamar vira evento — nunca o contínuo do tick. | Emite DOIS eventos encadeados (`IceSheetChanged` → `WaterBalanceShift`), o segundo com `causation_id` do primeiro. |


#### `hydrology/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ICE_SHEET_CHANGED` | — | `'IceSheetChanged'` | — |
| `WATER_BALANCE_SHIFT` | — | `'WaterBalanceShift'` | — |

**`HydrologyCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `TEMPERATURE_RISE` | — | `'TEMPERATURE_RISE'` | — |
| `TEMPERATURE_FALL` | — | `'TEMPERATURE_FALL'` | — |
| `PRECIPITATION_CHANGE` | — | `'PRECIPITATION_CHANGE'` | — |

**Ganchos de calibração.** Os vinte parâmetros de `hydrology/params.yaml` (Mesa → *Hidrologia*). `conservation_tolerance` é injetado em `ConservedTotal` por `build_planet_engine`.

**Cuidados.** A invariante de conservação **não repara** — só registra a deriva como `DiagnosticEvent`.
Reparar automaticamente esconderia o defeito exatamente onde ele precisa ser visto. O
acoplamento bidirecional água↔clima só não vira ciclo porque o Climate lê o gelo **defasado**.

---

## 7. Resource Engine

**Escreve** `RESOURCE` · **Lê** `ASTRONOMY`, `CLIMATE`, `HYDROLOGY`, `CHEMISTRY` · **Defasado** `BIOTA` · **Posição 7**

**Propósito.** Responde a uma pergunta só: **quanta vida este planeta comporta?** A resposta é
a `carrying_capacity` — o **único acoplamento** entre a camada determinística e a biologia. A
biologia gasta dentro do orçamento e nunca escreve de volta, e é por isso que a física continua
bit-a-bit reproduzível com a biologia ligada ou desligada (ADR 0006).

**Lei do mínimo (Liebig, 1840).** O crescimento não é limitado pela soma dos nutrientes, e sim
pelo **mais escasso** em relação à sua demanda — daí `min(N/dN, P/dP, S/dS)` e não média.

**Habitabilidade multiplicativa.** Os quatro fatores (temperatura, água, nutriente, energia)
**multiplicam-se**: um fator nulo zera a habitabilidade, porque não existe vida sem água por
mais perfeita que seja a temperatura. Uma soma permitiria compensar a ausência de um recurso
com o excesso de outro — justamente o que a lei do mínimo nega.

#### `resource/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/resource/contracts.py` · 60 linhas

**Docstring de topo (extraída):** Fatias e parâmetros do Resource Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'resource'` | — |
| `WRITES` | — | `SliceRef.RESOURCE` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.ASTRONOMY, SliceRef.CLIMATE, SliceRef.HYDROLOGY, SliceRef.CHEMISTRY})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.BIOTA})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`ResourceEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `ocean_accessibility` | `float` | — | — |
| `energy_conversion` | `float` | — | — |
| `nitrogen_demand` | `float` | — | — |
| `phosphorus_demand` | `float` | — | — |
| `sulfur_demand` | `float` | — | — |
| `optimal_temperature` | `float` | — | — |
| `temperature_tolerance` | `float` | — | — |
| `water_requirement` | `float` | — | — |
| `nutrient_requirement` | `float` | — | — |
| `energy_requirement` | `float` | — | — |
| `max_carrying_capacity` | `float` | — | — |
| `consumption_per_biomass` | `float` | — | — |
| `capacity_event_threshold` | `float` | — | — |
| `scarcity_fraction` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> ResourceEngineParams` | — | — |

#### `resource/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/resource/domain.py` · 119 linhas

**Docstring de topo (extraída):** Recurso puro: de estado físico para orçamento biológico.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `water_available` | `def water_available(ocean: float, freshwater: float, params: ResourceEngineParams) -> float` | Água biologicamente utilizável: a doce inteira, a salgada em parte. | A doce inteira; a salgada só em parte (dessalinização biológica tem custo). |
| `limiting_nutrient` | `def limiting_nutrient(nitrogen: float, phosphorus: float, sulfur: float, params: ResourceEngineParams) -> float` | Fração do elemento MAIS ESCASSO frente à sua demanda (lei do mínimo). | Fração do elemento MAIS ESCASSO frente à sua demanda. |
| `nutrients_available` | `def nutrients_available(nutrients: float, nitrogen: float, phosphorus: float, sulfur: float, params: ResourceEngineParams) -> float` | Estoque de nutrientes efetivamente aproveitável, limitado pelo mais escasso. | Estoque aproveitável, limitado pelo mais escasso. |
| `energy_available` | `def energy_available(solar_flux: float, params: ResourceEngineParams) -> float` | Parcela da irradiância incidente que vira energia biologicamente útil. | Parcela da irradiância que vira energia biologicamente útil. |
| `_saturating` | `def _saturating(value: float, requirement: float) -> float` | Aptidão [0,1] de um recurso: cresce até saturar no requisito. | Aptidão [0,1] que cresce até saturar no requisito. |
| `thermal_suitability` | `def thermal_suitability(temperature: float, params: ResourceEngineParams) -> float` | Aptidão térmica: gaussiana em torno do ótimo (idêntica ao `life`). | Gaussiana em torno do ótimo — idêntica ao subsistema `life` (ADR 0013). |
| `habitability` | `def habitability(temperature: float, water: float, nutrients: float, energy: float, params: ResourceEngineParams) -> float` | Índice [0,1] de aptidão do ambiente à vida — produto dos quatro fatores. | Produto dos quatro fatores. |
| `carrying_capacity` | `def carrying_capacity(habitability_index: float, params: ResourceEngineParams) -> float` | Orçamento biológico do planeta, em unidades de biomassa. | O orçamento biológico do planeta. |
| `consumption` | `def consumption(biomass: float, params: ResourceEngineParams) -> float` | Recurso retirado pela biomassa existente neste tick. | Recurso retirado pela biomassa neste tick. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EPS` | — | `1e-09` | — |

#### `resource/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/resource/service.py` · 246 linhas

**Docstring de topo (extraída):** Resource Engine — converte estado físico em orçamento biológico (M2).




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | Lê as quatro fatias físicas do MESMO tick (todas rodam antes) e o consumo da biota DEFASADO. |
| `_notable` | `def _notable(self, ctx: TickContext, *, capacity_before: float, capacity_after: float, before: tuple[float, float, float], after: tuple[float, float, float], index: float) -> tuple[DomainEvent, ...]` | Só a mudança relevante vira evento — nunca o estado contínuo. | A saída de ZERO é caso à parte e sempre emite: é essa travessia que dispara a abiogênese, e sem evento o `LifeEmerged` não teria causa a que apontar (ADR 0016). |
| `_limiting` | `def _limiting(self, availability: tuple[float, float, float]) -> tuple[ResourceCauseCode, str, float] \| None` | O recurso mais escasso frente ao PRÓPRIO requisito, ou nada. | Devolve UM recurso, não três: a lei do mínimo diz que existe um limitante, e nomeá-lo é a informação pedagógica. Três eventos simultâneos diriam ao aluno que há três problemas quando há um. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EPS` | — | `1e-09` | — |


#### `resource/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `CARRYING_CAPACITY_SHIFT` | — | `'CarryingCapacityShift'` | — |
| `RESOURCE_SCARCITY` | — | `'ResourceScarcity'` | — |

**`ResourceCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `HABITABILITY_GAIN` | — | `'HABITABILITY_GAIN'` | — |
| `HABITABILITY_LOSS` | — | `'HABITABILITY_LOSS'` | — |
| `WATER_SHORTAGE` | — | `'WATER_SHORTAGE'` | — |
| `NUTRIENT_SHORTAGE` | — | `'NUTRIENT_SHORTAGE'` | — |
| `ENERGY_SHORTAGE` | — | `'ENERGY_SHORTAGE'` | — |

**Ganchos de calibração.** Os catorze parâmetros de `resource/params.yaml` (Mesa → *Recurso*), com destaque para `max_carrying_capacity` (que move implicitamente o gatilho da abiogênese).

**Cuidados.** A escassez é medida em **fração do requisito**, não em valor absoluto: água, nutriente e
energia vivem em escalas diferentes (0,2 / 0,3 / 0,04), e um único limiar absoluto declararia
um deles permanentemente escasso num planeta normal. `consumed` é publicado mas **não
realimenta a capacidade** — é diagnóstico, não dreno (*Achados* nº 6). Não confundir
`optimal_temperature` (do AMBIENTE, aqui) com `Genome.temp_optimum` (da COORTE, na Evolution).

---

## 8. Evolution Engine

**Escreve** `BIOTA` · **Lê** `RESOURCE`, `CLIMATE` · **Defasado** `ECOLOGY`, `EVENT` · **Posição 8**

**Propósito.** Seleção natural emergente. Substitui o Biota Engine provisório do M2, que
crescia biomassa por curva logística: agora a biomassa é consequência de a comunidade se
sustentar (ou não) nas condições que encontra.

    excedente   = adequação_local − custo_de_manutenção − pressão_de_predação
    Δpopulação  = growth_rate × população × excedente

**Aptidão CONTEXTUAL, não ausência de aptidão (Q5).** Dizer "não há aptidão neste modelo"
seria impreciso. A aptidão EXISTE — o que não existe é aptidão **ABSOLUTA**. O mesmo genoma
que prospera a 20 °C perece a 60 °C sem ter mudado em nada: a aptidão é propriedade da RELAÇÃO
entre organismo e ambiente. Aqui o número **não é comparado entre espécies nem usado para
ordená-las** — cada coorte é avaliada contra o ambiente, não contra as concorrentes.

**Não há algoritmo genético.** A cadeia da decisão, para que ninguém a desfaça por engano:
RF-031 (AG com fitness global) → ADR-ARCH-0001 supera o fitness global (é teleológico: ensina
que a evolução "mira" um ótimo, a concepção equivocada que a plataforma existe para desfazer)
→ o M3 conclui que o DEAP **não tem papel**, porque o que ele oferece é maquinário de
otimização populacional. Sobram ~50 linhas puras. Um contrato de `import-linter` barra `deap` e
`mesa` neste pacote.

**Por que o genoma MÉDIO.** `tick()` precisa ser função pura do snapshot; guardar a lista de
espécies num atributo tornaria o Engine estatal, e a lista não cabe no Canal A (aditivo, de
floats). A formulação de **genética quantitativa** resolve: a comunidade é seu genoma médio, e
a seleção move essa média na direção do ótimo local. A média **rastreia** o ambiente, não
persegue um alvo (ADR 0016).

#### `evolution/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/evolution/contracts.py` · 62 linhas

**Docstring de topo (extraída):** Fatias e parâmetros do Evolution Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'evolution'` | — |
| `WRITES` | — | `SliceRef.BIOTA` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.RESOURCE, SliceRef.CLIMATE})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.ECOLOGY, SliceRef.EVENT})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`EvolutionEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `growth_rate` | `float` | — | — |
| `metabolism_cost` | `float` | — | — |
| `size_cost` | `float` | — | — |
| `energy_reference` | `float` | — | — |
| `crowding_weight` | `float` | — | — |
| `predation_weight` | `float` | — | — |
| `mutation_sigma` | `float` | — | — |
| `reproduction_threshold` | `float` | — | — |
| `speciation_threshold` | `float` | — | — |
| `extinction_population` | `float` | — | — |
| `abiogenesis_capacity` | `float` | — | — |
| `founder_population` | `float` | — | — |
| `max_species` | `int` | — | — |
| `mass_mortality_threshold` | `float` | — | — |
| `trait_shift_threshold` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> EvolutionEngineParams` | — | — |

#### `evolution/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/evolution/domain.py` · 219 linhas

**Docstring de topo (extraída):** Seleção natural EMERGENTE: sobrevivência e reprodução por condição local.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `thermal_match` | `def thermal_match(genome: Genome, temperature: float) -> float` | Quão bem ESTA coorte tolera a temperatura de agora — gaussiana no ótimo. | Gaussiana no ótimo DA COORTE: especialistas (janela estreita) despencam com pequenas variações. É o mecanismo por trás de `THERMAL_INTOLERANCE`. |
| `water_match` | `def water_match(genome: Genome, water_available: float) -> float` | Satura quando há água suficiente para a necessidade DESTA coorte. | Satura quando há água para a necessidade desta coorte. |
| `energy_match` | `def energy_match(genome: Genome, energy_available: float, params: EvolutionEngineParams) -> float` | Só o produtor depende da irradiância; o consumidor come da cadeia trófica. | Só o PRODUTOR depende da irradiância; o consumidor come da cadeia trófica. |
| `crowding` | `def crowding(occupancy: float, params: EvolutionEngineParams) -> float` | Lotação: o orçamento cheio aperta a todos, sem eleger vencedor. | Lotação: o orçamento cheio aperta a todos, sem eleger vencedor. É a densidade-dependência EMERGENTE. |
| `local_suitability` | `def local_suitability(genome: Genome, conditions: LocalConditions, params: EvolutionEngineParams) -> float` | Adequação [0,1] desta coorte ao ambiente que ela encontra. | Produto dos fatores limitantes — a aptidão CONTEXTUAL desta coorte a ESTE ambiente. |
| `maintenance_cost` | `def maintenance_cost(genome: Genome, params: EvolutionEngineParams) -> float` | O que a coorte gasta só para existir: corpo grande e metabolismo alto. | O que a coorte gasta só para existir. |
| `population_change` | `def population_change(genome: Genome, population: float, conditions: LocalConditions, params: EvolutionEngineParams) -> float` | Variação da coorte: o excedente local aplicado à população existente. | O excedente aplicado à população existente. Nada aqui otimiza. |
| `mutate` | `def mutate(genome: Genome, rng: np.random.Generator, params: EvolutionEngineParams) -> Genome` | Copia o genoma com desvio gaussiano por traço, recortando às faixas. | **Não-direcionada**: o desvio não sabe se melhora ou piora. É o ambiente, depois, que decide. |
| `_trait_spans` | `def _trait_spans() -> dict[str, float]` | Amplitude de cada traço — a mutação é relativa à faixa, não absoluta. | Amplitude de cada traço: sem isso um mesmo sigma moveria `metabolism` (0,05–3) e `temp_optimum` (−40–80) em escalas incomparáveis. |
| `has_speciated` | `def has_speciated(descendant: Genome, ancestor: Genome, params: EvolutionEngineParams) -> bool` | Divergiu o bastante da ancestral para ser outra espécie. | Divergência acima do limiar = espécie nova no códex, não ponto melhor no espaço de busca. |
| `is_extinct` | `def is_extinct(population: float, params: EvolutionEngineParams) -> bool` | Abaixo do mínimo viável, a coorte não se sustenta. | Abaixo do mínimo viável a coorte não se sustenta. |

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `LocalConditions` | dataclass | — | O ambiente que UMA coorte encontra neste tick. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EPS` | — | `1e-09` | — |

#### `evolution/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/evolution/service.py` · 421 linhas

**Docstring de topo (extraída):** Evolution Engine — seleção natural emergente sobre a comunidade (M3).




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | Bifurca: `biomass <= 0` → abiogênese; senão → seleção. |
| `_abiogenesis` | `def _abiogenesis(self, ctx: TickContext, conditions: LocalConditions, temperature: float) -> TickResult` | A primeira vida surge quando o ambiente a comporta. | A primeira vida surge quando o ambiente a comporta. O fundador parte do ÓTIMO LOCAL — a vida não surge com genoma arbitrário e depois 'melhora'. |
| `_selection` | `def _selection(self, ctx: TickContext, current: BiotaSlice, conditions: LocalConditions) -> TickResult` | — | A catástrofe remove uma fração SEM olhar o genoma, aplicada AQUI porque a biomassa TOTAL é desta fatia (tirá-la na Ecology faria a soma trófica descolar do total). |
| `_notable` | `def _notable(self, ctx: TickContext, current: BiotaSlice, genome: Genome, drifted: Genome, biomass: float, suitability: float, conditions: LocalConditions) -> tuple[DomainEvent, ...]` | Traduz o tick em ocorrências notáveis — granularidade AGREGADA (§Corr.2). | Granularidade AGREGADA. A cadeia causal aponta para o EVENTO quando a causa é catastrófica e para o CLIMA quando é ecológica — encadear uma morte por meteoro ao `TemperatureShift` faria o Tutor narrar a extinção como intolerância térmica. |

#### Funções auxiliares do serviço

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `_genome_of` | `def _genome_of(biota: BiotaSlice) -> Genome` | Reconstrói o genoma médio a partir da fatia. | Reconstrói o genoma médio a partir da fatia. |
| `_founder` | `def _founder(params: EvolutionEngineParams, temperature: float) -> Genome` | Genoma do primeiro colonizador: adaptado ao mundo que o recebeu. | Genoma do primeiro colonizador, adaptado ao mundo que o recebeu. **Ignora `params`** (`del params`) — os valores são literais. |
| `_toward_local_optimum` | `def _toward_local_optimum(genome: Genome, drifted: Genome, conditions: LocalConditions, params: EvolutionEngineParams) -> Genome` | Fica com a variante que se sustenta MELHOR nas condições de agora. | Fica com a variante que se sustenta melhor NAS CONDIÇÕES DE AGORA. É seleção, não otimização: a comparação é entre a coorte e a variante dela mesma. |
| `_richness_change` | `def _richness_change(current: BiotaSlice, biomass: float, genome: Genome, drifted: Genome, params: EvolutionEngineParams) -> float` | Riqueza sobe por especiação e cai quando a comunidade colapsa. | Riqueza sobe por especiação e cai quando a comunidade colapsa. |
| `_limiting_cause` | `def _limiting_cause(genome: Genome, conditions: LocalConditions, params: EvolutionEngineParams) -> EvolutionCauseCode` | Qual fator local matou a comunidade — o mais escasso, pela lei do mínimo. | **A catástrofe vem PRIMEIRO**, não como mais um candidato: se uma estava ativa quando a população cruzou o piso, foi ela que matou. Ver *Achados* nº 10 sobre os dois últimos ramos. |
| `_factor_of` | `def _factor_of(cause: EvolutionCauseCode) -> str` | Referência ao fator ambiental (refs, não cópias — envelope §4). | Referência ao fator ambiental (refs, não cópias — envelope §4). |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_TRAITS` | — | `('temp_optimum', 'temp_tolerance', 'water_need', 'size', 'metabolism', 'trophic_level')` | — |

#### `LocalConditions` — o único insumo da seleção

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `temperature` | `float` | — | Do Climate, mesmo tick. |
| `water_available` | `float` | — | Do Resource, mesmo tick. |
| `energy_available` | `float` | — | Do Resource, mesmo tick. |
| `carrying_capacity` | `float` | — | O orçamento que o Resource publicou. |
| `occupied` | `float` | — | Biomassa total já instalada — entra como grandeza AMBIENTAL, não como comparação com concorrentes. |
| `predation_pressure` | `float` | — | Da Ecology, leitura DEFASADA. |
| `catastrophe` | `float` | `0.0` | Da EventSlice. **Não entra em `local_suitability`**: uma catástrofe não é fator de adequação, é acidente. Existe aqui só para a ATRIBUIÇÃO DE CAUSA (ADR 0019). |

> **`occupancy` com capacidade zero é `math.inf`, não 1.** Devolver 1,0 tratava um planeta
> inabitável como um planeta apenas cheio — e a diferença não era acadêmica: com
> `crowding(1) ≈ 0,45` contra um custo de manutenção de 0,45, a comunidade **crescia num mundo
> de capacidade zero**. Com infinito, `crowding → 0` e a lei do mínimo faz o resto.


#### `evolution/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `LIFE_EMERGED` | — | `'LifeEmerged'` | — |
| `SPECIATION_OCCURRED` | — | `'SpeciationOccurred'` | — |
| `SPECIES_EXTINCT` | — | `'SpeciesExtinct'` | — |
| `TRAIT_SHIFT` | — | `'TraitShift'` | — |
| `MASS_MORTALITY` | — | `'MassMortality'` | — |

**`EvolutionCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `HABITABILITY_THRESHOLD` | — | `'HABITABILITY_THRESHOLD'` | — |
| `THERMAL_INTOLERANCE` | — | `'THERMAL_INTOLERANCE'` | — |
| `RESOURCE_SCARCITY` | — | `'RESOURCE_SCARCITY'` | — |
| `PREDATION_PRESSURE` | — | `'PREDATION_PRESSURE'` | — |
| `GENETIC_DIVERGENCE` | — | `'GENETIC_DIVERGENCE'` | — |
| `DIRECTIONAL_SELECTION` | — | `'DIRECTIONAL_SELECTION'` | — |
| `CATASTROPHIC_EVENT` | — | `'CATASTROPHIC_EVENT'` | — |

**Ganchos de calibração.** Os quinze parâmetros de `evolution/params.yaml` (Mesa → *Evolução*) **mais** `Genome.BOUNDS` em `simulation_engine/biology/genome.py`, que normaliza tanto a mutação quanto a distância genética.

**Cuidados.** `reproduction_threshold` é **carregado e nunca consumido** (*Achados* nº 1). A biomassa é
**ocupação**; a capacidade é do Resource — este Engine nunca a redefine. `species_richness` é
um ESCALAR: o Engine não tem identidades por espécie, e é isso que trava a decisão P-01 sobre o
que `/species` significa.

---

## 9. Ecology Engine

**Escreve** `ECOLOGY` · **Lê** `BIOTA`, `RESOURCE` · **Defasado** `EVENT` · **Posição 9**

**Propósito.** Reparte a comunidade em três níveis tróficos e resolve a predação, em aritmética
pura sobre agregados.

**Não envolve o modelo por agente e não importa `mesa`.** O ABM opera sobre populações por
espécie; este Engine opera sobre três agregados, que é o que cabe no Canal A. Envolvê-lo
exigiria materializar a lista de espécies a cada tick só para agregá-la de volta. A
consequência prática é que os dez Engines importam e rodam **sem o extra `sim` instalado**
(ADR 0017).

**O que ele escreve, e o que NÃO escreve.** Escreve a `EcologySlice`. **Não escreve a biomassa
total** — essa é da `BiotaSlice`. A ecologia decide a FORMA da pirâmide; o tamanho é da
Evolution (ADR 0016).

#### `ecology/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/ecology/contracts.py` · 64 linhas

**Docstring de topo (extraída):** Fatias e parâmetros do Ecology Engine (Spec §5.1).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'ecology'` | — |
| `WRITES` | — | `SliceRef.ECOLOGY` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.BIOTA, SliceRef.RESOURCE})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.EVENT})` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`EcologyEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `steps_per_tick` | `int` | — | — |
| `growth_rate` | `float` | — | — |
| `predation_rate` | `float` | — | — |
| `conversion_efficiency` | `float` | — | — |
| `mortality_rate` | `float` | — | — |
| `demographic_noise` | `float` | — | — |
| `min_viable_population` | `float` | — | — |
| `herbivore_share` | `float` | — | — |
| `predator_share` | `float` | — | — |
| `max_consumer_share` | `float` | — | — |
| `consumer_capacity_share` | `float` | — | — |
| `collapse_threshold` | `float` | — | — |
| `decline_threshold` | `float` | — | — |
| `max_agents` | `int` | — | — |
| `max_steps` | `int` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> EcologyEngineParams` | — | — |

#### `ecology/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/ecology/service.py` · 328 linhas

**Docstring de topo (extraída):** Ecology Engine — reparte a comunidade em níveis tróficos e resolve a predação.




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | Roda `steps_per_tick` passos e depois RENORMALIZA. A catástrofe **não** é aplicada aqui: chega já embutida no total que a Evolution publicou, e a renormalização a propaga aos três níveis sozinha. |
| `_notable` | `def _notable(self, ctx: TickContext, current: EcologySlice, levels: tuple[float, float, float], pressure: float) -> tuple[DomainEvent, ...]` | Só travessia vira evento, e por NÍVEL — nunca por organismo (Corr.2). | Só travessia vira evento, e por NÍVEL — nunca por organismo. O colapso é medido em PARTICIPAÇÃO no total, não em valor absoluto. |

#### Funções do módulo — a ciência trófica

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `viability_threshold` | `def viability_threshold(params: EcologyEngineParams) -> float` | Biomassa do nível de BAIXO necessária para sustentar o nível de cima. | **Derivada, não arbitrada**: `mortalidade/(conversão×predação)`. Calcular em vez de configurar é o que impede o limiar de ficar incoerente com as taxas quando alguém as recalibrar. |
| `_seeded_levels` | `def _seeded_levels(current: EcologySlice, biomass: float, params: EcologyEngineParams) -> tuple[float, float, float]` | Reparte a biomassa e deixa a SUCESSÃO ecológica ocupar níveis vazios. | Deixa a SUCESSÃO ecológica ocupar níveis vazios. Semear herbívoros antes de haver o que comer os mataria no primeiro passo — e o semeio só acontece uma vez. |
| `_room` | `def _room(occupied: float, ceiling: float) -> float` | Fração do ganho ainda admitida pelo teto ambiental — logística de Verhulst. | Logística de Verhulst `(1 − N/K)` estendida aos consumidores (Q11). Nunca fica negativo: um nível acima do teto para de ganhar, e quem o reduz é a mortalidade — um ganho negativo seria uma segunda via de morte, contabilizada duas vezes. |
| `_trophic_step` | `def _trophic_step(levels: tuple[float, float, float], capacity: float, params: EcologyEngineParams, ctx: TickContext) -> tuple[float, float, float]` | Um passo SÍNCRONO da cadeia, com teto global de predação por nível. | Passo SÍNCRONO com teto global de captura: todos leem a mesma fotografia e a captura é limitada ao estoque de presa. Sem isso, predadores somados comem mais presa do que existe e a diferença vira biomassa do nada. |
| `_renormalised` | `def _renormalised(levels: tuple[float, float, float], biomass: float, params: EcologyEngineParams) -> tuple[float, float, float]` | Ajusta a repartição ao total que a Evolution publicou, SEM inverter a pirâmide. | **A trava de Elton.** Uma renormalização ingênua escala os predadores para cima quando os produtores colapsam, produzindo um planeta de predadores sem presa. Aqui os consumidores somados não passam de `max_consumer_share` do total. |
| `_predation_pressure` | `def _predation_pressure(levels: tuple[float, float, float], params: EcologyEngineParams) -> float` | Pressão que os consumidores exercem — o que a Evolution lê defasado. | O que a Evolution lê defasado. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EPS` | — | `1e-09` | — |


#### `ecology/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `POPULATION_DECLINED` | — | `'PopulationDeclined'` | — |
| `TROPHIC_COLLAPSE` | — | `'TrophicCollapse'` | — |

**`EcologyCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `PREDATION_PRESSURE` | — | `'PREDATION_PRESSURE'` | — |
| `PREY_COLLAPSE` | — | `'PREY_COLLAPSE'` | — |
| `RESOURCE_SCARCITY` | — | `'RESOURCE_SCARCITY'` | — |

**Ganchos de calibração.** Os quinze parâmetros de `ecology/params.yaml` (Mesa → *Ecologia*), com destaque para o trio `predation_rate` / `conversion_efficiency` / `mortality_rate`, que define `viability_threshold`.

**Cuidados.** `max_agents` e `max_steps` são **carregados e não consumidos** (*Achados* nº 2). A cadência é
`steps_per_tick` (1 por tick), não um lote por era: com `era_length: 10` o trabalho por era é
equivalente ao do modelo anterior, mas a ecologia passa a ler um ambiente **atualizado** entre
passos em vez de um instantâneo congelado. Isso mudou a trajetória numérica de propósito — o M3
é o marco que introduz a biota, e não havia baseline anterior a preservar.

---

## 10. Event Engine

**Escreve** `EVENT` · **Lê** `CLIMATE`, `RESOURCE`, `BIOTA` · **Defasado** nada · **Posição 10 (fecha o tick)**

**Propósito.** Os acontecimentos extraordinários e o Diretor. Escreve UMA fatia e **nunca as
fatias que perturba**: quem aplica a perturbação é o Engine dono da grandeza, lendo o escalar
publicado aqui.

**Por que a inversão.** Um meteoro esfria o planeta, uma seca reduz a precipitação — todas
grandezas de fatias que JÁ TÊM DONO. A moldura admite um escritor por fatia, e `validate_graph`
recusaria um segundo. A saída é o Event **descrever a causa, não o efeito**: publica a
perturbação como escalar na fatia dele, e cada Engine afetado a incorpora à própria dinâmica
(ADR 0018). Isso mantém de pé, ao mesmo tempo: um dono por fatia, perturbações no Canal A
(float, aditivo, replayável) e nenhum Engine lendo estado interno de outro.

**Os dois canais.** Canal A (`EventSlice`) carrega a CONSEQUÊNCIA física contínua — poeira que
decai, forçamento negativo, intensidade de seca. Canal B carrega a OCORRÊNCIA discreta
(`MeteorImpact`, `DroughtBegan`). Separá-los é o que permite ao Climate reagir sem saber que
existe um catálogo, e ao Tutor explicar o meteoro sem recalcular física.

**Perturbação é estoque que decai, não pulso.** Modelar o meteoro como pulso instantâneo
produziria um degrau na temperatura e nenhum "inverno de impacto" — justamente o fenômeno a
ensinar (Toon et al. 1997; Robock 2000).

#### `event/contracts.py` — fronteira e parâmetros

**Arquivo:** `src/ecosfera_ai/engines/event/contracts.py` · 82 linhas

**Docstring de topo (extraída):** Fatias, parâmetros e catálogo do Event Engine (Spec §5.1, §8).




| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `ENGINE_ID` | — | `'event'` | — |
| `WRITES` | — | `SliceRef.EVENT` | — |
| `READS` | `frozenset[SliceRef]` | `frozenset({SliceRef.CLIMATE, SliceRef.RESOURCE, SliceRef.BIOTA})` | — |
| `LAGGED_READS` | `frozenset[SliceRef]` | `frozenset()` | — |
| `PARAMS_PATH` | — | `Path(__file__).parent / 'params.yaml'` | — |

**`EventEngineParams`** — a ciência como dado versionado. Os **valores atuais, efeitos e riscos**
de cada campo estão na [Mesa de Calibração](00-mesa-de-calibracao.md); aqui ficam os tipos
exatos, extraídos do código:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | `int` | — | — |
| `scheduling_probability` | `float` | — | — |
| `quiet_ticks_after` | `int` | — | — |
| `max_active_events` | `int` | — | — |
| `catalog` | `dict[EventKind, EventProfile]` | — | — |
| `ice_age_max_temperature` | `float` | — | — |
| `drought_min_temperature` | `float` | — | — |
| `wildfire_min_biomass` | `float` | — | — |
| `max_duration_s` | `float` | — | — |
| `max_events` | `int` | — | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path = PARAMS_PATH) -> EventEngineParams` | — | — |

#### `event/domain.py` — física pura

**Arquivo:** `src/ecosfera_ai/engines/event/domain.py` · 109 linhas

**Docstring de topo (extraída):** Catálogo de eventos extraordinários e seus perfis de perturbação.




| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `decay_at` | `def decay_at(profile: EventProfile, elapsed: int) -> float` | Fração da intensidade de pico ainda ativa após `elapsed` ticks. | Fora da janela a perturbação é EXATAMENTE zero, não um resíduo — um resíduo que nunca zera faria a linha de base derivar sem causa. |
| `perturbation_at` | `def perturbation_at(profile: EventProfile, elapsed: int) -> dict[str, float]` | Perturbação corrente do evento, campo a campo da `EventSlice`. | `impact` e `mortality` são PICOS, não estoques: valem só no tick do evento. Uma mortalidade catastrófica que decaísse por vinte ticks seria pressão ecológica, não catástrofe (ADR 0019). |
| `is_catastrophic` | `def is_catastrophic(profile: EventProfile) -> bool` | O evento mata INDEPENDENTEMENTE de adaptação? | `mortality > 0`. É o predicado que separa as duas taxonomias de extinção. |

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `EventKind` | Enum | IntEnum | Catálogo. É `IntEnum` porque o índice viaja na `EventSlice` (Canal A). |
| `EventProfile` | dataclass | — | Como UM evento perturba o mundo, em dados versionados (`params.yaml`). |

#### `event/service.py` — a porta `Engine`

**Arquivo:** `src/ecosfera_ai/engines/event/service.py` · 294 linhas

**Docstring de topo (extraída):** Event Engine — os acontecimentos extraordinários e o Diretor (M4).




| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | Três fases: `_advance` move o relógio, `_maybe_schedule` consulta o Diretor, `_with_perturbation` preenche os escalares. `entities_processed=1` mesmo em tick calmo — o Diretor decide a cada tick, e contar isso mantém a série comparável. |

#### Funções do serviço

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `_advance` | `def _advance(current: EventSlice, params: EventEngineParams, emitter: EventEmitter, events: list[DomainEvent]) -> EventSlice` | Move o relógio: envelhece o evento ativo, aproxima o anunciado, gasta o silêncio. | Envelhece o ativo, aproxima o anunciado e gasta o silêncio. `DroughtEnded` é o ÚNICO fim que vira evento próprio: uma seca que acaba é notícia; poeira que assentou não é um segundo acontecimento. |
| `_maybe_schedule` | `def _maybe_schedule(state: EventSlice, ctx: TickContext, params: EventEngineParams, emitter: EventEmitter, events: list[DomainEvent]) -> EventSlice` | Consulta o Diretor e, havendo decisão, TELEGRAFA o evento (RF-019/020). | TELEGRAFA o evento (RF-019/020). O anúncio é o ponto do desenho: um evento que chega sem aviso não ensina antecipação — ensina azar. |
| `_with_perturbation` | `def _with_perturbation(state: EventSlice, params: EventEngineParams) -> EventSlice` | Preenche os escalares de perturbação a partir do evento ativo. | Escala a perturbação pela severidade sorteada. |
| `_factors_of` | `def _factors_of(kind: EventKind) -> list[str]` | Fatores ambientais declarados no envelope — dado, não prosa. | Fatores ambientais declarados no envelope — dado, não prosa. |
| `_state_dict` | `def _state_dict(state: EventSlice) -> dict[str, float]` | — | Trivial. |
| `_replace_state` | `def _replace_state(current: EventSlice, *, kind: int, elapsed: int, severity: float, quiet: float, forecast: tuple[int, float, float] = (0, 0.0, 0.0)) -> EventSlice` | Novo estado de bookkeeping, com as perturbações ZERADAS. | Novo bookkeeping com as perturbações **zeradas**; repreenchê-las em `_with_perturbation` é o que garante que uma perturbação nunca sobreviva ao evento que a causou. |
| `_delta_values` | `def _delta_values(before: EventSlice, after: EventSlice) -> dict[str, float]` | O Canal A é ADITIVO: publica-se a diferença, não o valor absoluto. | O Canal A é ADITIVO: publica-se a diferença, não o valor absoluto. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_ONSET` | — | `{EventKind.METEOR: METEOR_IMPACT, EventKind.DROUGHT: DROUGHT_BEGAN, EventKind.WILDFIRE: WILDFIRE_IGNITED, EventKind.ICE_AGE: ICE_AGE_ONSET, EventKind.STORM: STORM_OCCURRED, EventKind.SUPERVOLCANO: SUPERVOLCANIC_ERUPTION}` | — |
| `_PERTURBATION_FIELDS` | — | `('dust_load', 'cooling_forcing', 'drought_intensity', 'supervolcanic_intensity', 'impact_energy', 'catastrophic_mortality')` | — |

> **`consequences` não sai daqui.** Anunciar "extinction" no impacto seria adivinhar um efeito
> que ainda não aconteceu — pode não haver extinção alguma. A relação causa→efeito é PROJETADA
> do Event Store, invertendo os `causation_id` depois do fato (ADR-ARCH-0002).

#### `event/director.py` — a "IA como Mestre" que não aprende

**Arquivo:** `src/ecosfera_ai/engines/event/director.py` · 111 linhas

**Docstring de topo (extraída):** O Diretor: decide QUAIS eventos acontecem e QUANDO — deterministicamente.


O nome engana: **não há aprendizado aqui**. O Diretor é uma função pura de
`(world-state, RNG semeado)`.

**O que a pureza proíbe.** O Diretor **não lê logs, métricas nem o Event Store**. A tentação é
evidente — "agendar uma seca porque o aluno vem prosperando há muitas eras" pede o histórico —
e é exatamente o que a moldura proíbe: se o Diretor lesse a trilha, o replay deixaria de ser
reproduzível a partir de `(seed, checkpoint)`, porque a trilha é EFEITO da execução, não
entrada dela.

**Sem RL, e adiado explicitamente.** Um Diretor treinado seria estatal e dependeria de
histórico. Introduzi-lo exige antes decidir onde o estado do agente vive e como o replay o
reconstrói — não é uma extensão, é outro desenho.



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `Schedule` | dataclass | — | O que o Diretor decidiu neste tick. |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `_is_plausible` | `def _is_plausible(kind: EventKind, snapshot: WorldStateSnapshot, p: EventEngineParams) -> bool` | O evento faz sentido no mundo de AGORA? | **Não é roteiro — é recusa do absurdo.** O Diretor não escolhe o evento 'certo' para a lição; descarta o fisicamente incoerente e sorteia entre o que resta. |
| `plausible_kinds` | `def plausible_kinds(snapshot: WorldStateSnapshot, p: EventEngineParams) -> list[EventKind]` | Catálogo filtrado pelo contexto, em ordem ESTÁVEL. | Ordem ESTÁVEL pelo valor do enum, não pela ordem do dicionário: a iteração precisa ser idêntica entre execuções para o sorteio ser reproduzível. |
| `decide` | `def decide(snapshot: WorldStateSnapshot, rng: np.random.Generator, p: EventEngineParams, *, quiet: bool) -> Schedule` | Agenda (ou não) um evento, a partir do estado e do RNG semeado. | Sorteia por peso entre os plausíveis; a severidade varia em `uniform(0.6, 1.0)` para que dois meteoros não sejam o mesmo meteoro. |

#### `EventKind` — o catálogo como enum

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `NONE` | — | `0` | — |
| `METEOR` | — | `1` | — |
| `DROUGHT` | — | `2` | — |
| `WILDFIRE` | — | `3` | — |
| `ICE_AGE` | — | `4` | — |
| `STORM` | — | `5` | — |
| `SUPERVOLCANO` | — | `6` | — |

> É `IntEnum` porque o índice viaja na `EventSlice`, e o **Canal A é de floats**. O nome viaja
> pelo Canal B, onde há espaço para estrutura.

#### `EventProfile` — como UM evento perturba o mundo

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `kind` | `EventKind` | — | — |
| `duration` | `int` | — | — |
| `decay` | `float` | — | — |
| `dust` | `float` | — | — |
| `cooling` | `float` | — | — |
| `drought` | `float` | — | — |
| `impact` | `float` | — | — |
| `mortality` | `float` | — | — |
| `supervolcanic` | `float` | — | — |
| `forecast_lead` | `int` | — | — |
| `weight` | `float` | — | — |


#### `event/events.py` — vocabulário do Canal B

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `EVENT_FORECAST` | — | `'EventForecast'` | — |
| `METEOR_IMPACT` | — | `'MeteorImpact'` | — |
| `DROUGHT_BEGAN` | — | `'DroughtBegan'` | — |
| `DROUGHT_ENDED` | — | `'DroughtEnded'` | — |
| `WILDFIRE_IGNITED` | — | `'WildfireIgnited'` | — |
| `ICE_AGE_ONSET` | — | `'IceAgeOnset'` | — |
| `STORM_OCCURRED` | — | `'StormOccurred'` | — |
| `SUPERVOLCANIC_ERUPTION` | — | `'SupervolcanicEruption'` | — |

**`EventCauseCode`** — causas estruturadas (enum, nunca prosa):

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `SCHEDULED_BY_DIRECTOR` | — | `'SCHEDULED_BY_DIRECTOR'` | — |
| `FORECAST_ANNOUNCED` | — | `'FORECAST_ANNOUNCED'` | — |
| `EVENT_ONSET` | — | `'EVENT_ONSET'` | — |
| `EVENT_SUBSIDED` | — | `'EVENT_SUBSIDED'` | — |

**Ganchos de calibração.** `event/params.yaml` inteiro — ritmo (`scheduling_probability`, `quiet_ticks_after`), catálogo (`catalog.*`) e contexto (`context.*`). Ver Mesa → *Eventos*, incluindo a tabela do catálogo evento a evento.

**Cuidados.** **O catálogo é DADO versionado, não código:** acrescentar um evento ou mudar uma severidade é
editar o YAML. `max_active_events` é carregado e **não consumido** (*Achados* nº 3) — a
`EventSlice` comporta um evento ativo por construção. `dust_load` e `impact_energy` são
publicados e **nenhum Engine os lê** (*Achados* nº 7): o resfriamento por poeira chega
inteiramente pelo coeficiente `cooling`. Os campos de telegrafia (`forecast_*`) existem na
fatia mas **não são expostos por nenhuma rota HTTP** (*Achados* nº 11).

---

## `noop` — o Engine que prova a moldura

### `noop/service.py`

**Arquivo:** `src/ecosfera_ai/engines/noop/service.py` · 49 linhas

**Docstring de topo (extraída):** Engine trivial que prova a moldura (critério de conclusão do M0 — Spec §8).


**Propósito.** Não modela ciência nenhuma, **de propósito**. Existe para demonstrar que o
Planet Engine registra, ordena, injeta RNG semeado, compõe delta e faz replay — sem que a prova
dependa de nenhuma física estar correta. Se um teste da moldura falha com este Engine, o
defeito é da moldura (critério de conclusão do M0, Spec §8).



| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `engine_id` | `str` | `NOOP_ENGINE_ID` | — |
| `heartbeat_every` | `int` | `1` | — |
| `reads` | `frozenset[SliceRef]` | `frozenset({SliceRef.RESOURCE})` | — |
| `lagged_reads` | `frozenset[SliceRef]` | `frozenset()` | — |
| `writes` | `SliceRef` | `SliceRef.RESOURCE` | — |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `tick` | `def tick(self, ctx: TickContext) -> TickResult` | — | Delta vazio + um `EngineHeartbeat` a cada `heartbeat_every` ticks. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `NOOP_ENGINE_ID` | — | `'noop'` | — |

**Cuidados.** Não faz parte de `ENGINE_ORDER` e nunca roda em produção.

---

## Os sinks de observabilidade por Engine

Cada Engine tem um `observability.py` com um sink de molde idêntico:

| Membro | Assinatura | O que faz |
|---|---|---|
| `record_metrics` | `def record_metrics(self, sample: PerfSample) -> None` | no-op — tempo e entidades já são cobertos pelo sink genérico |
| `emit` | `def emit(self, event: DomainEvent) -> None` | incrementa `engine_domain_events{engine, event_type}` quando o `event_type` é do domínio |
| `log` | `def log(self, message: str, /, **fields: object) -> None` | no-op |

**A regra que o molde protege:** os contadores são alimentados **por um sink, depois do tick**
— nunca de dentro de `tick()`. Se o Engine os incrementasse durante o cálculo, a medição
estaria dentro do caminho determinístico, que é o que o ADR-ARCH-0002 proíbe.

### Vocabulário de eventos por Engine

| Engine | `event_type` emitidos |
|---|---|
| `astronomy` | `InsolationShift` |
| `geology` | `VolcanicEruption` |
| `chemistry` | `NutrientDepletion`, `OceanAcidification`, `CarbonFluxShift` |
| `atmosphere` | `GreenhouseForcingChanged` |
| `climate` | `TemperatureShift`, `ClimateThresholdCrossed` |
| `hydrology` | `IceSheetChanged`, `WaterBalanceShift` |
| `resource` | `CarryingCapacityShift`, `ResourceScarcity` |
| `evolution` | `LifeEmerged`, `SpeciationOccurred`, `SpeciesExtinct`, `TraitShift`, `MassMortality` |
| `ecology` | `PopulationDeclined`, `TrophicCollapse` |
| `event` | `EventForecast`, `MeteorImpact`, `DroughtBegan`, `DroughtEnded`, `WildfireIgnited`, `IceAgeOnset`, `StormOccurred`, `SupervolcanicEruption` |

> Um `event_type` novo só chega ao motor causal se entrar em `configs/event_observations.yaml`.
> Nem todos os tipos acima têm mapeamento hoje — a tabela de tradução está documentada em
> [`40-aplicacao-e-interfaces.md`](40-aplicacao-e-interfaces.md).

---

**Achados desta auditoria:** [`90-achados-da-auditoria.md`](90-achados-da-auditoria.md)
