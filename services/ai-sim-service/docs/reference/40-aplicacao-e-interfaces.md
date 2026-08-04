# Aplicação, interfaces e configuração

> Espinha factual extraída do commit `7d80534` por `scripts/generate_reference.py`; prosa curada.
> Índice: [`README.md`](README.md) · Parâmetros: [`00-mesa-de-calibracao.md`](00-mesa-de-calibracao.md)

A camada hexagonal por fora do núcleo científico. A ordem de dependência é verificada por
`import-linter` (contrato *Camadas hexagonais do servico*):

    interfaces → infrastructure → application → domain

## Nesta página

- [`application/ports/` — as portas de saída](#applicationports--as-portas-de-saída)
- [`application/simulation/` — casos de uso do motor](#applicationsimulation--casos-de-uso-do-motor)
- [`application/platform/` — Event Store e artefato portável](#applicationplatform--event-store-e-artefato-portável)
- [`application/feedback/` — o tutor embrionário](#applicationfeedback--o-tutor-embrionário)
- [`application/telemetry/` — ingestão pedagógica](#applicationtelemetry--ingestão-pedagógica)
- [`domain/` — regras causais e telemetria](#domain--regras-causais-e-telemetria)
- [`interfaces/http/` — a borda](#interfaceshttp--a-borda)
- [`config/settings.py` — as feature flags](#configsettingspy--as-feature-flags)
- [Módulos vazios por design](#módulos-vazios-por-design)

---

## `application/ports/` — as portas de saída

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `application/ports/__init__.py` | 0 | — |  |
| `application/ports/event_bus.py` | 11 | Porta de saída para publicar eventos de domínio (EDA — pub/sub). |  |
| `application/ports/job_queue.py` | 52 | Porta de saída para trabalho assíncrono pesado (Dossiê §4, ADR 0007). |  |
| `application/ports/llm.py` | 14 | Porta de saída para o LLM. No MVP usa-se NullLLM; o adaptador Ollama entra no Inc 6. |  |
| `application/ports/planet_repo.py` | 41 | Porta de saída para persistir o planeta: estado corrente e linha do tempo. |  |
| `application/ports/telemetry_repo.py` | 13 | Porta de saída para persistir telemetria/evidência (Repository + Ports&Adapters). |  |

| Porta | Protocol | Adaptadores existentes |
|---|---|---|
| Persistência de planeta | `PlanetRepository` | `InMemoryPlanetRepository`, `PostgresPlanetRepository` |
| Persistência de telemetria | `TelemetryRepository` | `InMemoryTelemetryRepository` |
| Fila assíncrona | `JobQueue` | `InlineJobQueue`, `ArqJobQueue` |
| Barramento de eventos | `EventBus` | `NullEventBus` |
| LLM | `LLMClient` | `NullLLM` (o adaptador Ollama entra no Inc 6) |

`JobStatus` — ciclo de vida de um job:

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `PENDING` | — | `'pending'` | — |
| `RUNNING` | — | `'running'` | — |
| `COMPLETE` | — | `'complete'` | — |
| `FAILED` | — | `'failed'` | — |
| `UNKNOWN` | — | `'unknown'` | — |

---

## `application/simulation/` — casos de uso do motor

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `application/simulation/__init__.py` | 0 | — |  |
| `application/simulation/advance_era.py` | 221 | Caso de uso: avançar uma era completa da simulação (RF-013/014/016). |  |
| `application/simulation/create_planet.py` | 37 | Caso de uso: criar e configurar um planeta (RF-011/012). |  |
| `application/simulation/errors.py` | 18 | Erros de aplicação da simulação — módulo LEVE, sem dependência científica. |  |
| `application/simulation/evolve_biology.py` | 134 | Caso de uso: rodar a biologia emergente de uma era (RF-031/032). |  |
| `application/simulation/replay_state.py` | 93 | Caso de uso: reconstruir o estado de uma era passada (RF-016/023). |  |
| `application/simulation/run_tick.py` | 51 | Caso de uso: avançar um tick da simulação e explicar o resultado (RF-013/014). |  |

### `run_tick.py`

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__init__` | `def __init__(self, repo: PlanetRepository, orchestrator: Ticker, explain: ExplainCausalUseCase) -> None` | — | — |
| `execute` | `async def execute(self, planet_id: str) -> TickOutcome` | — | — |

### `advance_era.py` — o caso de uso mais denso da camada

#### `advance_era.py`

**Arquivo:** `src/ecosfera_ai/application/simulation/advance_era.py` · 221 linhas

**Docstring de topo (extraída):** Caso de uso: avançar uma era completa da simulação (RF-013/014/016).


Avança uma era completa: roda `era_length` ticks, grava o checkpoint append-only, detecta
marcos, opcionalmente despacha o job de biologia e monta a explicação causal.



| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__init__` | `def __init__(self, repo: PlanetRepository, orchestrator: Ticker, explain: ExplainCausalUseCase, era_length: int, jobs: JobQueue \| None = None, *, biology_enabled: bool = False, resolves_inline: bool = True, explain_events: ExplainFromEventsUseCase \| None = None) -> None` | — | — |
| `execute` | `async def execute(self, planet_id: str) -> EraOutcome` | — | — |
| `_narrate` | `def _narrate(self, planet_id: str, base: PlanetState, state: PlanetState, domain_events: Sequence[DomainEvent], biology: BiologySummary \| None) -> tuple[CausalExplanation, tuple[CausalLink, ...], str]` | Narra a era a partir da TRILHA DE EVENTOS quando ela existe. | — |
| `_run_biology` | `async def _run_biology(self, planet_id: str, era: int) -> tuple[BiologySummary \| None, JobRef \| None]` | Despacha a evolução pela porta `JobQueue`, resolvendo conforme o backend. | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `_summary_from` | `def _summary_from(result: dict[str, Any]) -> BiologySummary` | Reidrata o resumo biológico devolvido pelo job (inline ou ARQ). | Reidrata o resumo biológico devolvido pelo job (inline ou ARQ). |
| `_biology_observations` | `def _biology_observations(biology: BiologySummary \| None) -> list[Observation]` | Traduz o resultado biológico em observações para o motor de regras. | Traduz o resultado biológico em observações para o motor de regras. |

| Constante | Tipo | Valor | Significado |
|---|---|---|---|
| `JOB_RUN_EVOLUTION` | — | `'run_evolution'` | — |
| `NARRATED_FROM_EVENTS` | — | `'events'` | A explicação veio do Event Store (caminho preferido, ADR 0011). |
| `NARRATED_FROM_STATE_DELTA` | — | `'state_delta'` | Recuo: a explicação veio do delta de estado. |
| `OBS_EXTINCTION` | — | `'extinction'` | — |
| `OBS_BIODIVERSITY` | — | `'biodiversity'` | — |

### `replay_state.py`

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__init__` | `def __init__(self, repo: PlanetRepository, orchestrator: Ticker, biology: EvolveBiologyUseCase \| None = None) -> None` | — | Recebe o `Ticker` de replay (`for_replay()`), que NÃO publica no Canal B. |
| `execute` | `async def execute(self, planet_id: str, era: int) -> ReplayOutcome` | — | — |
| `_replay_biology` | `async def _replay_biology(self, planet_id: str, era: int) -> list[SpeciesRecord]` | Reconstrói o códex reexecutando a biologia de TODAS as eras até `era`. | — |

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `EraNotFoundError` | classe | Exception | Era inexistente na linha do tempo do planeta (HTTP 404). |
| `ReplayOutcome` | dataclass | — | Estado reconstruído e o veredito da verificação de determinismo. |

### `evolve_biology.py` e `create_planet.py`

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `application/simulation/evolve_biology.py` | 134 | Caso de uso: rodar a biologia emergente de uma era (RF-031/032). | Roda a biologia emergente de uma era DENTRO do orçamento que a física publicou. **Caminho B** — gated por `biology_enabled`. |
| `application/simulation/create_planet.py` | 37 | Caso de uso: criar e configurar um planeta (RF-011/012). |  |
| `application/simulation/errors.py` | 18 | Erros de aplicação da simulação — módulo LEVE, sem dependência científica. | Módulo LEVE, sem dependência científica: importável pela borda HTTP sem arrastar o motor. |

---

## `application/platform/` — Event Store e artefato portável

### `event_query.py` — o contrato de leitura que o M6 vai assinar

#### `event_query.py`

**Arquivo:** `src/ecosfera_ai/application/platform/event_query.py` · 170 linhas

**Docstring de topo (extraída):** Contrato de LEITURA do Event Store — o que o M6 vai assinar.


O M5 entrega a **superfície de leitura** — por planeta, era, janela de ticks, correlação,
causação, `cause_code`, Engine e tipo — mais o passeio da cadeia causal do efeito até a raiz.

**Não implementa consumidores de propósito.** Fazê-lo agora fixaria decisões de produto ainda
abertas (o que `/species` significa — P-01). O M6 assina o contrato sem renegociar o formato.
Diagnóstico técnico fica **fora por padrão**: quem quiser vê-lo pede (ADR 0022 §2).



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `EventQuery` | dataclass | — | Filtro de consulta. Campos ausentes não restringem. |
| `EventStoreQuery` | Protocol | Protocol | Porta de leitura. O M6 depende DESTA assinatura, não de um adaptador. |
| `InMemoryEventQuery` | dataclass | — | Implementação sobre uma trilha em memória — a de referência do contrato. |
| `ScientificProjection` | dataclass | — | Visão CIENTÍFICA: o fenômeno, sem o ruído técnico. |
| `TechnicalProjection` | dataclass | — | Visão TÉCNICA: só o diagnóstico — orçamento estourado, invariante violada. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `query` | `def query(self, spec: EventQuery) -> Sequence[DomainEvent]` | — | — |
| `causal_chain` | `def causal_chain(self, event_id: str) -> Sequence[DomainEvent]` | Sobe a cadeia pelo `causation_id`, do efeito até a raiz. | — |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `educational_payload_is_complete` | `def educational_payload_is_complete(events: Iterable[DomainEvent]) -> bool` | A visão EDUCACIONAL é do M6 — aqui só se confere que nada lhe falta. | A visão EDUCACIONAL é do M6; aqui só se confere que o envelope carrega tudo de que ela precisará. Descobrir uma falta no M6 seria descobrir tarde. |

> **As três projeções sobre uma fonte de verdade** (ADR 0022 §1): a científica (pesquisa,
> replay, professor avançado) e a técnica (operação) **particionam** a trilha — nada some, nada
> duplica, e o teste afirma isso somando as duas. A educacional é do M6.

### `export_simulation.py`

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `ImportReport` | dataclass | — | O que a importação encontrou — auditável, não um booleano solto. |
| `ExportSimulationUseCase` | classe | — | Empacota uma simulação inteira num artefato portável. |
| `ImportSimulationUseCase` | classe | — | Recarrega um artefato e CONFERE que ele reproduz o original. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__init__` | `def __init__(self, repo: PlanetRepository) -> None` | — | — |
| `execute` | `async def execute(self, artefact: SimulationExport) -> ImportReport` | — | — |

---

## `application/feedback/` — o tutor embrionário

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `application/feedback/__init__.py` | 0 | — |  |
| `application/feedback/explain_causal.py` | 19 | Caso de uso: gerar explicação causal de um resultado do tick (RF-033/039). |  |
| `application/feedback/explain_from_events.py` | 181 | Feedback causal derivado do Event Store, não do world-state (ADR 0011). |  |

### `explain_from_events.py` — feedback derivado do Event Store

#### `explain_from_events.py`

**Arquivo:** `src/ecosfera_ai/application/feedback/explain_from_events.py` · 181 linhas

**Docstring de topo (extraída):** Feedback causal derivado do Event Store, não do world-state (ADR 0011).


Narra a cadeia causal a partir da **trilha de eventos**, não do world-state, e **sem LLM**
(ADR 0002/0011). A tradução evento→observação é **dado versionado**
(`configs/event_observations.yaml`): o consumidor conhece o VOCABULÁRIO dos eventos, nunca os
módulos dos Engines. Um Engine pode ser reescrito inteiro sem tocar naquele arquivo, desde que
continue emitindo o mesmo envelope.



| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `EventMapping` | dataclass | — | Como um tipo de evento vira uma observação do motor de regras. |
| `EventTranslation` | dataclass | — | Tabela versionada de tradução evento -> observação. |
| `CausalLink` | dataclass | — | Um elo do rastro causal, reconstruído por `causation_id`. |
| `EventExplanation` | dataclass | — | Explicação do tutor mais o rastro que a sustenta (auditabilidade). |
| `ExplainFromEventsUseCase` | classe | — | Narra a cadeia causal a partir da trilha de eventos, sem LLM. |

| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `load_translation` | `def load_translation(path: Path) -> EventTranslation` | Lê a tabela do YAML versionado. | Lê a tabela versionada do YAML. |
| `causal_trace` | `def causal_trace(events: Sequence[DomainEvent]) -> tuple[CausalLink, ...]` | Reconstrói os elos causa->efeito invertendo `causation_id`. | Reconstrói os elos causa→efeito **invertendo `causation_id`** — a relação é PROJETADA depois do fato, e é por isso que os Engines não declaram `consequences`. |

### `configs/event_observations.yaml` — a tabela de tradução

`delta_from` diz como extrair a magnitude do `cause_detail`: `field` usa o valor com o sinal
que ele tiver; `minuend`/`subtrahend` usa a diferença (travessia de faixa).

**Cuidado.** Um `event_type` sem entrada aqui **existe na trilha e é invisível ao motor de
regras**. Ao acrescentar um evento novo a um Engine, acrescente também o mapeamento — ou
registre conscientemente que ele é só trilha.

---

## `application/telemetry/` — ingestão pedagógica

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `application/telemetry/__init__.py` | 0 | — |  |
| `application/telemetry/ingest_event.py` | 45 | Caso de uso: ingerir um evento de telemetria (RF-071) respeitando consentimento. |  |

**Cuidado.** `ConsentRequiredError` é bloqueio **LGPD** (RNF-009): evento de menor sem
consentimento não é processado. Esta trilha é **separada** da simulação de propósito — o
artefato portável (`shared_kernel/portable.py`) não carrega dado de aluno, e misturá-las faria
de todo export de pesquisa um export de dado pessoal.

---

## `domain/` — regras causais e telemetria

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `domain/__init__.py` | 0 | — |  |
| `domain/feedback/__init__.py` | 0 | — |  |
| `domain/feedback/causal_rules.py` | 100 | Motor de regras causais determinístico (MVP — sem LLM). |  |
| `domain/feedback/models.py` | 53 | Modelos de domínio do feedback causal. Puros: sem FastAPI, sem I/O. |  |
| `domain/feedback/rule_loader.py` | 29 | Carrega regras causais do YAML versionado (dados, não código). |  |
| `domain/telemetry/__init__.py` | 0 | — |  |
| `domain/telemetry/models.py` | 42 | Modelos de telemetria pedagógica (RF-071) e Evidência (Modelagem §8). |  |

### `causal_rules.py` — o motor determinístico (sem LLM)

| Classe | Forma | Bases | O que é |
|---|---|---|---|
| `CausalRule` | dataclass | — | Regra determinística: (cause, direction_in) -> (effect, direction_out). |
| `CausalRuleEngine` | classe | — | Encadeia regras a partir das observações do tick, produzindo a cadeia causal. |

| Membro | Assinatura | O que faz | Nota |
|---|---|---|---|
| `__init__` | `def __init__(self, rules: list[CausalRule], max_depth: int = 3) -> None` | — | — |
| `explain` | `def explain(self, planet_id: str, observations: list[Observation]) -> CausalExplanation` | — | — |
| `_summarize` | `def _summarize(chain: list[CausalStep]) -> str` | — | — |

### `configs/causal_rules.yaml` — as regras como dado versionado

`same_direction: true` ⇒ causa↑ implica efeito↑; `false` ⇒ causa↑ implica efeito↓. A versão
corrente é **4** (M2: entram as regras dos ciclos fechados — água, carbono oceânico, nutrientes
e capacidade de suporte).

**Ganchos de calibração.** As regras são **narrativa**, não física: mudar uma não altera a
trajetória, altera a explicação. Mas uma regra cuja `cause`/`effect` não esteja em
`OBSERVABLE_VARIABLES` (`simulation_engine/state.py`) **nunca dispara**.

---

## `interfaces/http/` — a borda

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `interfaces/__init__.py` | 0 | — |  |
| `interfaces/http/__init__.py` | 0 | — |  |
| `interfaces/http/deps.py` | 257 | Composition root: injeta adaptadores nas portas. Único lugar que conhece concretos. |  |
| `interfaces/http/schemas/__init__.py` | 0 | — |  |
| `interfaces/http/schemas/biology.py` | 68 | — |  |
| `interfaces/http/schemas/feedback.py` | 30 | — |  |
| `interfaces/http/schemas/simulation.py` | 53 | — |  |
| `interfaces/http/schemas/telemetry.py` | 18 | — |  |
| `interfaces/http/schemas/timeline.py` | 63 | — |  |
| `interfaces/http/v1/__init__.py` | 0 | — |  |
| `interfaces/http/v1/biology.py` | 116 | — |  |
| `interfaces/http/v1/feedback.py` | 42 | — |  |
| `interfaces/http/v1/health.py` | 14 | — |  |
| `interfaces/http/v1/router.py` | 20 | — |  |
| `interfaces/http/v1/simulation.py` | 118 | — |  |
| `interfaces/http/v1/telemetry.py` | 37 | — |  |
| `interfaces/http/v1/timeline.py` | 111 | — |  |

### Rotas expostas (`api_v1_prefix = /ai/api/v1`)

| Rota | Caso de uso | RF |
|---|---|---|
| `POST /planets` | `CreatePlanetUseCase` | RF-011/012 |
| `POST /planets/{id}/tick` | `RunTickUseCase` | RF-013/014 |
| `GET /planets/{id}` | `PlanetRepository` | — |
| `POST /planets/{id}/eras` | `AdvanceEraUseCase` | RF-013/016 |
| `GET /planets/{id}/timeline` | `PlanetRepository` | Dossiê §9 |
| `GET /planets/{id}/eras/{era}` | `ReplayStateUseCase` | RF-016/023 |
| `GET /planets/{id}/codex` · `/species/{sid}` · `/ecology` | `PlanetRepository` (caminho B) | RF-031/032 |
| `GET /jobs/{job_id}` | `JobQueue` | ADR 0007 |
| `POST /ai/explain` | `ExplainCausalUseCase` | RF-033/039 |
| `POST /telemetry/events` | `IngestTelemetryUseCase` | RF-071 |
| `GET /health` | — | — |

### `deps.py` — o composition root

#### `deps.py`

**Arquivo:** `src/ecosfera_ai/interfaces/http/deps.py` · 257 linhas

**Docstring de topo (extraída):** Composition root: injeta adaptadores nas portas. Único lugar que conhece concretos.


**Único lugar que conhece adaptadores concretos.** Todas as escolhas de backend acontecem aqui,
por feature flag.



| Função | Assinatura | O que faz | Nota |
|---|---|---|---|
| `get_event_store` | `def get_event_store() -> InMemoryEventStore` | Event Store do processo — fonte de verdade do Canal B até o M5. | — |
| `get_observability_sink` | `def get_observability_sink() -> ObservabilitySink` | Compõe os pilares: Event Store + métricas + logs + contadores de domínio. | Compõe os quatro pilares num `CompositeSink`: Event Store + métricas + logs + os contadores de domínio por Engine. |
| `get_orchestrator` | `def get_orchestrator() -> Ticker` | Caminho de simulação: a moldura de Engines, e desde o M2 o único. | O caminho de simulação — a moldura de Engines, e desde o M2 o único. |
| `get_planet_repo` | `def get_planet_repo() -> PlanetRepository` | Seleciona o adaptador da porta conforme a feature flag de persistência. | Seleciona o adaptador conforme `persistence_backend`. |
| `get_evolve_biology_use_case` | `def get_evolve_biology_use_case() -> EvolveBiologyUseCase` | A capacidade de suporte não é mais injetada: vem publicada no estado. | A capacidade de suporte não é mais injetada: vem PUBLICADA no estado pelo Resource Engine. |
| `get_job_queue` | `def get_job_queue() -> JobQueue` | Seleciona a fila conforme a flag; o handler do job é registrado no inline. | Seleciona a fila conforme `job_backend`; o handler do job é registrado no inline. |
| `get_replay_orchestrator` | `def get_replay_orchestrator() -> Ticker` | Motor da reconstrução: mesmo cálculo, SEM publicar no Canal B. | Mesmo cálculo, **sem publicar** no Canal B. Sem isto, cada consulta a uma era reemitiria a trilha daquela era. |

**Cuidados.** `PlanetStateOut` expõe **treze campos** — os do M1. Toda a ciência do M2/M3/M4
(pH, nutrientes, `carrying_capacity`, riqueza, pirâmide trófica, estado de evento e telegrafia)
está no `PlanetState` e **não** no contrato HTTP. Ver *Achados* nº 11 e nº 12.

---

## `config/settings.py` — as feature flags

### `config/settings.py`

**Arquivo:** `src/ecosfera_ai/config/settings.py` · 84 linhas

**Docstring de topo (extraída):** Configuração via variáveis de ambiente (12-factor), com Pydantic Settings.


Configuração 12-factor com Pydantic Settings, prefixo `ECOSFERA_`, arquivo `.env`.



| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `model_config` | — | `SettingsConfigDict(env_prefix='ECOSFERA_', env_file='.env', extra='ignore')` | — |
| `app_name` | `str` | `'ecosfera-ai-sim-service'` | — |
| `environment` | `str` | `Field(default='dev')` | — |
| `log_level` | `str` | `Field(default='INFO')` | — |
| `log_json` | `bool` | `Field(default=False)` | — |
| `api_v1_prefix` | `str` | `'/ai/api/v1'` | — |
| `causal_rules_path` | `Path` | `Field(default=Path('configs/causal_rules.yaml'))` | Regras causais versionadas. |
| `simulation_params_path` | `Path` | `Field(default=Path('configs/simulation_params.yaml'))` | Parâmetros do núcleo determinístico. |
| `event_observations_path` | `Path` | `Field(default=Path('configs/event_observations.yaml'))` | Tradução evento → observação (ADR 0011). |
| `persistence_backend` | `str` | `Field(default='inmemory')` | `inmemory` (dev/teste) \| `postgres` (staging/prod). |
| `biology_enabled` | `bool` | `Field(default=False)` | **Gate da fronteira determinístico × IA.** `False` por padrão desde o M3: o que ela liga é o caminho B, com aptidão escalar que a DEC-01 proíbe (ADR 0017). A biologia do Evolution/Ecology Engine NÃO depende dela. |
| `job_backend` | `str` | `Field(default='inline')` | `inline` (dev/teste) \| `arq` (Redis). |
| `redis_dsn` | `str` | `Field(default='redis://localhost:6379')` | — |
| `database_url` | `str` | `Field(default='postgresql+asyncpg://ecosfera:ecosfera@localhost:5432/ecosfera')` | — |
| `tracing_enabled` | `bool` | `Field(default=False)` | Spans da moldura (Pilar 4). No-op enquanto desligado — o gancho garante o ponto de engate, não a instrumentação. |
| `llm_enabled` | `bool` | `Field(default=False)` | Ligado no Inc 6. |
| `ollama_base_url` | `str` | `Field(default='http://localhost:11434')` | — |
| `llm_model` | `str` | `Field(default='llama3')` | — |
| `request_timeout_s` | `float` | `Field(default=3.0)` | — |

> **`ECOSFERA_ENGINES_FRAMEWORK` foi REMOVIDA no M2** (ADR 0014): a moldura de Engines é o
> único caminho de simulação, e não há mais um segundo motor para a flag escolher. Definir a
> variável de ambiente hoje **não faz nada**.

---

## Módulos vazios por design

| Arquivo | Linhas | Propósito (docstring de topo) | Nota |
|---|---|---|---|
| `agents/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. |  |
| `models/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. |  |
| `pipelines/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. |  |
| `rag/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. |  |
| `embeddings/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. |  |
| `evaluation/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. |  |

Todos carregam a mesma docstring — "Ativado em incremento posterior (ver docs/adr/0002).
Vazio por design." — e existem para reservar o lugar arquitetural do Inc 6/7.

`main.py` (30 linhas) é a fábrica da aplicação FastAPI: `create_app()` monta logging, métricas,
handlers RFC 7807 e o router v1.
