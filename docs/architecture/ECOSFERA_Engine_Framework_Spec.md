# ECOSFERA — Especificação da Moldura Comum de Engines

**Versão 1.0 · Guia de implementação incremental**
Base: ADR‑ARCH‑0001 (Arquitetura de Engines) + ADR‑ARCH‑0002 (Observabilidade por Design) + Dossiê PD&I (§4/§8/§9/§15, GDD §10).

> Este documento especifica **o que é comum a todo Engine** — interface, canais, contratos, envelope de evento, observabilidade, replay e template. É a "moldura" a ser projetada de uma vez (ADR‑ARCH‑0001, Emenda 4). O contrato **específico** de cada Engine firma‑se ao construí‑lo. Valide a moldura com a fatia vertical **Geology → Atmosphere → Climate** antes de escalar em largura.

---

## 1. Camadas do sistema

| Camada | Engines | Loop determinístico? | Padrão |
|---|---|---|---|
| **Simulação** | Planet (orquestrador), Geology, Atmosphere, Climate, Hydrology, Chemistry, Evolution, Ecology, Resource, Event | Sim (tick por seed) | Template completo (§5) |
| **Plataforma/Infra** | Persistence, Observability (Event Store) | Não | Ports & Adapters (hexagonal) |
| **Consumidores** (read‑side) | Analytics, Education, AI Tutor | Não (assíncrono) | Assinam o Event Store; nunca recalculam ciência |

**Localização no código** (dentro do `ai-sim-service`, ADR‑ARCH‑0001 Emenda 1):
```
src/ecosfera_ai/
  engines/
    planet/         # orquestrador (era o TickOrchestrator)
    geology/  atmosphere/  climate/  hydrology/  chemistry/
    resource/  event/
    evolution/  ecology/        # emergentes (ADR‑ARCH‑0001)
  platform/
    persistence/    # Persistence Engine (adaptadores Postgres/Mongo)
    observability/  # Event Store + pilares (§6)
  consumers/
    analytics/  education/  ai_tutor/   # ai_tutor = ai_engine (Inc 6)
  shared_kernel/    # world-state, envelope de evento, tipos comuns (§3, §4)
```

---

## 2. Dois canais de comunicação

### Canal A — World‑State + deltas por tick (determinístico)
Para **acoplamento físico contínuo**. O Planet Engine expõe um **snapshot read‑only versionado** do world‑state; cada Engine lê apenas as fatias de que depende (declaradas) e devolve um **delta** só da sua fatia. O Planet Engine compõe os deltas em **ordem definida** (§5.3). Nenhum Engine escreve no estado de outro.

### Canal B — Domain Events (discreto, append‑only)
Para **ocorrências notáveis** (erupção, especiação, extinção, início de seca, evento climático). Vão ao **Event Store** (fonte de verdade, ADR‑ARCH‑0002). Consumidores (Tutor, Education, Analytics, Observability) assinam **apenas** este canal — nunca o world‑state interno.

**Regra de ouro (enforce em CI):** um Engine de simulação **produz** deltas (Canal A) e **emite** eventos (Canal B); **não importa** outro Engine nem lê seu estado interno. Consumidores **só** leem o Event Store.

---

## 3. Contrato do World‑State

- `WorldStateSnapshot` — **imutável e versionado** (`version`, `tick`, `era`, `seed`). Composto por **fatias** tipadas por domínio: `GeologySlice`, `AtmosphereSlice`, `ClimateSlice`, `HydrologySlice`, `ChemistrySlice`, `ResourceSlice`, `BiotaSlice` (evolução/ecologia).
- Cada Engine declara `reads: set[SliceRef]` e `writes: SliceRef` (uma só). O Planet Engine valida o grafo de dependências no boot (detecta ciclos não resolvidos).
- Deltas: `StateDelta` carrega apenas a fatia escrita + metadados (`engine_id`, `tick`, `caused_by: list[EventId]`). Composição associativa e determinística.
- **Invariantes** (testadas): não‑negatividade de estoques; conservação aproximada de massa/energia com tolerância declarada por Engine.

---

## 4. Envelope de Evento (schema comum + explicabilidade)

Todo domain event usa o mesmo envelope. Os campos de explicabilidade são **requisito**, não opção (ADR‑ARCH‑0002, Correção 1): garantem que um consumidor explique o fenômeno **sem recalcular ciência**.

```jsonc
{
  "event_id": "uuid",
  "event_type": "PopulationDeclined",      // vocabulário do domínio
  "engine_id": "evolution",
  "occurred_at": { "tick": 1287, "era": 4 },// QUANDO (tempo de simulação, determinístico)
  "seed": "…",                              // reprodutibilidade
  "location": { "region_id": "…" },         // ONDE
  "participants": ["species:Alpha"],        // QUEM
  "environmental_factors": ["resource:water#low"], // fatores ambientais (refs, não cópias)
  "genes": ["gene:therm_tol"],              // genes envolvidos (quando aplicável)
  "resources": ["water"],                   // recursos consumidos/afetados
  "cause_code": "RESOURCE_SCARCITY",        // causa ESTRUTURADA (enum), não prosa
  "cause_detail": { "duration_ticks": 5 },  // parâmetros da causa
  "consequences": ["event:uuid-downstream"],// O QUE resultou (liga a eventos filhos)
  "correlation_id": "uuid",                 // agrupa a cadeia causal (trace)
  "causation_id": "uuid|null",              // evento que causou este (trace)
  "granularity": "aggregate"                // aggregate | per_organism (§ ADR‑0002 Corr.2)
}
```

- **`cause_code` é enum, nunca texto pedagógico.** A prosa é do Tutor.
- `correlation_id`/`causation_id` habilitam **traces** (Pilar 4): reconstruir toda a cadeia que levou, por exemplo, uma espécie à extinção.
- Eventos são **determinísticos**: mesma seed → mesma sequência, mesma ordem.

---

## 5. Template do Engine de simulação

### 5.1 Estrutura por Engine
```
engines/<engine>/
  domain/        # modelos e regras puras (sem framework)
  service.py     # implementa a interface Engine (§5.2)
  events.py      # tipos de evento do domínio + cause_codes (enum)
  contracts.py   # fatia de world-state lida/escrita; parâmetros
  params.yaml    # parâmetros científicos VERSIONADOS (dados, não código)
  observability.py # métricas/tracing específicos (usa o contrato §6)
  tests/         # unit + integração + determinismo + sanidade científica
  README.md      # doc técnica + doc científica (fenômeno modelado, referências)
```

### 5.2 Interface comum (porta)
```python
class Engine(Protocol):
    engine_id: str
    reads: frozenset[SliceRef]
    writes: SliceRef

    def tick(self, ctx: TickContext) -> TickResult: ...
    # TickContext: snapshot read-only, rng semeado, tick/era, orçamento
    # TickResult: StateDelta (Canal A) + list[DomainEvent] (Canal B) + PerfSample
```
`rng` vem **semeado pelo Planet Engine** a partir da seed do planeta e do `engine_id`/tick (determinismo reprodutível, RF‑023). O Engine **nunca** usa fontes de aleatoriedade globais.

### 5.3 Protocolo de tick (Planet Engine)
Ordem determinística documentada, respeitando acoplamentos:
`physics → chemistry → atmosphere → climate → geology → hydrology → resource → evolution → ecology → event`
Fases por tick: (1) publica snapshot read‑only; (2) cada Engine computa delta+eventos lendo o snapshot; (3) Planet compõe deltas em ordem, aplicando invariantes; (4) fecha o tick; (5) ao fechar **era**, grava checkpoint append‑only + eventos (base de replay). Observabilidade consome os eventos **depois**, fora do loop.

---

## 6. Contrato de Observabilidade (obrigatório em todo Engine de simulação)

Implementa ADR‑ARCH‑0002. Faz parte do DoD.

- **Events:** todo comportamento relevante vira `DomainEvent` (envelope §4), determinístico, ao Event Store. Granularidade **agregada por padrão**; `per_organism` só sob flag/amostragem.
- **Logs:** `structlog` estruturado, correlacionado por `correlation_id`/`trace_id`. É **projeção** dos eventos para auditoria/diagnóstico — nunca inspeciona estado interno.
- **Metrics (Prometheus):** por Engine e por tick — tempo (médio/máx/mín), organismos/células processados, eventos emitidos, memória, taxa de eventos.
- **Traces (OpenTelemetry):** span por Engine/tick; a cadeia causal reconstruível via `causation_id`.
- **Orçamento por tick:** cada Engine declara um teto (tempo/nº de eventos/nº de agentes) em `params.yaml`. Excedeu → emite `DiagnosticEvent` (Canal B, visão técnica). **Nunca** altera a decisão da simulação.
- **Pureza:** a coleta é lateral e assíncrona; a simulação não lê logs/métricas/traces. Emissão determinística; consumo fora do loop.

**Fora do escopo agora (ADR‑ARCH‑0002, Correção 3):** profiling profundo always‑on (cache/CPU/quadrático) → `py-spy`/`scalene` on‑demand em dev; auto‑otimização por IA → adiada, com `DiagnosticEvent` já disponível para consumo futuro.

---

## 7. Contrato de Replay

- Entrada: `seed` + `checkpoint` da era + `event_log` (eventos append‑only).
- `replay(seed, checkpoint, events) -> WorldStateSnapshot` reconstrói **exatamente** o estado (bit‑a‑bit), incluindo biota emergente.
- Teste obrigatório por Engine: reexecutar a era reproduz a **mesma sequência de eventos** e o **mesmo world‑state**. Divergência = bug de determinismo (bloqueia merge).

---

## 8. Roadmap de implementação dos Engines

Dependências → ordem. Justificativa: seguir o fluxo físico (energia/matéria) minimiza retrabalho; consumidores por último, pois dependem de eventos ricos.

| Marco | Engines | Depende de | Critério de conclusão |
|---|---|---|---|
| **M0 — Moldura** | shared_kernel (world‑state, envelope, interface, replay, contrato de observabilidade) + Planet Engine (esqueleto) | núcleo determinístico atual | moldura testada; Planet orquestra 1 Engine trivial com replay |
| **M1 — Fatia vertical** | Geology → Atmosphere → Climate | M0 | feedback vulcanismo→CO₂→estufa→temperatura observável; determinístico; eventos + traces |
| **M2 — Física ambiental** | Hydrology, Chemistry, Resource | M1 | ciclos acoplados; invariantes de massa/energia |
| **M3 — Vida emergente** | Evolution (emergente, ADR‑0001), Ecology | M2 | especiação/extinção emergentes e reprodutíveis por seed; eventos causais legíveis |
| **M4 — Eventos extraordinários** | Event Engine + Diretor | M2/M3 | meteoro/seca/erupção cascateiam; telegrafados |
| **M5 — Infra plena** | Persistence, Observability (Event Store completo) | M0+ (contínuo) | replay/export/import; 4 pilares operacionais |
| **M6 — Consumidores** | Analytics → Education → AI Tutor (LLM+RAG, Inc 6) | M3/M5 | Tutor explica a partir do Event Store, sem recalcular ciência |

**Riscos técnicos e mitigação:** acoplamento instável (RSK‑01) → invariantes + fatia vertical; custo do ABM/eventos (RSK‑02) → orçamento por tick + granularidade agregada; explosão de eventos → agregado por padrão; determinismo sob emergência → tick ordenado + seed threadada + teste de replay por Engine; over‑engineering (RSK‑07) → in‑process até o volume exigir.

**Validação:** teste de determinismo/replay + sanidade científica por Engine; contrato de eventos versionado; *enforcement* de dependência em CI (`import-linter`/`dependency-cruiser`) barrando acesso a estado interno de outro Engine. **CI:** ruff + mypy `--strict` + pytest (unit/integração/contrato/determinismo/performance) como gate de PR, por Engine.

---

## 9. Definition of Done por Engine
- [ ] Domínio puro; interface `Engine` implementada; fatia lida/escrita declarada
- [ ] Parâmetros em `params.yaml` versionado (nunca hardcoded)
- [ ] RNG semeado pelo Planet; **replay bit‑a‑bit** testado (RF‑023)
- [ ] Eventos no envelope §4 com `cause_code` estruturado e campos de explicabilidade
- [ ] Contrato de Observabilidade §6 (events/logs/metrics/traces + orçamento por tick)
- [ ] Invariantes científicas testadas; doc técnica **e** científica no README
- [ ] Não importa outro Engine nem lê seu estado interno (enforce em CI)
- [ ] ruff + mypy strict + pytest verdes; cobertura ≥ 90% no código novo
