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
Desde o M2 o tick roda por **oito Engines**, sem adaptador nem fatia órfã
(ADR 0012/0013/0014):

```
astronomy -> geology -> chemistry -> atmosphere -> climate -> hydrology -> resource -> biota
```

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

## Moldura de Engines — o único caminho de simulação (M0 → M2)
A arquitetura de Engines do Dossiê v3 §10.4 (ADR-ARCH-0001) foi adotada de dentro
para fora. O M0 entregou a moldura; o M1 entregou os três primeiros Engines
científicos e o primeiro feedback físico real; o **M2 fechou os ciclos
determinísticos e aposentou o caminho legado** (ADR 0012/0013/0014).

```
shared_kernel/         world-state e deltas (§3), envelope de evento (§4), porta
                       Engine + contexto de tick (§5.2), RNG semeado, contrato de
                       observabilidade (§6), replay (§7)
engines/planet/        Planet Engine — orquestra, e não conhece Engine algum
engines/composition.py registra os oito Engines na ordem de acoplamento
engines/bridge.py      tradução PlanetState <-> WorldStateSnapshot
engines/astronomy/     órbita (Verlet) e irradiância incidente          (M2)
engines/geology/       vulcanismo, relevo e a FONTE de carbono          (M1)
engines/chemistry/     troca ar<->oceano, pH, nutrientes e N/P/S        (M2)
engines/atmosphere/    estoque de CO2 e forçamento radiativo log        (M1)
engines/climate/       temperatura a partir do forçamento               (M1)
engines/hydrology/     quatro reservatórios de água e a criosfera       (M2)
engines/resource/      capacidade de suporte (lei do mínimo de Liebig)  (M2)
engines/biota/         biomassa agregada — PROVISÓRIO até o M3          (M2)
engines/noop/          Engine trivial que prova a moldura (critério do M0, §8)
```

### Ordem de acoplamento
```
astronomy → geology → chemistry → atmosphere → climate → hydrology → resource → biota
```
Cada posição tem razão física: a insolação é a entrada de energia de tudo abaixo,
a geologia desgaseifica, a química publica a troca com o oceano, a atmosfera
integra o carbono já debitado, o clima converte forçamento em temperatura, a água
se move com o calor recém-resolvido, o recurso traduz o ambiente em capacidade de
suporte, e a biota a gasta.

A ordem é **verificada no boot**, não apenas documentada: `validate_graph` recusa
qualquer leitura para trás que não esteja declarada em `lagged_reads`.

### Os feedbacks modelados
```
vulcanismo (geology) → +CO2 (atmosphere) → +forçamento → +temperatura (climate)
                            ↕ troca ar<->oceano (chemistry)
temperatura → evaporação/degelo (hydrology) → albedo → temperatura   [defasado]
água + nutriente + energia + calor → capacidade (resource) → biomassa (biota)
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

### O Biota é PROVISÓRIO
`engines/biota/` porta a física determinística do antigo `life` e nada mais:
crescimento logístico, abiogênese por limiar, ruído demográfico. **Zero**
evolução, especiação, genoma, mutação ou ABM — e nenhum import de `deap`, `mesa`
ou `simulation_engine/biology/`, o que o import-linter transforma em erro de
build. É substituído pela evolução emergente no M3 (ADR 0013).

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
subsistema de simulação, não Engine (ADR 0014). `platform/` e `consumers/` da
Spec §1 nascem no M5/M6.

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
