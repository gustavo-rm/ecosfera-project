# Núcleo determinístico e plataforma

> Espinha factual extraída do commit `7d80534` por `scripts/generate_reference.py`; prosa curada.
> Índice: [`README.md`](README.md) · Parâmetros: [`00-mesa-de-calibracao.md`](00-mesa-de-calibracao.md)

Duas camadas convivem aqui:

- **`simulation_engine/`** — o núcleo determinístico anterior à moldura de Engines. Do que
  restou, uma parte é **viva e crítica** (`PlanetState`, `params`, `timeline`, `genome`) e
  outra está **dormente** (`biology/`, o caminho B do ADR 0017).
- **`infrastructure/` e `core/`** — a camada de plataforma: persistência, filas, logging e
  métricas. Ports & Adapters; nada científico.

## Nesta página

- [`state.py` — o `PlanetState` persistido](#statepy--o-planetstate-persistido)
- [`params.py` — carregamento dos parâmetros do núcleo](#paramspy--carregamento-dos-parâmetros-do-núcleo)
- [`timeline.py` — eras, checkpoints e replay-lite](#timelinepy--eras-checkpoints-e-replay-lite)
- [`ticker.py` e `orchestrator.py` — contratos residuais](#tickerpy-e-orchestratorpy--contratos-residuais)
- [`biology/genome.py` — o genoma inspecionável (VIVO)](#biologygenomepy--o-genoma-inspecionável-vivo)
- [`biology/` — o caminho B, dormente](#biology--o-caminho-b-dormente)
- [`infrastructure/` — persistência, filas e mensageria](#infrastructure--persistência-filas-e-mensageria)
- [`core/` — logging, métricas e erros](#core--logging-métricas-e-erros)

---

## `state.py` — o `PlanetState` persistido

**Arquivo:** `src/ecosfera_ai/simulation_engine/state.py` · 325 linhas

**Docstring de topo (extraída):** Estado do planeta e álgebra de deltas do núcleo de simulação determinístico.


**Propósito.** O objeto que a borda HTTP e a persistência de fato guardam, e o único estado que
atravessa o ciclo `snapshot → Engines → PlanetState` a cada tick. Imutável por design: cada
tick produz um NOVO estado (append-only), o que habilita replay e auditoria.

**Por que ele importa para quem calibra.** Um campo de fatia sem lugar aqui **volta a zero uma
vez por tick**. Foi por isso que o `PlanetState` cresceu de 8 para ~60 campos entre o M1 e o
M4 — cada estoque novo das fatias precisou de casa. É a dívida de rehidratação do ADR 0015, e
substituí-lo pelo `WorldStateSnapshot` continua sendo trabalho futuro.



| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `to_dict` | `def to_dict(self) -> dict[str, Any]` | Forma canônica do estado — a mesma para JSONB, export e checkpoint. | Forma canônica — a MESMA para JSONB, export portável e checkpoint. Mora no domínio, não no adaptador Postgres, porque é contrato de domínio. |
| `from_dict` | `def from_dict(cls, data: Mapping[str, Any]) -> PlanetState` | Reconstrói TOLERANDO chaves desconhecidas. | **Tolera chaves desconhecidas** — foi isso que permitiu ao M3 acrescentar fatias sem migration. O preço: um campo REMOVIDO (como `oxygen` no M5) é descartado em silêncio, e um renomeado vira default. Por isso o artefato portável carrega `world_state_version` e recusa versões diferentes. |
| `value` | `def value(self, variable: str) -> float` | Lê uma variável de estado pelo nome da linguagem ubíqua do domínio. | Lê variável pelo nome da linguagem ubíqua. |
| `apply` | `def apply(self, delta: StateDelta, bounds: StateBounds) -> PlanetState` | Aplica um delta e recorta cada variável à sua faixa física válida. | Aplica delta e RECORTA cada variável à faixa física. A órbita não é recortada — o integrador simplético é quem garante a estabilidade. |
| `advanced` | `def advanced(self) -> PlanetState` | Retorna o mesmo estado com o contador de tick incrementado (nova era). | Trivial. |
| `delta_from` | `def delta_from(self, previous: PlanetState) -> StateDelta` | Delta absoluto agregado deste estado em relação a um anterior. | Delta absoluto agregado entre dois estados. |
| `observe` | `def observe(self, previous: PlanetState, *, epsilon: float = 1e-09) -> list[Observation]` | Deriva observações (variação relativa) para o motor de feedback causal. | Deriva `Observation` (variação RELATIVA) para o motor de regras; omite variação < `epsilon` para não poluir a cadeia. |

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `PlanetSeed` | dataclass | — | A semente controla apenas a estocasticidade dos ticks — o estado inicial vem dos parâmetros versionados. |
| `StateBounds` | dataclass | — | Faixas físicas válidas (RF-014); alimentadas por `configs/simulation_params.yaml:bounds`. |
| `StateDelta` | dataclass | — | Variação aditiva de um subsistema; somável (`__add__`). |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `OBSERVABLE_VARIABLES` | `tuple[str, ...]` | `('co2', 'temperature', 'ice_cover', 'water', 'biomass', 'energy', 'solar_flux', 'volcanism', 'relief', 'salinity', 'ocean_circulation')` | Ordem canônica da narrativa (`co2` primeiro: é a alavanca pedagógica). As coordenadas orbitais ficam de fora de propósito — são estado interno do integrador. |

**Ganchos de calibração.** `OBSERVABLE_VARIABLES` (Mesa → *Constantes de módulo*); os `bounds`
(Mesa → *Núcleo*).

**Cuidados.** Acrescentar campo aqui **exige** mapeá-lo nos dois sentidos em `engines/bridge.py`,
senão ele existe no banco e nunca é preenchido. Os campos da `EventSlice` levam prefixo
`event_` para não colidirem com nomes já usados.

---

## `params.py` — carregamento dos parâmetros do núcleo

**Arquivo:** `src/ecosfera_ai/simulation_engine/params.py` · 208 linhas

**Docstring de topo (extraída):** Carrega os parâmetros de simulação do YAML versionado (dados, não código).


**Propósito.** Lê `configs/simulation_params.yaml`. Depois do M2 sobrou aqui só o que **não
pertence a um Engine**: condições iniciais, faixas físicas, progressão de eras, orçamento da
moldura e os parâmetros da camada emergente (que não é um Engine — ADR 0014).



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `InitialState` | dataclass | — | Condições iniciais do planeta (dados versionados, nunca hardcoded). |
| `TimelineParams` | dataclass | — | Parâmetros da progressão de eras (dados versionados). |
| `SimulationParams` | dataclass | — | Conjunto versionado de parâmetros que configuram o motor de simulação. |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_params` | `def load_params(path: Path) -> SimulationParams` | Lê e valida os parâmetros de simulação do YAML versionado. | Leitura TOLERANTE nas seções novas: um YAML anterior continua carregando com defaults. |
| `_engine_budget` | `def _engine_budget(raw: dict[str, Any]) -> TickBudget` | Lê o orçamento por tick da moldura, caindo no padrão quando ausente. | Cai no `TickBudget()` padrão quando a seção está ausente. |
| `initial_state` | `def initial_state(seed: PlanetSeed, params: SimulationParams) -> PlanetState` | Constrói o estado inicial de um planeta a partir da semente e dos parâmetros. | Deriva a órbita inicial dos parâmetros do **Astronomy Engine** — posição `(R, 0)` e velocidade perpendicular `sqrt(GM/R)`, opcionalmente perturbada por `eccentricity_kick`. Derivar de outra fonte permitiria estado de partida incoerente com a gravidade que o integrador usa. |
| `_floats` | `def _floats(raw: dict[str, Any]) -> dict[str, float]` | — | Trivial. |
| `_evolution_fields` | `def _evolution_fields(raw: dict[str, Any]) -> dict[str, Any]` | — | Converte contagens para `int`. |
| `_ecology_fields` | `def _ecology_fields(raw: dict[str, Any]) -> dict[str, Any]` | — | Idem. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `_EVOLUTION_INTS` | — | `frozenset({'population_size', 'generations', 'tournament_size', 'max_species'})` | — |
| `_ECOLOGY_INTS` | — | `frozenset({'steps', 'max_agents', 'max_steps'})` | — |

**Ganchos de calibração.** Todo o `configs/simulation_params.yaml` (Mesa → *Núcleo*).

---

## `timeline.py` — eras, checkpoints e replay-lite

**Arquivo:** `src/ecosfera_ai/simulation_engine/timeline.py` · 183 linhas

**Docstring de topo (extraída):** Linha do tempo do planeta: eras, checkpoints append-only e replay (Dossiê §9).


**Propósito.** O *event-sourcing-lite* do serviço (ADR 0004). Como o motor é determinístico por
semente, não é preciso gravar o estado de cada tick — bastam um **checkpoint** ao fim de cada
era e o **log de eventos** com o que NÃO é derivável: as intervenções do aluno e os marcos.

**Convenção de ordenação, única e explícita:** os eventos registrados no tick T são aplicados
ao estado em T, imediatamente antes do passo que leva de T para T+1. Gravação e replay
precisam concordar nisso.



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `EventLogEntry` | dataclass | — | Entrada append-only do log de eventos de um planeta. |
| `EraCheckpoint` | dataclass | — | Estado imutável ao FIM de uma era (Dossiê §9). |
| `EraSummary` | dataclass | — | Metadados de uma era para listagem da linha do tempo (sem o estado inteiro). |
| `StepOutcome` | Protocol | Protocol | O que o replay precisa do resultado de um tick: o estado resultante. |
| `Stepper` | Protocol | Protocol | Capacidade mínima exigida do motor pelo replay: avançar um tick. |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `intervention_delta` | `def intervention_delta(payload: Mapping[str, float \| str]) -> StateDelta` | Converte o payload de uma intervenção em `StateDelta`. | Chaves desconhecidas são IGNORADAS para que um cliente novo não quebre a reconstrução de um log antigo. |
| `apply_event` | `def apply_event(state: PlanetState, entry: EventLogEntry, bounds: StateBounds) -> PlanetState` | Aplica um evento ao estado. Só intervenções mutam; marcos são no-ops. | Só `intervention` muta o estado; marcos são no-ops na reconstrução. |
| `detect_milestones` | `def detect_milestones(planet_id: str, previous: PlanetState, current: PlanetState) -> list[EventLogEntry]` | Deriva marcos narrativos da transição entre dois estados. | Deriva `life_emerged`, `snowball` e `ice_free` da transição entre dois estados. |
| `replay` | `def replay(base: PlanetState, events: Iterable[EventLogEntry], until_tick: int, stepper: Stepper, bounds: StateBounds) -> PlanetState` | Reconstrói o estado em `until_tick` a partir de um checkpoint + eventos. | Função pura: não faz I/O, não consome relógio nem RNG próprio. |
| `summarize` | `def summarize(checkpoints: Sequence[EraCheckpoint], event_counts: Mapping[int, int]) -> list[EraSummary]` | Monta a listagem da linha do tempo a partir dos checkpoints persistidos. | Monta a listagem da linha do tempo. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `EVENT_INTERVENTION` | — | `'intervention'` | — |
| `EVENT_LIFE_EMERGED` | — | `'life_emerged'` | — |
| `EVENT_SNOWBALL` | — | `'snowball'` | — |
| `EVENT_ICE_FREE` | — | `'ice_free'` | — |
| `_DELTA_FIELDS` | `frozenset[str]` | `frozenset((f.name for f in fields(StateDelta)))` | — |

**Cuidados.** Este replay é o **do núcleo legado** (`PlanetState` + log de intervenções); o
replay da moldura vive em `shared_kernel/replay.py` e reexecuta o Planet Engine. São dois
mecanismos com o mesmo nome e propósitos distintos — não os confunda ao investigar divergência.

---

## `ticker.py` e `orchestrator.py` — contratos residuais

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `simulation_engine/ticker.py` | 32 | Capacidade de "avançar um tick", isolada do orquestrador concreto. | Protocol `Ticker` (`bounds`, `subsystem_names`, `tick`). Desde o M2 há uma única implementação — `FrameworkTickOrchestrator` —, e o Protocol permanece porque é ele que mantém os casos de uso independentes do motor. |
| `simulation_engine/orchestrator.py` | 37 | Contrato de resultado de um tick (RF-013/014/023). | Só o `TickResult` sobreviveu; o `TickOrchestrator` monolítico foi desmontado no M2, e `SUBSYSTEM_ORDER` virou `ENGINE_ORDER` — que passou a ser VERIFICADA no boot em vez de apenas documentada. |

`TickResult` — o contrato que os casos de uso consomem:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `state` | `PlanetState` | — | — |
| `delta` | `StateDelta` | — | — |
| `observations` | `list[Observation]` | — | — |
| `events` | `tuple[DomainEvent, ...]` | `()` | Canal B do tick, **já filtrado**: só a visão científica; o diagnóstico técnico nunca chega ao aluno. |

---

## `biology/genome.py` — o genoma inspecionável (VIVO)

**Arquivo:** `src/ecosfera_ai/simulation_engine/biology/genome.py` · 112 linhas

**Docstring de topo (extraída):** Genoma inspecionável das espécies (RF-031).


**Propósito.** Apesar de morar sob `biology/`, este módulo **não está dormente**: o Evolution
Engine o importa (`Genome`, `TROPHIC_PRODUCER`), e `Genome.BOUNDS` normaliza tanto a mutação
quanto a distância genética da evolução emergente.

Duas exigências o moldam: **inspecionabilidade** (RF-031 — o aluno abre o códex e vê traços com
nomes do domínio, não pesos opacos) e **emergência reproduzível** (RF-023 — o genoma é dado
imutável e puro; a estocasticidade vive no motor).



| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `temp_optimum` | `float` | — | — |
| `temp_tolerance` | `float` | — | — |
| `water_need` | `float` | — | — |
| `size` | `float` | — | — |
| `metabolism` | `float` | — | — |
| `trophic_level` | `float` | — | — |
| `BOUNDS` | `ClassVar[dict[str, tuple[float, float]]]` | `{'temp_optimum': (-40.0, 80.0), 'temp_tolerance': (1.0, 60.0), 'water_need': (0.0, 2.0), 'size': (0.01, 100.0), 'metabolism': (0.05, 3.0), 'trophic_level': (1.0, 3.0)}` | — |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `trophic_class` | `def trophic_class(self) -> int` | Nível trófico discreto usado pela cadeia alimentar da ecologia. | Discretiza `trophic_level` por arredondamento — a leitura ecológica usa isto. |
| `clamped` | `def clamped(self) -> Genome` | Retorna o genoma com todos os traços recortados às faixas válidas. | Recorta às faixas; um organismo fora da física do mundo não é biologicamente admissível. |
| `distance` | `def distance(self, other: Genome) -> float` | Distância genética normalizada [0,1] entre dois genomas. | Distância normalizada [0,1]: cada traço contribui com a diferença RELATIVA à própria faixa, de modo que traços em escalas diferentes pesem igual. **É o critério de especiação.** |
| `to_dict` | `def to_dict(self) -> dict[str, float]` | Serializa para o catálogo/API (inspecionável — RF-031). | Serializa para catálogo/API. |
| `from_dict` | `def from_dict(cls, data: dict[str, Any]) -> Genome` | Reconstrói tolerando chaves desconhecidas (evolução de schema). | Tolera chaves desconhecidas. |
| `to_vector` | `def to_vector(self) -> list[float]` | Vetor ordenado de traços — representação que o DEAP manipula. | Representação que o DEAP manipula (caminho B). |
| `from_vector` | `def from_vector(cls, vector: list[float]) -> Genome` | Reconstrói a partir do vetor do DEAP, recortando às faixas válidas. | Idem, recortando às faixas. |
| `trait_names` | `def trait_names(cls) -> list[str]` | — | Trivial. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `TROPHIC_PRODUCER` | — | `1` | — |
| `TROPHIC_HERBIVORE` | — | `2` | — |
| `TROPHIC_PREDATOR` | — | `3` | — |

**Ganchos de calibração.** `Genome.BOUNDS` e os três `TROPHIC_*` (Mesa → *Constantes de
módulo*). **`BOUNDS` é o botão oculto da velocidade de especiação**: ele multiplica
`mutation_sigma` e divide `Genome.distance`.

---

## `biology/` — o caminho B, dormente

> **Estado.** `biology_enabled = False` por padrão desde o M3 (ADR 0017). O caminho roda um AG
> do DEAP com `selTournament` sobre uma função de aptidão **ESCALAR**, o que a DEC-01 proíbe
> ("não existe função de aptidão em nenhum ponto") e o ADR-ARCH-0001 supera. A auditoria de
> conformidade desaconselhou explicitamente subir com ele ligado: publicaria como "emergente"
> um comportamento que a especificação classifica como cientificamente inválido, e o Tutor
> passaria a explicar ao aluno uma dinâmica que não é o que o texto diz ser.
>
> Desligá-lo é **contenção, não arquitetura** — não decide o destino do caminho legado, apenas
> impede que ciência sabidamente errada rode sem alguém a ter pedido. `test_path_b_is_dormant`
> guarda isso. A decisão de destino está aberta em **P-01**.
>
> **Não calibre estes módulos esperando efeito no world-state.** A biologia emergente do
> Evolution/Ecology Engine não depende desta flag: ela roda no tick, sempre.

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `simulation_engine/biology/engine.py` | 110 | Fachada da biologia emergente: uma era de evolução + ecologia (ADR 0006). | Fachada: uma era de evolução + ecologia. Centraliza a derivação da semente (`biology_seed`), que é o que garante que reconstruir o passado produza o MESMO códex. |
| `simulation_engine/biology/evolution.py` | 363 | Motor evolutivo com DEAP: seleção, cruzamento, mutação, especiação e extinção. | AG com DEAP. Salva/semeia/**restaura** o estado global do módulo `random` no `finally`, porque o DEAP usa o RNG global em todos os operadores. `_deap()` é fábrica preguiçosa: sem ela, `deap` viraria requisito de importação de toda a física. |
| `simulation_engine/biology/ecology.py` | 312 | Modelo ecológico com Mesa: dinâmica trófica EMERGENTE (TASK-0050/0051, RF-032). | ABM com Mesa; cada agente é uma POPULAÇÃO de espécie, não um indivíduo. Atualização síncrona em duas fases corrigiu três defeitos medidos no M3 (7,76% de biomassa fantasma por era, sobrepredação e dependência da ordem de iteração). |
| `simulation_engine/biology/fitness.py` | 101 | Funções de aptidão ambiental (TASK-0049). | Aptidão ESCALAR — o módulo que a DEC-01 proíbe. `environmental_fitness` multiplica cinco fatores. Não confundir com `engines/evolution/domain.local_suitability`, que é aptidão CONTEXTUAL e não é comparada entre espécies. |
| `simulation_engine/biology/codex.py` | 89 | Códex de espécies (GDD §11): o catálogo que se preenche conforme a vida evolui. | Códex de espécies (GDD §11): `SpeciesRecord` imutável com genoma, era de surgimento, linhagem (`ancestor_id`) e era de extinção. `species_id_for` é DETERMINÍSTICO — um UUID aleatório quebraria a igualdade que o replay exige. |

**Cuidados.** `FitnessParams`, `EvolutionParams` e `EcologyParams` vivem aqui e são importados
por `simulation_engine/params.py`, que por sua vez é importado por `engines/composition.py`.
É essa cadeia que tornava o `deap` requisito de import de toda a física — resolvida pela
fábrica preguiçosa, mas ainda é o acoplamento a vigiar num refactor.

---

## `infrastructure/` — persistência, filas e mensageria

Adaptadores das portas declaradas em `application/ports/`. Trocar a flag troca só o adaptador;
nenhuma camada acima muda de assinatura (ADR 0001/0005).

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `infrastructure/__init__.py` | 0 | — |  |
| `infrastructure/jobs/__init__.py` | 0 | — |  |
| `infrastructure/jobs/arq_job_queue.py` | 88 | Fila assíncrona sobre Redis com ARQ (staging/produção — ADR 0007). | Fila real sobre Redis (ADR 0007). |
| `infrastructure/jobs/inline_job_queue.py` | 58 | Fila SÍNCRONA: executa o job na hora, no mesmo processo (ADR 0007). | Executa o job na hora, no mesmo processo — padrão em dev/teste. |
| `infrastructure/jobs/worker.py` | 74 | Worker ARQ que executa o job pesado de evolução (ADR 0007). | Worker ARQ do job `run_evolution`; monta o caso de uso com persistência REAL (o worker não usa in-memory). |
| `infrastructure/llm/__init__.py` | 0 | — |  |
| `infrastructure/llm/null_llm.py` | 11 | LLM no-op usado até o Inc 6. Mantém a porta satisfeita sem dependência de Ollama. | No-op até o Inc 6 — mantém a porta satisfeita sem depender de Ollama. |
| `infrastructure/messaging/__init__.py` | 0 | — |  |
| `infrastructure/messaging/null_event_bus.py` | 13 | Barramento no-op (MVP). Inc 1/7 troca por Redis Streams (fan-out simples). | No-op; o Inc 1/7 troca por Redis Streams. |
| `infrastructure/persistence/__init__.py` | 0 | — |  |
| `infrastructure/persistence/inmemory_planet_repo.py` | 81 | Adaptador de persistência de planetas em memória (MVP/testes). | Padrão em dev/teste (`persistence_backend='inmemory'`). |
| `infrastructure/persistence/inmemory_telemetry_repo.py` | 25 | Adaptador de persistência em memória (MVP/testes). |  |
| `infrastructure/persistence/postgres_planet_repo.py` | 305 | Adaptador de persistência de planetas em PostgreSQL (SQLAlchemy 2.0 async). | Adaptador real (SQLAlchemy 2.0 async + asyncpg). O estado vai como JSONB — é por isso que ganhar campos não exige migration. |

### `postgres_planet_repo.py` — funções de módulo

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `state_to_json` | `def state_to_json(state: PlanetState) -> str` | Serializa o estado para JSONB — delegando a forma canônica ao domínio. | **Delega a forma canônica ao domínio** (`PlanetState.to_dict`) — o adaptador não define o formato. |
| `state_from_json` | `def state_from_json(raw: Any) -> PlanetState` | Reconstrói o estado tolerando chaves desconhecidas (evolução de schema). | Tolera chaves desconhecidas (evolução de schema). |
| `create_engine` | `def create_engine(database_url: str) -> AsyncEngine` | Cria o engine assíncrono (driver asyncpg). | Engine assíncrono (driver asyncpg). |
| `_species_from_row` | `def _species_from_row(row: Any) -> SpeciesRecord` | Reconstrói o registro do códex a partir da linha do Postgres. | Reconstrói o `SpeciesRecord` da linha. |

**Cuidados.** Migrations Alembic ficam em `migrations/versions/` e **não são detalhadas neste
guia** (fora de escopo): `0001_init_rag_schema.py`, `0002_create_simulation_schema.py`,
`0003_add_species_and_biology_events.py`, `0004_event_store_envelope.py`.

---

## `core/` — logging, métricas e erros

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `core/__init__.py` | 0 | — |  |
| `core/errors.py` | 80 | Handlers de erro no formato RFC 7807 (Problem Details), coerente com o Dossiê §5. | Handlers RFC 7807 (`application/problem+json`). |
| `core/logging.py` | 43 | Logging estruturado (structlog). JSON em staging/prod, legível em dev. | structlog: JSON em staging/prod, legível em dev. |
| `core/observability.py` | 62 | Métricas Prometheus (técnicas e pedagógicas) desde o Inc 0 (Dossiê §16.2). | As métricas Prometheus do serviço. Nenhuma é consultada pela simulação. |

### Métricas declaradas (`core/observability.py`)

| Métrica | Tipo | Rótulos | O que conta |
|---|---|---|---|
| `ecosfera_feedback_requests_total` | Counter | `source` | Explicações causais geradas |
| `ecosfera_telemetry_events_total` | Counter | `processed` | Eventos de telemetria ingeridos |
| `ecosfera_simulation_ticks_total` | Counter | — | Ticks determinísticos executados |
| `ecosfera_simulation_eras_total` | Counter | — | Eras avançadas (checkpoints gravados) |
| `ecosfera_simulation_replays_total` | Counter | `matched` | Reconstruções; `matched` diz se bateram com o checkpoint |
| `ecosfera_biology_generations_total` | Counter | — | Gerações do AG (**caminho B, dormente**) |
| `ecosfera_biology_speciations_total` | Counter | — | Especiações (caminho B) |
| `ecosfera_biology_extinctions_total` | Counter | — | Extinções (caminho B) |
| `ecosfera_biology_jobs_total` | Counter | `backend`, `outcome` | Jobs de evolução executados |
| `ecosfera_engine_tick_seconds` | Histogram | `engine` | Tempo de um tick, por Engine |
| `ecosfera_engine_events_emitted_total` | Counter | `engine` | Domain events emitidos, por Engine |
| `ecosfera_engine_entities_processed_total` | Counter | `engine` | Entidades processadas, por Engine |
| `ecosfera_engine_domain_events_total` | Counter | `engine`, `event_type` | Projeção do Event Store |
| `ecosfera_engine_budget_exceeded_total` | Counter | `engine`, `limit` | Tetos estourados (gera `DiagnosticEvent`) |

**Cuidados.** As cinco últimas são **laterais**: o Planet Engine as registra depois de compor o
tick, e nenhuma decisão da simulação as consulta. `engine_budget_exceeded` é derivada do
EVENTO, não de um canal paralelo — se o `DiagnosticEvent` não foi emitido, não existe teto
estourado a contar.
