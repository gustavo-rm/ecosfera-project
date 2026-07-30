# ADR 0009 — Contrato de Observabilidade da moldura de Engines

## Status
Aceito. Implementa o **ADR-ARCH-0002** (Observabilidade por Design) e a Spec §6.
Complementa o ADR 0008. Referência: Dossiê v3 §10.5.

## Contexto

O ECOSFERA é plataforma educacional: o motor precisa ser explicável, auditável e
depurável. A IA Tutora **não pode inferir o estado inspecionando objetos em
memória** — ela consome uma trilha de eventos. Isso torna a observabilidade um
requisito de arquitetura, não um adorno adicionado depois.

O risco simétrico é acoplá-la de volta ao cálculo. Basta um `if tempo_do_tick >
teto: pular_engine` para o resultado da simulação passar a depender da carga da
máquina — e o replay bit-a-bit, já implementado, morre.

## Decisão

### `ObservabilitySink`: uma porta, quatro pilares

```python
class ObservabilitySink(Protocol):
    def record_metrics(self, sample: PerfSample) -> None: ...
    def emit(self, event: DomainEvent) -> None: ...
    def log(self, message: str, /, **fields: object) -> None: ...
```

| Implementação | Pilar |
| --- | --- |
| `InMemoryEventStore` | 1. Events — fonte de verdade, append-only |
| `StructlogSink` | 2. Logs — projeção dos eventos, correlacionada |
| `PrometheusMetricsSink` | 3. Metrics — tempo, eventos e entidades por Engine/tick |
| `span()` atrás de flag | 4. Traces — gancho OpenTelemetry, no-op por padrão |
| `NullSink` | ausência EXPLÍCITA, em vez de `if sink is not None` |
| `CompositeSink` | fan-out na ordem declarada |

### Pureza é regra de chamada, verificada em teste

O sink é acionado **pelo Planet Engine, depois de compor e fechar o tick** —
nunca por um Engine durante o cálculo. `tests/unit/test_observability_purity.py`
verifica quatro afirmações:

1. toda observação ocorre depois de todo cálculo (ordem de chamadas);
2. o snapshot é idêntico com sink ligado e desligado;
3. dois relógios diferentes produzem o mesmo snapshot (tempo é medida lateral);
4. `publish=False` no replay não reemite — reconstruir é reproduzir, não
   reocorrer, e a trilha do Event Store não pode duplicar.

### Orçamento por tick → `DiagnosticEvent`, jamais decisão

Cada Engine tem um teto declarado em `configs/simulation_params.yaml` (dado
versionado): tempo, número de eventos, número de entidades. Estourar emite um
`DiagnosticEvent` no Canal B e **não altera um bit** do resultado. É a
Correção 3 do ADR-ARCH-0002: ~80% do valor de depuração a ~5% do custo, sem
profiling always-on perturbando o próprio tempo que se quer medir.

Invariante recortada (estoque negativo, fração fora de [0,1]) segue o mesmo
caminho: o recorte é parte determinística da composição, o **registro** é que
vira evento.

### Um envelope só, três projeções

`DiagnosticEvent` não é um segundo formato — é um `DomainEvent` com
`event_type="DiagnosticRaised"`. A visão científica
(`store.scientific_view()`) e a técnica (`store.technical_view()`) são
**filtros** sobre a mesma trilha. A visão educacional não existe aqui: ela é
renderizada pelo Education/AI Tutor a partir dos eventos (Correção 1). O Engine
entrega o esqueleto causal como dado; a prosa é do Tutor.

Coerente com isso, a métrica de orçamento é derivada do **evento**, não de um
canal paralelo: se o `DiagnosticEvent` não foi emitido, não existe teto estourado
a contar.

### Granularidade agregada por padrão

`Granularity.AGGREGATE` é o default do envelope; `PER_ORGANISM` existe para
investigação pontual (Correção 2). Eventos por organismo por tick explodiriam o
Event Store e virariam o próprio gargalo.

### OpenTelemetry adiado, gancho presente

`span()` é no-op enquanto `ECOSFERA_TRACING_ENABLED` estiver desligado. Trazer o
SDK agora custaria dependência pesada para spans que ninguém coleta. O que
precisa existir desde já é o **ponto de engate**, para que ligar tracing no M5
não exija tocar no Planet Engine. Enquanto isso a cadeia causal já é
reconstruível por `correlation_id`/`causation_id` no Event Store — que é
exatamente o "como chegamos aqui" que o Tutor precisa.

## Consequências

+ O Tutor terá uma trilha limpa, determinística e replayável, sem inspecionar
  memória de Engine.
+ Trocar o Event Store em memória por um adaptador Postgres (M5) não toca em
  nenhum Engine: eles só conhecem a porta.
+ Depuração por replay: mesma semente, mesmos eventos, mesma ordem.
− Todo Engine de simulação passa a dever o contrato §6 — é Definition of Done,
  não opcional.
− O Event Store em memória é do processo: reiniciar perde a trilha. Adequado ao
  M0; o adaptador durável é o M5.
− O `DiagnosticEvent` compartilha o Event Store com os eventos científicos, então
  a política de retenção precisará distinguir os dois (e considerar a LGPD para
  dados de menores) quando a persistência real chegar.
