# Guia de Referência e Calibração — `ai-sim-service`

> **Proveniência.** Gerado a partir do commit `7d80534`, em 2026-08-04.
> A **espinha factual** (assinaturas, tipos, defaults, valores de parâmetro, contagens) é
> **extraída do código** por `scripts/generate_reference.py`, que percorre
> `src/ecosfera_ai/**` com o módulo `ast` da biblioteca padrão — sem regex e **sem executar**
> o código auditado — e lê os `*.yaml` de ciência versionada.
> A **prosa explicativa** é curada por cima, a partir do código, dos ADRs e da Spec da moldura.
> Onde o código não sustenta uma afirmação, o guia escreve **"a confirmar"** ou **"não
> declarado"** em vez de estimar.
>
> **Re-gerar a espinha factual** (faça isso sempre que o código mudar, para ver o que o guia
> precisa refletir):
> ```bash
> cd services/ai-sim-service
> uv run python scripts/generate_reference.py --summary        # contagens de conferência
> uv run python scripts/generate_reference.py -o reference.json # JSON completo
> ```

## Cobertura

| | |
|---|---|
| Módulos `.py` de produção documentados | **163** (todo `src/ecosfera_ai/**`) |
| Arquivos de ciência versionada | **13** (10 `params.yaml` de Engine + 3 `configs/*.yaml`) |
| Excluídos | `tests/**`, `__pycache__`, artefatos gerados |
| Listados sem detalhamento | migrations Alembic (`migrations/versions/0001`–`0004`) |

## Por onde começar

**Se você veio calibrar**, vá direto para a Mesa. Ela existe para que você não precise reler o
código.

### [→ 00 · Mesa de Calibração Científica](00-mesa-de-calibracao.md)
Todo parâmetro que altera o comportamento científico, com valor atual, efeito de aumentar,
efeito de diminuir e o risco de mexer. Inclui:
- os dez `params.yaml` de Engine, agrupados por domínio;
- o catálogo de eventos, evento a evento;
- as condições iniciais e as faixas físicas;
- as **constantes de módulo que funcionam como botão** (`Genome.BOUNDS`, `WORLD_STATE_VERSION`, `_DIGEST_BYTES`…);
- as **invariantes que a calibração não pode violar**, com o teste que guarda cada uma;
- o **índice reverso** "quero calibrar X → vá para";
- as **dívidas conhecidas**, para não calibrar contra um problema já mapeado.

### [→ 10 · Moldura comum (`shared_kernel`)](10-shared-kernel.md)
World-state e fatias, envelope de evento, porta `Engine`, RNG semeado, replay, os quatro
pilares de observabilidade, artefato portável e séries temporais. **Tudo depende desta camada**,
por isso ela vem primeiro.

### [→ 20 · Engines de simulação](20-engines.md)
Na **ordem de tick real**: Planet (orquestrador) → astronomy → geology → chemistry → atmosphere
→ climate → hydrology → resource → evolution → ecology → event. Cada Engine com as fatias que
lê e escreve, a posição no tick, a física que implementa, os ganchos de calibração e as
invariantes que sustenta.

### [→ 30 · Núcleo determinístico e plataforma](30-nucleo-e-plataforma.md)
`PlanetState` (o objeto realmente persistido), parâmetros, linha do tempo, o genoma
inspecionável, o **caminho B dormente** (ADR 0017) e a camada de infraestrutura.

### [→ 40 · Aplicação, interfaces e configuração](40-aplicacao-e-interfaces.md)
Portas e adaptadores, casos de uso, contrato de leitura do Event Store, o tutor sem LLM, as
rotas HTTP e as feature flags.

### [→ 90 · Achados durante a auditoria](90-achados-da-auditoria.md)
Quatorze itens encontrados ao ler o código para este guia. **Nada foi corrigido** — é material
para o arquiteto decidir.

## O mapa em uma tela

```
                    ┌──────────────────────────────────────────┐
  Canal A           │            WorldStateSnapshot            │
  (deltas, floats)  │  10 fatias · 1 dono por fatia · imutável │
                    └──────────────────────────────────────────┘
                                       ▲
        astronomy → geology → chemistry → atmosphere → climate → hydrology
              → resource → evolution → ecology → event    (ordem do tick)
                                       │
                    ┌──────────────────▼───────────────────────┐
  Canal B           │   Event Store (append-only, envelope §4)  │
  (eventos)         │  projeções: científica · técnica · [M6]   │
                    └──────────────────────────────────────────┘
```

- **Canal A** resolve o acoplamento físico contínuo. É aditivo e de floats — uma estrutura não
  trafega por ele, e isso não é limitação a contornar: é o que sustenta o replay.
- **Canal B** registra a ocorrência notável. `cause_code` é enum, nunca prosa; a frase
  pedagógica é do consumidor.
- **A observabilidade é lateral.** O sink é acionado depois de compor o tick, e nenhuma
  decisão da simulação lê métrica, log ou trilha. É o que mantém o replay possível.

## Referências cruzadas

| Documento | Onde |
|---|---|
| Spec da moldura de Engines | `docs/architecture/ECOSFERA_Engine_Framework_Spec.md` (raiz do monorepo) |
| ADR-ARCH-0001 (arquitetura de Engines) e 0002 (observabilidade) | `docs/architecture/adr/` (raiz) |
| ADRs do serviço (0001–0022) | `services/ai-sim-service/docs/adr/` |
| Decisões pendentes (P-01, P-02) | `docs/decisions/pending.md` |
| Decisões adiadas e ciência ausente | `docs/decisions/deferred.md` |
| Auditoria de conformidade do Evolution Engine | `docs/evolution-engine/00-auditoria-conformidade.md` (raiz) |

### ADRs mais citados neste guia

| ADR | Assunto | Onde toca a calibração |
|---|---|---|
| ADR-ARCH-0001 | Arquitetura de Engines; supera o fitness global | Evolution não tem parâmetro de AG |
| ADR-ARCH-0002 | Observabilidade por design | Todo limiar de evento; pureza do sink |
| 0006 | Biologia emergente | `carrying_capacity` é o único acoplamento física↔biologia |
| 0010 | Fronteira geology/atmosphere/chemistry | `forcing_coefficient`, `equilibrium_offset` |
| 0012 | Ciclos fechados de carbono e água | `reference_ocean_carbon` ↔ `initial_state.ocean_carbon` |
| 0013 | Astronomy port e biota provisória | Parâmetros orbitais, habitabilidade |
| 0016 | Evolução emergente sem fitness global | Genoma médio, `crowding_weight` |
| 0017 | Biologia opcional e as duas trilhas | `biology_enabled=False`; caminho B dormente |
| 0018 | Event Engine, fatia de perturbação e Diretor | Catálogo, `supervolcanic_multiplier` |
| 0019 | Extinção catastrófica × ecológica | `mortality` do catálogo, `consumer_capacity_share` |
| 0020 | Instabilidade de carbono em horizonte longo | **Dívida aberta** — leia antes de calibrar carbono |
| 0021 / 0022 | Event Store portável; quatro pilares e projeções | `EXPORT_FORMAT_VERSION`, projeções |

---

## Cobertura completa — os 163 módulos de produção

Extraída do JSON, para que a afirmação de cobertura seja verificável. Os `__init__.py` de
pacote de Engine são fachadas de reexportação, cobertas pela ficha do Engine correspondente;
os `__init__.py` sem docstring são vazios de namespace. Os `observability.py` seguem um molde
único, documentado em bloco na página 20.

| Módulo | Linhas | Docstring de topo (extraída) | Página |
|---|---|---|---|
| `__init__.py` | 9 | ECOSFERA ai-sim-service — serviço Python/FastAPI de simulação e IA. | [40](40-aplicacao-e-interfaces.md) |
| `agents/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. | [40](40-aplicacao-e-interfaces.md) |
| `application/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `application/feedback/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `application/feedback/explain_causal.py` | 19 | Caso de uso: gerar explicação causal de um resultado do tick (RF-033/039). | [40](40-aplicacao-e-interfaces.md) |
| `application/feedback/explain_from_events.py` | 181 | Feedback causal derivado do Event Store, não do world-state (ADR 0011). | [40](40-aplicacao-e-interfaces.md) |
| `application/platform/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `application/platform/event_query.py` | 170 | Contrato de LEITURA do Event Store — o que o M6 vai assinar. | [40](40-aplicacao-e-interfaces.md) |
| `application/platform/export_simulation.py` | 107 | Export e import de uma simulação inteira, com verificação de replay. | [40](40-aplicacao-e-interfaces.md) |
| `application/ports/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `application/ports/event_bus.py` | 11 | Porta de saída para publicar eventos de domínio (EDA — pub/sub). | [40](40-aplicacao-e-interfaces.md) |
| `application/ports/job_queue.py` | 52 | Porta de saída para trabalho assíncrono pesado (Dossiê §4, ADR 0007). | [40](40-aplicacao-e-interfaces.md) |
| `application/ports/llm.py` | 14 | Porta de saída para o LLM. No MVP usa-se NullLLM; o adaptador Ollama entra no Inc 6. | [40](40-aplicacao-e-interfaces.md) |
| `application/ports/planet_repo.py` | 41 | Porta de saída para persistir o planeta: estado corrente e linha do tempo. | [40](40-aplicacao-e-interfaces.md) |
| `application/ports/telemetry_repo.py` | 13 | Porta de saída para persistir telemetria/evidência (Repository + Ports&Adapters). | [40](40-aplicacao-e-interfaces.md) |
| `application/simulation/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `application/simulation/advance_era.py` | 221 | Caso de uso: avançar uma era completa da simulação (RF-013/014/016). | [40](40-aplicacao-e-interfaces.md) |
| `application/simulation/create_planet.py` | 37 | Caso de uso: criar e configurar um planeta (RF-011/012). | [40](40-aplicacao-e-interfaces.md) |
| `application/simulation/errors.py` | 18 | Erros de aplicação da simulação — módulo LEVE, sem dependência científica. | [40](40-aplicacao-e-interfaces.md) |
| `application/simulation/evolve_biology.py` | 134 | Caso de uso: rodar a biologia emergente de uma era (RF-031/032). | [40](40-aplicacao-e-interfaces.md) |
| `application/simulation/replay_state.py` | 93 | Caso de uso: reconstruir o estado de uma era passada (RF-016/023). | [40](40-aplicacao-e-interfaces.md) |
| `application/simulation/run_tick.py` | 51 | Caso de uso: avançar um tick da simulação e explicar o resultado (RF-013/014). | [40](40-aplicacao-e-interfaces.md) |
| `application/telemetry/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `application/telemetry/ingest_event.py` | 45 | Caso de uso: ingerir um evento de telemetria (RF-071) respeitando consentimento. | [40](40-aplicacao-e-interfaces.md) |
| `config/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `config/settings.py` | 84 | Configuração via variáveis de ambiente (12-factor), com Pydantic Settings. | [40](40-aplicacao-e-interfaces.md) |
| `core/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `core/errors.py` | 80 | Handlers de erro no formato RFC 7807 (Problem Details), coerente com o Dossiê §5. | [30](30-nucleo-e-plataforma.md) |
| `core/logging.py` | 43 | Logging estruturado (structlog). JSON em staging/prod, legível em dev. | [30](30-nucleo-e-plataforma.md) |
| `core/observability.py` | 62 | Métricas Prometheus (técnicas e pedagógicas) desde o Inc 0 (Dossiê §16.2). | [30](30-nucleo-e-plataforma.md) |
| `domain/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `domain/feedback/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `domain/feedback/causal_rules.py` | 100 | Motor de regras causais determinístico (MVP — sem LLM). | [40](40-aplicacao-e-interfaces.md) |
| `domain/feedback/models.py` | 53 | Modelos de domínio do feedback causal. Puros: sem FastAPI, sem I/O. | [40](40-aplicacao-e-interfaces.md) |
| `domain/feedback/rule_loader.py` | 29 | Carrega regras causais do YAML versionado (dados, não código). | [40](40-aplicacao-e-interfaces.md) |
| `domain/telemetry/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `domain/telemetry/models.py` | 42 | Modelos de telemetria pedagógica (RF-071) e Evidência (Modelagem §8). | [40](40-aplicacao-e-interfaces.md) |
| `embeddings/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. | [40](40-aplicacao-e-interfaces.md) |
| `engines/__init__.py` | 6 | Camada de Simulação: um pacote por Engine (ADR-ARCH-0001, Spec §1). | [20](20-engines.md) |
| `engines/astronomy/__init__.py` | 18 | Astronomy Engine — órbita e irradiância incidente (M2). | [20](20-engines.md) |
| `engines/astronomy/contracts.py` | 52 | Fatias e parâmetros do Astronomy Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/astronomy/domain.py` | 59 | Física pura da órbita: velocity Verlet e irradiância incidente. | [20](20-engines.md) |
| `engines/astronomy/events.py` | 13 | Vocabulário de evento do Astronomy Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/astronomy/observability.py` | 26 | Métricas de domínio do Astronomy Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/astronomy/service.py` | 88 | Astronomy Engine — órbita e irradiância (o antigo subsystem `physics`). | [20](20-engines.md) |
| `engines/atmosphere/__init__.py` | 21 | Atmosphere Engine — estoque de carbono e forçamento radiativo (M1). | [20](20-engines.md) |
| `engines/atmosphere/contracts.py` | 56 | Fatias lidas/escritas e parâmetros do Atmosphere Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/atmosphere/domain.py` | 89 | Física pura da atmosfera: ciclo do carbono e forçamento radiativo. | [20](20-engines.md) |
| `engines/atmosphere/events.py` | 14 | Vocabulário de evento do Atmosphere Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/atmosphere/observability.py` | 30 | Métricas de domínio do Atmosphere Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/atmosphere/service.py` | 114 | Atmosphere Engine — estoque de carbono e forçamento radiativo. | [20](20-engines.md) |
| `engines/bridge.py` | 244 | Tradução entre o `PlanetState` persistido e o world-state da moldura. | [20](20-engines.md) |
| `engines/chemistry/__init__.py` | 25 | Chemistry Engine — ciclos biogeoquímicos e o fluxo ar<->oceano (M2). | [20](20-engines.md) |
| `engines/chemistry/contracts.py` | 60 | Fatias e parâmetros do Chemistry Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/chemistry/domain.py` | 94 | Química pura: ciclos do carbono não-atmosférico, de N/P/S e do pH. | [20](20-engines.md) |
| `engines/chemistry/events.py` | 17 | Vocabulário de evento do Chemistry Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/chemistry/observability.py` | 33 | Métricas de domínio do Chemistry Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/chemistry/service.py` | 222 | Chemistry Engine — carbono não-atmosférico, N/P/S, nutrientes e pH (M2). | [20](20-engines.md) |
| `engines/climate/__init__.py` | 19 | Climate Engine — temperatura a partir do forçamento radiativo (M1). | [20](20-engines.md) |
| `engines/climate/contracts.py` | 73 | Fatias lidas/escritas e parâmetros do Climate Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/climate/domain.py` | 76 | Física pura do clima: balanço de energia de caixa única. | [20](20-engines.md) |
| `engines/climate/events.py` | 15 | Vocabulário de evento do Climate Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/climate/observability.py` | 30 | Métricas de domínio do Climate Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/climate/service.py` | 146 | Climate Engine — resolve a temperatura a partir do forçamento radiativo. | [20](20-engines.md) |
| `engines/composition.py` | 261 | Montagem do planeta: registra os oito Engines e costura com os casos de uso. | [20](20-engines.md) |
| `engines/ecology/__init__.py` | 23 | Ecology Engine — dinâmica trófica emergente sobre a comunidade (M3). | [20](20-engines.md) |
| `engines/ecology/contracts.py` | 64 | Fatias e parâmetros do Ecology Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/ecology/events.py` | 16 | Vocabulário de evento do Ecology Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/ecology/observability.py` | 28 | Métricas de domínio do Ecology Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/ecology/service.py` | 328 | Ecology Engine — reparte a comunidade em níveis tróficos e resolve a predação. | [20](20-engines.md) |
| `engines/event/__init__.py` | 5 | Event Engine — eventos extraordinários e o Diretor (M4). | [20](20-engines.md) |
| `engines/event/contracts.py` | 82 | Fatias, parâmetros e catálogo do Event Engine (Spec §5.1, §8). | [20](20-engines.md) |
| `engines/event/director.py` | 111 | O Diretor: decide QUAIS eventos acontecem e QUANDO — deterministicamente. | [20](20-engines.md) |
| `engines/event/domain.py` | 109 | Catálogo de eventos extraordinários e seus perfis de perturbação. | [20](20-engines.md) |
| `engines/event/events.py` | 30 | Vocabulário de evento do Event Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/event/observability.py` | 51 | Métricas de domínio do Event Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/event/service.py` | 294 | Event Engine — os acontecimentos extraordinários e o Diretor (M4). | [20](20-engines.md) |
| `engines/evolution/__init__.py` | 27 | Evolution Engine — seleção natural emergente, sem fitness global (M3). | [20](20-engines.md) |
| `engines/evolution/contracts.py` | 62 | Fatias e parâmetros do Evolution Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/evolution/domain.py` | 219 | Seleção natural EMERGENTE: sobrevivência e reprodução por condição local. | [20](20-engines.md) |
| `engines/evolution/events.py` | 51 | Vocabulário de evento do Evolution Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/evolution/observability.py` | 33 | Métricas de domínio do Evolution Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/evolution/service.py` | 421 | Evolution Engine — seleção natural emergente sobre a comunidade (M3). | [20](20-engines.md) |
| `engines/geology/__init__.py` | 14 | Geology Engine — vulcanismo, relevo e a fonte de carbono (M1). | [20](20-engines.md) |
| `engines/geology/contracts.py` | 65 | Fatias lidas/escritas e parâmetros científicos do Geology Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/geology/domain.py` | 54 | Física pura da geologia: vulcanismo, relevo e desgaseificação de carbono. | [20](20-engines.md) |
| `engines/geology/events.py` | 20 | Vocabulário de evento do Geology Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/geology/observability.py` | 28 | Métricas de domínio do Geology Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/geology/service.py` | 105 | Geology Engine — vulcanismo, relevo e a FONTE de carbono do planeta. | [20](20-engines.md) |
| `engines/hydrology/__init__.py` | 23 | Hydrology Engine — ciclo da água, criosfera e circulação (M2). | [20](20-engines.md) |
| `engines/hydrology/contracts.py` | 65 | Fatias e parâmetros do Hydrology Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/hydrology/domain.py` | 107 | Física pura do ciclo da água: quatro reservatórios e os fluxos entre eles. | [20](20-engines.md) |
| `engines/hydrology/events.py` | 16 | Vocabulário de evento do Hydrology Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/hydrology/observability.py` | 31 | Métricas de domínio do Hydrology Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/hydrology/service.py` | 156 | Hydrology Engine — o ciclo da água e a criosfera (M2). | [20](20-engines.md) |
| `engines/noop/__init__.py` | 5 | Engine trivial de validação da moldura (critério do M0 — Spec §8). | [20](20-engines.md) |
| `engines/noop/service.py` | 49 | Engine trivial que prova a moldura (critério de conclusão do M0 — Spec §8). | [20](20-engines.md) |
| `engines/planet/__init__.py` | 20 | Planet Engine — orquestrador do tick determinístico (Spec §5.3). | [20](20-engines.md) |
| `engines/planet/registry.py` | 56 | Registro ordenado de Engines — sem descoberta mágica (Spec §5.3). | [20](20-engines.md) |
| `engines/planet/service.py` | 282 | Planet Engine — o orquestrador do tick (Spec §5.3, ADR-ARCH-0001 Emenda 3). | [20](20-engines.md) |
| `engines/resource/__init__.py` | 23 | Resource Engine — disponibilidade de recurso e capacidade de suporte (M2). | [20](20-engines.md) |
| `engines/resource/contracts.py` | 60 | Fatias e parâmetros do Resource Engine (Spec §5.1). | [20](20-engines.md) |
| `engines/resource/domain.py` | 119 | Recurso puro: de estado físico para orçamento biológico. | [20](20-engines.md) |
| `engines/resource/events.py` | 18 | Vocabulário de evento do Resource Engine (Canal B, envelope §4). | [20](20-engines.md) |
| `engines/resource/observability.py` | 32 | Métricas de domínio do Resource Engine (Spec §5.1/§6). | [20](20-engines.md) |
| `engines/resource/service.py` | 246 | Resource Engine — converte estado físico em orçamento biológico (M2). | [20](20-engines.md) |
| `evaluation/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. | [40](40-aplicacao-e-interfaces.md) |
| `infrastructure/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/jobs/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/jobs/arq_job_queue.py` | 88 | Fila assíncrona sobre Redis com ARQ (staging/produção — ADR 0007). | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/jobs/inline_job_queue.py` | 58 | Fila SÍNCRONA: executa o job na hora, no mesmo processo (ADR 0007). | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/jobs/worker.py` | 74 | Worker ARQ que executa o job pesado de evolução (ADR 0007). | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/llm/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/llm/null_llm.py` | 11 | LLM no-op usado até o Inc 6. Mantém a porta satisfeita sem dependência de Ollama. | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/messaging/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/messaging/null_event_bus.py` | 13 | Barramento no-op (MVP). Inc 1/7 troca por Redis Streams (fan-out simples). | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/persistence/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/persistence/inmemory_planet_repo.py` | 81 | Adaptador de persistência de planetas em memória (MVP/testes). | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/persistence/inmemory_telemetry_repo.py` | 25 | Adaptador de persistência em memória (MVP/testes). | [30](30-nucleo-e-plataforma.md) |
| `infrastructure/persistence/postgres_planet_repo.py` | 305 | Adaptador de persistência de planetas em PostgreSQL (SQLAlchemy 2.0 async). | [30](30-nucleo-e-plataforma.md) |
| `interfaces/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/deps.py` | 257 | Composition root: injeta adaptadores nas portas. Único lugar que conhece concretos. | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/schemas/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/schemas/biology.py` | 68 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/schemas/feedback.py` | 30 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/schemas/simulation.py` | 53 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/schemas/telemetry.py` | 18 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/schemas/timeline.py` | 63 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/__init__.py` | 0 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/biology.py` | 116 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/feedback.py` | 42 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/health.py` | 14 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/router.py` | 20 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/simulation.py` | 118 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/telemetry.py` | 37 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `interfaces/http/v1/timeline.py` | 111 | *(sem docstring)* | [40](40-aplicacao-e-interfaces.md) |
| `main.py` | 30 | Fábrica da aplicação FastAPI (ai-sim-service). | [40](40-aplicacao-e-interfaces.md) |
| `models/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. | [40](40-aplicacao-e-interfaces.md) |
| `pipelines/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. | [40](40-aplicacao-e-interfaces.md) |
| `rag/__init__.py` | 1 | Ativado em incremento posterior (ver docs/adr/0002). Vazio por design. | [40](40-aplicacao-e-interfaces.md) |
| `shared_kernel/__init__.py` | 87 | Moldura comum de Engines: contratos que todo Engine de simulação partilha. | [10](10-shared-kernel.md) |
| `shared_kernel/engine.py` | 173 | Porta comum de Engine de simulação (Spec §5.2) e o contexto de um tick. | [10](10-shared-kernel.md) |
| `shared_kernel/events.py` | 296 | Envelope comum de Domain Event (Canal B — Spec §4, ADR-ARCH-0002). | [10](10-shared-kernel.md) |
| `shared_kernel/observability.py` | 221 | Contrato de Observabilidade da moldura (Spec §6, ADR-ARCH-0002). | [10](10-shared-kernel.md) |
| `shared_kernel/portable.py` | 144 | Artefato PORTÁVEL de uma simulação: export, import e verificação de replay. | [10](10-shared-kernel.md) |
| `shared_kernel/replay.py` | 109 | Contrato de replay (Spec §7): reconstruir uma era bit-a-bit a partir da semente. | [10](10-shared-kernel.md) |
| `shared_kernel/rng.py` | 45 | Fábrica determinística de RNG por (semente, engine, tick) — RF-023. | [10](10-shared-kernel.md) |
| `shared_kernel/timeseries.py` | 124 | Série temporal de um escalar ao longo de uma corrida — a ferramenta que faltou. | [10](10-shared-kernel.md) |
| `shared_kernel/world_state.py` | 670 | Contrato do World-State: snapshot imutável, fatias por domínio e deltas. | [10](10-shared-kernel.md) |
| `simulation_engine/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/biology/__init__.py` | 0 | *(sem docstring)* | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/biology/codex.py` | 89 | Códex de espécies (GDD §11): o catálogo que se preenche conforme a vida evolui. | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/biology/ecology.py` | 312 | Modelo ecológico com Mesa: dinâmica trófica EMERGENTE (TASK-0050/0051, RF-032). | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/biology/engine.py` | 110 | Fachada da biologia emergente: uma era de evolução + ecologia (ADR 0006). | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/biology/evolution.py` | 363 | Motor evolutivo com DEAP: seleção, cruzamento, mutação, especiação e extinção. | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/biology/fitness.py` | 101 | Funções de aptidão ambiental (TASK-0049). | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/biology/genome.py` | 112 | Genoma inspecionável das espécies (RF-031). | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/orchestrator.py` | 37 | Contrato de resultado de um tick (RF-013/014/023). | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/params.py` | 208 | Carrega os parâmetros de simulação do YAML versionado (dados, não código). | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/state.py` | 325 | Estado do planeta e álgebra de deltas do núcleo de simulação determinístico. | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/ticker.py` | 32 | Capacidade de "avançar um tick", isolada do orquestrador concreto. | [30](30-nucleo-e-plataforma.md) |
| `simulation_engine/timeline.py` | 183 | Linha do tempo do planeta: eras, checkpoints append-only e replay (Dossiê §9). | [30](30-nucleo-e-plataforma.md) |
