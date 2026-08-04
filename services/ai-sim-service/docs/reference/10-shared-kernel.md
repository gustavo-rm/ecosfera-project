# Moldura comum — `shared_kernel`

> Espinha factual extraída do commit `7d80534` por `scripts/generate_reference.py`; prosa curada.
> Índice: [`README.md`](README.md) · Parâmetros: [`00-mesa-de-calibracao.md`](00-mesa-de-calibracao.md)

Este pacote é a **camada de que tudo depende** e que não depende de nada: contratos de
world-state e delta (Spec §3), envelope de evento (§4), porta `Engine` e contexto de tick
(§5.2), RNG semeado, observabilidade (§6), replay (§7) e o artefato portável (M5).

Duas regras estruturais, verificadas por `import-linter` no `pyproject.toml`:

- `shared_kernel` **não importa** `ecosfera_ai.engines`, `infrastructure` nem `interfaces`;
- nenhum Engine importa outro Engine.

Se um dia uma regra científica aparecer aqui, é sinal de que ela ficou sem Engine dono.

## Nesta página

- [`world_state.py` — fatias, deltas e invariantes](#world_statepy--fatias-deltas-e-invariantes)
- [`engine.py` — a porta `Engine` e o contrato de tick](#enginepy--a-porta-engine-e-o-contrato-de-tick)
- [`events.py` — o envelope §4](#eventspy--o-envelope-4)
- [`rng.py` — determinismo por semente](#rngpy--determinismo-por-semente)
- [`replay.py` — reconstrução bit-a-bit](#replaypy--reconstrução-bit-a-bit)
- [`observability.py` — os quatro pilares](#observabilitypy--os-quatro-pilares)
- [`portable.py` — artefato exportável](#portablepy--artefato-exportável)
- [`timeseries.py` — trajetória observável](#timeseriespy--trajetória-observável)
- [`__init__.py` — superfície pública](#__init__py--superfície-pública)

---
### `world_state.py` — fatias, deltas e invariantes

**Arquivo:** `src/ecosfera_ai/shared_kernel/world_state.py` · 670 linhas

**Docstring de topo (extraída):** Contrato do World-State: snapshot imutável, fatias por domínio e deltas.


**Propósito.** Define o Canal A inteiro: o snapshot imutável e versionado, as dez fatias
tipadas por domínio, o delta aditivo de um Engine e as invariantes que o Planet Engine
aplica ao compor.

**As três decisões que este arquivo carrega:**

1. **Deltas são aditivos** — carregam a VARIAÇÃO, não o valor final. É o que torna a
   composição associativa e permite a um Engine descrever só a própria contribuição.
2. **Composição é sequencial, não simultânea** — o Planet republica o snapshot a cada delta,
   de modo que o Engine N enxerga o efeito dos Engines 1..N−1. "Read-only" é regra de
   PROPRIEDADE (ninguém escreve fatia alheia), não de atualidade do dado (ADR 0008).
3. **Uma fatia, um dono** — a fatia é a unidade de propriedade de escrita, e `validate_graph`
   recusa no boot um segundo escritor.



#### Fatias do world-state (uma por domínio, um Engine dono cada)

| Fatia | `SliceRef` | Engine dono | Campos |
|---|---|---|---|
| `AstronomySlice` | `ASTRONOMY` | `astronomy` | `orbital_x`, `orbital_y`, `orbital_vx`, `orbital_vy`, `solar_flux` |
| `GeologySlice` | `GEOLOGY` | `geology` | `relief`, `volcanism`, `co2_flux` |
| `AtmosphereSlice` | `ATMOSPHERE` | `atmosphere` | `co2`, `pressure`, `greenhouse_forcing` |
| `ClimateSlice` | `CLIMATE` | `climate` | `temperature`, `energy` |
| `HydrologySlice` | `HYDROLOGY` | `hydrology` | `ocean`, `ice`, `vapour`, `freshwater`, `salinity`, `ocean_circulation`, `ice_fraction`, `evaporation`, `precipitation` |
| `ChemistrySlice` | `CHEMISTRY` | `chemistry` | `ocean_carbon`, `soil_carbon`, `nitrogen`, `phosphorus`, `sulfur`, `nutrients`, `ph`, `air_sea_flux` |
| `ResourceSlice` | `RESOURCE` | `resource` | `water_available`, `nutrients_available`, `energy_available`, `carrying_capacity`, `consumed` |
| `BiotaSlice` | `BIOTA` | `evolution` | `biomass`, `species_richness` + 6 traços médios (`mean_*`) |
| `EcologySlice` | `ECOLOGY` | `ecology` | `producer_biomass`, `herbivore_biomass`, `predator_biomass`, `predation_pressure`, `total_population` |
| `EventSlice` | `EVENT` | `event` | 6 perturbações + 3 campos de telegrafia + 4 de bookkeeping |

#### `EventSlice` — campos (a fatia com mais sutileza)

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `dust_load` | `float` | `0.0` | — |
| `cooling_forcing` | `float` | `0.0` | — |
| `drought_intensity` | `float` | `0.0` | — |
| `impact_energy` | `float` | `0.0` | — |
| `catastrophic_mortality` | `float` | `0.0` | — |
| `supervolcanic_intensity` | `float` | `0.0` | — |
| `forecast_kind` | `float` | `0.0` | — |
| `forecast_ticks_ahead` | `float` | `0.0` | — |
| `forecast_severity` | `float` | `0.0` | — |
| `active_kind` | `float` | `0.0` | — |
| `active_elapsed` | `float` | `0.0` | — |
| `active_severity` | `float` | `0.0` | — |
| `quiet_remaining` | `float` | `0.0` | — |

> **Por que o bookkeeping (`active_*`, `quiet_remaining`) mora na FATIA e não no Engine:**
> `tick()` precisa ser função pura do snapshot — é disso que o replay bit-a-bit depende. Um
> Engine que guardasse "qual evento está ativo e há quantos ticks" num atributo próprio
> deixaria de depender só do que recebe. É o mesmo motivo pelo qual a Evolution carrega o
> genoma médio na fatia em vez da lista de espécies (ADR 0016).

#### `BiotaSlice` — campos

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `biomass` | `float` | `0.0` | Biomassa total da comunidade — **ocupação**, não teto. |
| `species_richness` | `float` | `0.0` | Contagem escalar. Não há identidades por espécie no Engine (P-01). |
| `mean_temp_optimum` | `float` | `0.0` | Genoma MÉDIO da comunidade: é o que permite ao Engine ser função pura do snapshot. |
| `mean_temp_tolerance` | `float` | `0.0` | Largura da janela térmica média — especialista vs. generalista. |
| `mean_water_need` | `float` | `0.0` | Necessidade hídrica média. |
| `mean_size` | `float` | `0.0` | Tamanho corporal médio (entra em `size_cost`). |
| `mean_metabolism` | `float` | `0.0` | Metabolismo médio (entra em `metabolism_cost`). |
| `mean_trophic_level` | `float` | `0.0` | Nível trófico médio; `energy_match` só limita quem é produtor. |

> `biomass` é **ocupação, não limite**. O teto é a `carrying_capacity` da `ResourceSlice`,
> e quem a deriva é o Resource. Esta é a fronteira em que um Engine futuro tende a se confundir.

#### `WorldStateSnapshot`

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__post_init__` | `def __post_init__(self) -> None` | — | Congela `provenance` num `MappingProxyType` — um snapshot é fato, não acumulador. |
| `with_provenance` | `def with_provenance(self, updates: Mapping[SliceRef, tuple[str, ...]]) -> WorldStateSnapshot` | Novo snapshot com a proveniência das fatias tocadas atualizada. | Encadeia `causation_id` ENTRE ticks (uma erupção no tick 12 explicando o forçamento que cruza o patamar no tick 40). |
| `slice_of` | `def slice_of(self, ref: SliceRef) -> Any` | Lê uma fatia pelo seu identificador (acesso somente leitura). | Acesso somente leitura pelo `SliceRef` (mapa explícito `SLICE_ATTRIBUTE`, não convenção de nome). |
| `with_slice` | `def with_slice(self, ref: SliceRef, value: Any) -> WorldStateSnapshot` | Devolve um NOVO snapshot com a fatia substituída (nunca muta o atual). | Substituição imutável — nunca muta o snapshot atual. |
| `advanced` | `def advanced(self) -> WorldStateSnapshot` | Novo snapshot com o contador de tick incrementado. | Trivial: incrementa `tick`. |

#### `StateDelta`

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__post_init__` | `def __post_init__(self) -> None` | — | Congela `values`. |
| `merge` | `def merge(self, other: StateDelta) -> StateDelta` | Soma dois deltas da MESMA fatia (associativo e determinístico). | Soma deltas da MESMA fatia (associativo). Deltas de Engines distintos viram `engine_id='composed'`; a autoria original fica em cada delta. |

#### Invariantes

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `InvariantBreach` | dataclass | — | Registro de violação — insumo do `DiagnosticEvent`. Nunca altera a decisão da simulação. |
| `InvariantOutcome` | dataclass | — | Snapshot após aplicar uma invariante, com as violações observadas. |
| `Invariant` | Protocol | Protocol | Protocol: `name` + `apply(before, after) -> InvariantOutcome`. |
| `NonNegativeStocks` | dataclass | — | **Repara** (recorta em `floor`) e registra. O recorte é regra determinística conhecida. |
| `BoundedFraction` | dataclass | — | **Repara** (recorta em [`low`,`high`]) e registra. |
| `ConservedTotal` | dataclass | — | **NÃO repara.** Não existe reparo correto: saber que a soma se moveu não diz de qual reservatório tirar a diferença, e escolher um esconderia o defeito. |
| `CompositionOutcome` | dataclass | — | Resultado de compor deltas: novo snapshot + violações de invariante. |

#### Funções de módulo

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `apply_delta` | `def apply_delta(snapshot: WorldStateSnapshot, delta: StateDelta) -> WorldStateSnapshot` | Soma o delta à fatia que ele declara escrever, sem tocar nas demais. | Recusa com `ValueError` um delta que nomeie campo inexistente na fatia — contrato verificado em runtime. |
| `compose` | `def compose(snapshot: WorldStateSnapshot, deltas: Sequence[StateDelta], invariants: Iterable[Invariant] = ()) -> CompositionOutcome` | Compõe deltas EM ORDEM sobre o snapshot, aplicando as invariantes. | Pura e determinística; o Planet a chama UMA VEZ POR ENGINE, republicando o resultado. |
| `slice_values` | `def slice_values(target: Any) -> Mapping[str, float]` | Lê uma fatia como mapa campo->valor (útil em testes e projeções). | Utilitário de projeção/teste. |
| `difference` | `def difference(before: Any, after: Any) -> Mapping[str, float]` | Delta campo a campo entre duas versões da MESMA fatia. | Utilitário de projeção/teste. |

#### Constantes

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `WORLD_STATE_VERSION` | — | `5` | — |
| `SLICE_ATTRIBUTE` | `Mapping[SliceRef, str]` | `MappingProxyType({SliceRef.ASTRONOMY: 'astronomy', SliceRef.GEOLOGY: 'geology', SliceRef.ATMOSPHERE: 'atmosphere', SliceRef.CLIMATE: 'climate', SliceRef.HYDROLOGY: 'hydrology', SliceRef.CHEMISTRY: 'chemistry', SliceRef.RESOURCE: 'resource', SliceRef.BIOTA: 'biota', SliceRef.ECOLOGY: 'ecology', SliceRef.EVENT: 'event'})` | — |

**Ganchos de calibração.** `WORLD_STATE_VERSION` (Mesa → *Constantes de módulo*). Os
`bounds` que alimentam `BoundedFraction` vivem em `configs/simulation_params.yaml`.

**Cuidados.**
- Acrescentar ou remover campo de fatia **exige subir `WORLD_STATE_VERSION`** — o histórico
  de versões 1→5 no topo do arquivo é a documentação viva disso (a v5 removeu
  `atmosphere.oxygen`, que nunca teve escritor).
- `apply_delta` SOMA floats: uma estrutura (lista de espécies, dicionário) **não trafega**
  pelo Canal A. Isso não é limitação a contornar — é o que sustenta a semântica aditiva de
  que o replay depende (ADR 0016).
- `ConservedTotal` aplica-se **por delta**, o que a torna precisa quanto à autoria: a soma só
  pode mudar no delta de quem escreve a fatia.

---

### `engine.py` — a porta `Engine` e o contrato de tick

**Arquivo:** `src/ecosfera_ai/shared_kernel/engine.py` · 173 linhas

**Docstring de topo (extraída):** Porta comum de Engine de simulação (Spec §5.2) e o contexto de um tick.


**Propósito.** Um Engine é uma função pura disfarçada de objeto: recebe snapshot read-only e
RNG semeado, devolve o delta da sua fatia e os eventos que julgou notáveis. Não persiste, não
loga, não mede tempo, não conhece outro Engine.

**Por que `tick` é SÍNCRONO.** Corrotinas introduzem ordem de escalonamento como variável
oculta; sob `asyncio` a mesma semente poderia produzir intercalações distintas e o replay
bit-a-bit deixaria de valer. A fronteira síncrono/assíncrono é, deliberadamente, a mesma
fronteira determinístico/observável (ADR 0008).



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `EngineGraphError` | classe | Exception | Registro inconsistente — falha no BOOT, nunca em produção. |
| `TickBudget` | dataclass | — | Teto declarado por tick. Estourar emite `DiagnosticEvent` e **nada mais**. |
| `PerfSample` | dataclass | — | Medida LATERAL de um tick; nunca entra no world-state nem no envelope científico. |
| `TickContext` | dataclass | — | Tudo o que um Engine pode ver do mundo — e nada além. |
| `TickResult` | dataclass | — | Saída de um Engine: delta (Canal A), eventos (Canal B), entidades e custo medido. |
| `Engine` | Protocol | Protocol | Protocol: `engine_id`, `reads`, `lagged_reads`, `writes`, `tick(ctx)`. |

#### `TickBudget` — campos

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `max_duration_s` | `float` | `1.0` | — |
| `max_events` | `int` | `1000` | — |
| `max_entities` | `int` | `100000` | — |

#### `TickContext` — campos

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `snapshot` | `WorldStateSnapshot` | — | — |
| `rng` | `np.random.Generator` | — | — |
| `tick` | `int` | — | — |
| `era` | `int` | — | — |
| `budget` | `TickBudget` | — | — |
| `caused_by` | `Mapping[SliceRef, tuple[str, ...]]` | `field(default_factory=dict)` | Proveniência causal do Canal A, RESTRITA ao que o Engine declarou ler — proveniência de fatia não declarada seria acesso a estado alheio pela porta dos fundos. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `seed` | `def seed(self) -> int` | — | Trivial: `snapshot.seed`. |
| `caused_by_slice` | `def caused_by_slice(self, ref: SliceRef) -> str \| None` | Primeiro evento responsável pelo valor corrente da fatia, se houver. | Primeiro `event_id` responsável pelo valor corrente da fatia — é o que permite encadear `causation_id` sem ler o Canal B de outro Engine. |

#### `PerfSample`

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `exceeded` | `def exceeded(self, budget: TickBudget) -> tuple[str, ...]` | Quais tetos do orçamento este tick estourou (vazio = dentro). | Devolve quais tetos o tick estourou; vazio = dentro. Consumido por `PlanetEngine._diagnose`. |

#### Funções de módulo

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `validate_graph` | `def validate_graph(engines: Sequence[Engine]) -> None` | Valida o grafo de dependências no boot; falha rápido e explicando. | **Verificação de boot.** Detecta os três defeitos visíveis só nas declarações: id duplicado, fatia com dois donos, e leitura para trás não declarada em `lagged_reads`. |

**Ganchos de calibração.** `TickBudget` recebe seus valores de
`configs/simulation_params.yaml → engines.budget` (Mesa → *Núcleo*).

**Cuidados.**
- `perf` sai `None` do Engine e é preenchido pelo Planet, que detém o relógio. Se o Engine se
  cronometrasse, o tempo de parede estaria dentro do valor de retorno do cálculo determinístico.
- **Leitura para trás é legítima, mas precisa ser declarada.** Não declarada, `validate_graph`
  a trata como ordem inconsistente e falha no boot com mensagem explicando o ciclo.
- Cada Engine carrega o próprio `max_duration_s`/`max_events` no `params.yaml`, mas **quem
  vigora é o `TickBudget` global** — ver *Achados* nº 4.

---

### `events.py` — o envelope §4

**Arquivo:** `src/ecosfera_ai/shared_kernel/events.py` · 296 linhas

**Docstring de topo (extraída):** Envelope comum de Domain Event (Canal B — Spec §4, ADR-ARCH-0002).


**Propósito.** O envelope único do Canal B. Todo evento significativo responde, **como dado**:
o quê, quando, onde, quem, sob quais fatores ambientais, quais genes, quais recursos, por qual
causa e com quais consequências. Explicabilidade é requisito de esquema — é o que permite ao
Tutor narrar o fenômeno sem recalcular ciência.

**Duas regras estruturais valem para todos os eventos:**

- **`cause_code` é enum, nunca prosa.** A frase pedagógica é do consumidor
  (Education/AI Tutor), não do Engine científico. `DomainEvent.__post_init__` levanta
  `TypeError` se alguém tentar passar uma string (ADR-ARCH-0002, Correção 1).
- **Identificadores são derivados, não sorteados.** `uuid4()` dentro do loop quebraria o
  replay: a mesma semente produziria ids diferentes. Aqui os ids saem de `uuid5` sobre
  (semente, era, tick, engine, tipo, sequência).



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `CauseCodeEnum` | Enum | StrEnum | Base **vazia de propósito**: em Python só se herda de Enum sem membros, e é isso que permite a cada Engine declarar o próprio vocabulário. |
| `CoreCauseCode` | classe | CauseCodeEnum | Causas universais da moldura — nenhuma delas é científica. |
| `Granularity` | Enum | StrEnum | `AGGREGATE` é o padrão; `PER_ORGANISM` existe para investigação pontual (Correção 2). |
| `SimulationTime` | dataclass | — | QUANDO em tempo de SIMULAÇÃO — não relógio de parede. |
| `DomainEvent` | dataclass | — | O envelope §4, campo a campo. |
| `EventEmitter` | dataclass | — | Fábrica de eventos de um Engine em um tick; o contador interno entra na derivação do id. |
| `UnknownCauseCodeError` | classe | ValueError | Uma trilha veio de uma versão com Engines que esta não tem. Falhar é melhor que degradar em silêncio. |

#### `DomainEvent` — campos do envelope

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `event_id` | `str` | — | — |
| `event_type` | `str` | — | — |
| `engine_id` | `str` | — | — |
| `occurred_at` | `SimulationTime` | — | — |
| `seed` | `int` | — | — |
| `cause_code` | `CauseCodeEnum` | — | — |
| `correlation_id` | `str` | — | — |
| `causation_id` | `str \| None` | `None` | — |
| `location` | `Mapping[str, str]` | `field(default_factory=dict)` | — |
| `participants` | `tuple[str, ...]` | `()` | — |
| `environmental_factors` | `tuple[str, ...]` | `()` | — |
| `genes` | `tuple[str, ...]` | `()` | — |
| `resources` | `tuple[str, ...]` | `()` | — |
| `cause_detail` | `Mapping[str, float \| int \| str]` | `field(default_factory=dict)` | — |
| `consequences` | `tuple[str, ...]` | `()` | — |
| `granularity` | `Granularity` | `Granularity.AGGREGATE` | — |

#### `CoreCauseCode` — vocabulário universal

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `TICK_CLOSED` | — | `'TICK_CLOSED'` | — |
| `ERA_CLOSED` | — | `'ERA_CLOSED'` | — |
| `BUDGET_EXCEEDED` | — | `'BUDGET_EXCEEDED'` | — |
| `INVARIANT_BREACH` | — | `'INVARIANT_BREACH'` | — |
| `ENGINE_HEARTBEAT` | — | `'ENGINE_HEARTBEAT'` | — |

#### Funções de módulo

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `deterministic_id` | `def deterministic_id(*parts: object) -> str` | Deriva um UUID estável a partir das partes — mesma entrada, mesmo id. | UUID5 sobre as partes — mesma entrada, mesmo id. É o que torna o replay comparável por `event_id`. |
| `correlation_id_for` | `def correlation_id_for(seed: int, era: int, tick: int) -> str` | Correlação de um tick inteiro: agrupa a cadeia causal daquele instante. | Agrupa a cadeia causal de um tick inteiro. |
| `diagnostic_event` | `def diagnostic_event(emitter: EventEmitter, cause_code: CauseCodeEnum, detail: Mapping[str, float \| int \| str], *, causation_id: str \| None = None) -> DomainEvent` | Evento da visão técnica (orçamento, invariante) — mesmo envelope §4. | Visão técnica no MESMO envelope; um segundo formato violaria a fonte única de verdade. |
| `_cause_code_registry` | `def _cause_code_registry() -> dict[str, CauseCodeEnum]` | Mapa `valor -> membro` de TODOS os vocabulários de causa declarados. | Varre as subclasses de `CauseCodeEnum` — é o que mantém o envelope agnóstico a Engines novos. |
| `event_to_dict` | `def event_to_dict(event: DomainEvent) -> dict[str, Any]` | Envelope §4 completo como dado portável (JSON-compatível). | Forma portável (JSON) do envelope completo. |
| `event_from_dict` | `def event_from_dict(data: Mapping[str, Any]) -> DomainEvent` | Reconstrói o evento a partir do dado portável. | Reconstrói; recusa `cause_code` de vocabulário desconhecido. |

#### Constantes

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `EVENT_NAMESPACE` | — | `uuid.UUID('6f9619ff-8b86-d011-b42d-00c04fc964ff')` | **Nunca alterar**: invalidaria os ids de todos os eventos já gravados. |
| `DIAGNOSTIC_EVENT_TYPE` | — | `'DiagnosticRaised'` | Tipo reservado ao Canal B técnico; nunca realimenta a simulação. |

**Ganchos de calibração.** `EVENT_NAMESPACE` (Mesa → *Constantes de módulo*).

**Cuidados.**
- Um `event_type` novo precisa entrar em `configs/event_observations.yaml` para virar
  observação do motor causal; senão ele existe na trilha e é invisível ao Tutor.
- A visão técnica e a científica **particionam** a trilha (`is_diagnostic`): nada some, nada
  duplica — o teste soma as duas (ADR 0022 §1).

---

### `rng.py` — determinismo por semente

**Arquivo:** `src/ecosfera_ai/shared_kernel/rng.py` · 45 linhas

**Docstring de topo (extraída):** Fábrica determinística de RNG por (semente, engine, tick) — RF-023.


**Propósito.** Cada Engine recebe um `numpy.random.Generator` derivado da tripla
(semente do planeta, `engine_id`, tick). Três consequências desejadas: reprodutível,
independente entre Engines (acrescentar ou reordenar um Engine não desloca os sorteios dos
outros) e sem estado global (`random.seed()` seria estado de processo).



| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `engine_entropy` | `def engine_entropy(engine_id: str) -> int` | Converte o nome do Engine em entropia ESTÁVEL entre processos. | BLAKE2b, não `hash()`: o hash do Python é aleatorizado por processo (PYTHONHASHSEED) e daria trajetórias diferentes a cada execução. |
| `seed_sequence_for` | `def seed_sequence_for(seed: int, engine_id: str, tick: int) -> np.random.SeedSequence` | Sequência de semente do par (Engine, tick) sob a semente do planeta. | `SeedSequence([seed, tick, entropia_do_engine])`. |
| `rng_for` | `def rng_for(seed: int, engine_id: str, tick: int) -> np.random.Generator` | Gerador semeado que o Planet Engine entrega ao Engine no `TickContext`. | O que o Planet Engine entrega no `TickContext`. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_DIGEST_BYTES` | — | `8` | — |

**Cuidados.** Engines usam **só** o gerador recebido. Qualquer biblioteca que sorteie a partir
do estado global do módulo `random` contamina o resultado e mata o replay.

---

### `replay.py` — reconstrução bit-a-bit

**Arquivo:** `src/ecosfera_ai/shared_kernel/replay.py` · 109 linhas

**Docstring de topo (extraída):** Contrato de replay (Spec §7): reconstruir uma era bit-a-bit a partir da semente.


**Propósito.** Reconstruir uma era a partir de (semente, checkpoint, log de eventos), e
**conferir** que o resultado bate.

A reconstrução é por **reexecução**, não por reaplicação de deltas gravados. Reaplicar deltas
só provaria que a serialização funciona; reexecutar prova a propriedade que interessa — que a
semente basta. Divergência é bug de determinismo e bloqueia merge (Spec §7).



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `StepOutcome` | dataclass | — | Um passo de reexecução. |
| `ReplayMismatchError` | classe | Exception | Determinismo quebrado. |
| `ReplayReport` | dataclass | — | Resultado auditável; `deterministic` só é verdadeiro se TUDO o que se pôde comparar bateu. |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `replay` | `def replay(seed: int, checkpoint: WorldStateSnapshot, events: Sequence[DomainEvent], *, stepper: Stepper, until_tick: int) -> WorldStateSnapshot` | Reconstrói o estado em `until_tick` a partir do checkpoint (Spec §7). | Conveniência sobre `verify_replay`. |
| `verify_replay` | `def verify_replay(seed: int, checkpoint: WorldStateSnapshot, events: Sequence[DomainEvent], *, stepper: Stepper, until_tick: int, expected: WorldStateSnapshot \| None = None) -> ReplayReport` | Reconstrói e confere: mesma sequência de eventos e mesmo estado final. | Confere DUAS coisas: a mesma sequência de `event_id` e (quando `expected` é dado) o mesmo estado final. Recusa checkpoint de outra semente e detecta stepper que não avança o tick. |

**Cuidados.**
- O `stepper` é **injetado** (na prática, `PlanetEngine.stepper()`), não importado — é o que
  mantém este módulo puro e testável sem montar um registro de Engines.
- O caminho de replay roda com `publish=False`: reconstruir uma era é **reproduzir, não
  reocorrer**. Sem isso, cada `GET /eras/{era}` reemitiria a trilha inteira e o Tutor veria
  erupções acontecerem duas vezes.

---

### `observability.py` — os quatro pilares

**Arquivo:** `src/ecosfera_ai/shared_kernel/observability.py` · 221 linhas

**Docstring de topo (extraída):** Contrato de Observabilidade da moldura (Spec §6, ADR-ARCH-0002).


**Propósito.** Quatro pilares sobre UMA fonte de verdade (o Event Store): eventos, logs,
métricas e traces. Logs e métricas são PROJEÇÕES; nenhum deles é consultado pela simulação.

> **A invariante que este módulo existe para proteger:** a simulação nunca depende dos logs.
> Os logs dependem da simulação.

Operacionalmente vira uma regra de chamada, verificada em
`tests/unit/test_observability_purity.py`: **o sink é acionado pelo Planet Engine DEPOIS de
compor o tick**, jamais por um Engine durante o cálculo. Medir o tempo é permitido; reagir a
ele dentro do loop, não.



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `ObservabilitySink` | Protocol | Protocol | Protocol dos três sinais: `record_metrics`, `emit`, `log`. |
| `NullSink` | classe | — | Descarta tudo. Existe para que 'sem observabilidade' seja escolha explícita, e não um `if sink is not None` espalhado pelo Planet. |
| `InMemoryEventStore` | dataclass | — | Event Store append-only do processo — fonte de verdade até o M5. |
| `PrometheusMetricsSink` | classe | — | Pilar 3. Deriva o contador de orçamento do EVENTO, não de um canal paralelo. |
| `StructlogSink` | classe | — | Pilar 2 — logs como projeção dos eventos, correlacionados por `correlation_id`. |
| `CompositeSink` | dataclass | — | Encaminha o mesmo sinal a vários sinks, na ordem declarada. |

#### `InMemoryEventStore` — as três projeções

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `events` | `def events(self) -> tuple[DomainEvent, ...]` | — | — |
| `record_metrics` | `def record_metrics(self, sample: PerfSample) -> None` | — | No-op: o Event Store guarda eventos; métricas têm sink próprio. |
| `emit` | `def emit(self, event: DomainEvent) -> None` | — | — |
| `log` | `def log(self, message: str, /, **fields: object) -> None` | — | — |
| `by_correlation` | `def by_correlation(self, correlation_id: str) -> tuple[DomainEvent, ...]` | Cadeia causal de um instante — a consulta que o Tutor faz (Pilar 4). | Cadeia causal de um instante — a consulta que o Tutor faz (Pilar 4). |
| `scientific_view` | `def scientific_view(self) -> tuple[DomainEvent, ...]` | Projeção científica: tudo menos o diagnóstico técnico. | Tudo menos o diagnóstico técnico. |
| `technical_view` | `def technical_view(self) -> tuple[DomainEvent, ...]` | Projeção técnica: só os `DiagnosticEvent`s. | Só os `DiagnosticEvent`. |

#### Tracing (Pilar 4)

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `configure_tracing` | `def configure_tracing(*, enabled: bool) -> None` | Liga/desliga os spans da moldura (default: desligado). | — |
| `tracing_enabled` | `def tracing_enabled() -> bool` | — | — |
| `span` | `def span(name: str, **attributes: object) -> Iterator[None]` | Span por Engine/tick. No-op enquanto o tracing estiver desligado. | Span por Engine/tick. **No-op enquanto o tracing estiver desligado** (padrão). |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_TRACING_ENABLED` | — | `False` | — |

**Cuidados.**
- **O Pilar 4 é um gancho, não uma implementação.** O M2 prometeu OpenTelemetry para o M5;
  não entrou, e a promessa foi corrigida em vez de mantida como texto morto. O que o gancho
  garante é o PONTO DE ENGATE. A cadeia causal já é reconstruível por
  `correlation_id`/`causation_id` no Event Store, que é o traço que o tutor consome (ADR 0022 §5).
- `_TRACING_ENABLED` é estado de MÓDULO alterado por `configure_tracing` — é o único estado
  global do pacote, e é observável, não decisório.

---

### `portable.py` — artefato exportável

**Arquivo:** `src/ecosfera_ai/shared_kernel/portable.py` · 144 linhas

**Docstring de topo (extraída):** Artefato PORTÁVEL de uma simulação: export, import e verificação de replay.


**Propósito.** Uma simulação deixa de viver só no banco de quem a rodou e vira um arquivo que
atravessa máquinas: o pesquisador leva a corrida, o professor recebe o planeta da turma, um
bug de campo vira artefato anexado ao relato (critério do M5, Spec §8).

**O que carrega, e por quê:** semente + versão dos parâmetros (sem eles o replay não reproduz
nada, e recalibrar muda a trajetória); `world_state_version` (um checkpoint da v3 lido como v5
traria fatias ausentes); checkpoints por era (âncoras do replay); e o event log íntegro, no
envelope §4 completo.

**O que NÃO carrega: nenhum dado de aluno.** A telemetria pedagógica (RF-071) vive noutra
trilha, com consentimento e retenção próprios (RNF-009); misturá-las faria de todo export de
pesquisa um export de dado pessoal.



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `IncompatibleExportError` | classe | ValueError | O artefato não pode ser importado com segurança nesta versão. |
| `SimulationExport` | dataclass | — | Uma simulação inteira, portável e versionada. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `to_json` | `def to_json(self, *, indent: int \| None = None) -> str` | Serializa de forma DETERMINÍSTICA (chaves ordenadas). | **Determinístico** (`sort_keys=True`): duas exportações da mesma simulação dão byte a byte o mesmo arquivo, o que permite comparar artefatos por hash. |
| `from_json` | `def from_json(cls, raw: str) -> SimulationExport` | — | Recusa formato ou `world_state_version` diferentes — falhar alto é deliberado. |
| `domain_events` | `def domain_events(self) -> list[DomainEvent]` | Reconstrói os eventos como objetos de domínio. | Reconstrói o Canal B como objetos de domínio. |
| `encode_events` | `def encode_events(events: Sequence[DomainEvent]) -> tuple[Mapping[str, Any], ...]` | — | Serializa o Canal B. |
| `eras` | `def eras(self) -> list[int]` | — | Trivial. |
| `checkpoint` | `def checkpoint(self, era: int) -> Mapping[str, Any]` | — | Trivial; `KeyError` quando a era não está no artefato. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `EXPORT_FORMAT_VERSION` | — | `1` | — |

**Ganchos de calibração.** `EXPORT_FORMAT_VERSION` (Mesa → *Constantes de módulo*).

**Cuidados.** Este módulo é dado e serialização: não roda tick, não conhece Engine, não lê
métrica. Um import silenciosamente degradado produziria um planeta *parecido* com o original e
diferente dele — e a diferença só apareceria como divergência de replay muito depois.

---

### `timeseries.py` — trajetória observável

**Arquivo:** `src/ecosfera_ai/shared_kernel/timeseries.py` · 124 linhas

**Docstring de topo (extraída):** Série temporal de um escalar ao longo de uma corrida — a ferramenta que faltou.


**Propósito.** A ferramenta que faltava. O M4 descobriu que o carbono não tem equilíbrio de
longo prazo (ADR 0020) e não conseguiu **mostrar** isso a ninguém: a suíte verificava correção
POR TICK, e o colapso só aparece na TRAJETÓRIA.

Este módulo **não analisa e não corrige nada** — torna a dívida observável e exportável, que é
o que o M5 se propôs: instrumentar, não consertar.

**Por que os fluxos, e não só o estoque.** Ver o CO₂ subir diz QUE o carbono escapa; não diz
ONDE. Com os quatro termos separados — desgaseificação, estoque atmosférico, troca ar↔oceano e
solo, sumidouro biótico — soma-se entrada e saída e vê-se qual termo não fecha.



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `TimeSeries` | dataclass | — | Uma corrida, canal a canal, tick a tick. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__post_init__` | `def __post_init__(self) -> None` | — | Recusa série desalinhada: ela mentiria sobre QUANDO cada valor ocorreu. |
| `channel` | `def channel(self, name: str) -> Sequence[float]` | — | Trivial. |
| `to_csv` | `def to_csv(self) -> str` | CSV — o formato que abre em qualquer planilha ou notebook. | CSV porque a finalidade é ser aberto por um humano investigando a dívida. |
| `to_json` | `def to_json(self) -> str` | — | Forma programática. |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `collect` | `def collect(snapshots: Iterable[WorldStateSnapshot], *, channels: Mapping[str, Callable[[WorldStateSnapshot], float]] = CARBON_CHANNELS, planet_id: str = '', seed: int = 0) -> TimeSeries` | Extrai as séries de uma trajetória JÁ EXECUTADA. | Consome snapshots de uma trajetória JÁ EXECUTADA; não roda tick. Mesma disciplina do sink. |

#### `CARBON_CHANNELS` — os sete canais do ciclo do carbono

| Canal | Extrai | Papel no diagnóstico |
|---|---|---|
| `geology_outgassing` | `geology.co2_flux` | **Fonte** (basal + supervulcanismo) |
| `atmosphere_co2` | `atmosphere.co2` | Estoque — o número que dispara o alarme |
| `ocean_carbon` | `chemistry.ocean_carbon` | Reservatório não-atmosférico |
| `soil_carbon` | `chemistry.soil_carbon` | Sumidouro permanente (soterramento) |
| `air_sea_flux` | `chemistry.air_sea_flux` | Troca — um fluxo, somado a um lado e subtraído do outro |
| `biomass` | `biota.biomass` | Sumidouro biótico (a Atmosphere absorve ∝ biomassa) |
| `temperature` | `climate.temperature` | Contexto mínimo para interpretar os anteriores |

**Ganchos de calibração.** `CARBON_CHANNELS` (Mesa → *Constantes de módulo*). É o instrumento
recomendado ANTES de mexer em qualquer parâmetro do ciclo do carbono.

---

### `__init__.py` — superfície pública

**Arquivo:** `src/ecosfera_ai/shared_kernel/__init__.py` · 87 linhas

**Docstring de topo (extraída):** Moldura comum de Engines: contratos que todo Engine de simulação partilha.


**Propósito.** Reexporta o que a Spec define como comum: world-state e deltas (§3), envelope
(§4), porta `Engine` e contexto (§5.2), RNG, observabilidade (§6) e replay (§7). A lista
`__all__` (41 nomes) é o contrato de superfície do pacote.



**Cuidados.** `ConservedTotal` e `EventSlice` **não** estão em `__all__`; quem os usa
(`engines/composition.py`, `engines/event/service.py`) importa do módulo direto. Não é
defeito, mas é assimetria: acrescentar um nome aqui é declarar API pública.

---
