# ADR‑ARCH‑0002 — Observabilidade por Design (Observability by Design)

**Série:** projeto/arquitetura (`docs/adr/`).
**Status:** Aceito. **Obrigatório** para o Evolution Engine desde o início; padrão para todos os Engines de simulação.
**Decisões relacionadas:** ADR‑ARCH‑0001 (Engines). Especificação: `ECOSFERA_Engine_Framework_Spec.md` §6 (Contrato de Observabilidade).

## Contexto

O ECOSFERA é uma plataforma **educacional**: o motor não precisa apenas funcionar, precisa ser **explicável, auditável e depurável**. Nenhum mecanismo relevante pode ser "caixa‑preta". A IA Tutora **não pode inferir o estado inspecionando objetos em memória** — precisa consumir uma **trilha de eventos**. Quatro públicos consomem visões diferentes da mesma verdade: IA Tutora, professores, desenvolvedores e ferramentas de monitoramento.

A proposta original estruturava três "logs" (Científico, Diagnóstico‑IA, Educacional). Adota‑se a reformulação — mais moderna e correta — de **quatro pilares de observabilidade** sobre uma **única fonte de verdade (Event Store)**, com três correções obrigatórias para adequar à realidade do projeto (custo, pureza de domínio, determinismo).

## Decisão

### Princípio Fundamental (invariante, literal da proposta — reforçado)
> A simulação **nunca** depende dos logs. Os logs dependem da simulação. Nenhuma decisão biológica/científica é tomada consultando logs, métricas ou traces.

Reforço operacional: a **emissão** de eventos é determinística (mesma seed → mesmos eventos, na mesma ordem); a **consumação** (logs, métricas, traces, projeções) é **assíncrona e fora do loop determinístico**, portanto **não pode afetar o replay**. Medir tempo de tick é permitido como métrica lateral, mas **jamais** realimenta decisões da simulação (ex.: não se pula um subsistema por estar lento — isso quebraria o determinismo).

### Quatro pilares sobre uma fonte de verdade
O **Event Store** (append‑only, determinístico, replayável) é a fonte única de verdade. Dela derivam:

1. **Events** — os domain events em si (a fonte).
2. **Logs** — registros estruturados (`structlog`) para auditoria/diagnóstico, como **projeções** dos eventos.
3. **Metrics** — Prometheus: tempo por Engine/tick (médio/máx/mín), organismos processados, eventos emitidos, memória, taxa de eventos.
4. **Traces** — OpenTelemetry: encadeia a **cadeia causal completa** (ex.: mudança ambiental → declínio populacional → extinção; ou mutação → propagação na população). É o "como chegamos aqui" que o Tutor precisa.

### Três públicos = três projeções (não três emissores)
- **Visão Científica** — projeção filtrada/enriquecida dos eventos (pesquisa, replay, professor avançado).
- **Visão Técnica/Diagnóstico** — métricas + traces + `DiagnosticEvent`s (desenvolvedores; e, no futuro, consumo por IA de otimização).
- **Visão Educacional** — **renderizada pelos consumidores** (Education/AI Tutor Engine) a partir dos eventos, **não emitida pelo Engine científico** (ver Correção 1).

### Correção 1 — A Visão Educacional é projeção do consumidor, não saída do Engine
O Evolution Engine emite eventos **neutros e estruturados** com metadados causais suficientes (ex.: `PopulationDeclined{species, cause_code: RESOURCE_SCARCITY, resource: water, duration_ticks: 5, participants, genes, consequences}`). A frase educacional ("a espécie Alpha perdeu população porque houve escassez de água por cinco ciclos") é **renderizada pelo Education/AI Tutor Engine**. O Engine fornece o **esqueleto causal como dado**; o Tutor fornece a prosa e a pedagogia. Emitir texto educacional do Engine violaria a diretriz "nenhum Engine contém conhecimento pedagógico" (ADR‑ARCH‑0001). Logo, **explicabilidade é requisito de schema do evento** — todo evento significativo responde: o quê, quando, onde, quais organismos, quais fatores ambientais, quais genes, quais recursos, quais consequências (Spec §4).

### Correção 2 — Granularidade em camadas (evitar explosão de eventos)
Eventos por‑organismo por tick (nascimento/morte de cada indivíduo) explodem armazenamento e replay e viram o próprio gargalo. Padrão:
- **Agregado por padrão:** deltas por espécie/coorte (ex.: `+N nascimentos, −M mortes` com códigos de causa).
- **Por‑organismo sob demanda:** flag de debug / amostragem, ativada apenas para uma investigação específica.

### Correção 3 — Diagnóstico profundo: métricas+traces agora; profiling on‑demand; auto‑otimização adiada
Cache hit/miss, detecção de operações quadráticas, alocações e "loops infinitos" *always‑on* são caros em Python e **perturbam o próprio tempo de tick** que se quer medir. Adaptação:
- **Agora:** Prometheus + OpenTelemetry; **detecção de gargalo = orçamento por tick** (excedeu o teto configurável → emite `DiagnosticEvent`). Entrega ~80% do valor de depuração a ~5% do custo.
- **On‑demand (dev):** profiling profundo com `py-spy`/`scalene`, fora do caminho de produção.
- **Adiado (trilha de pesquisa):** detecção automática de anomalia/degradação progressiva e **auto‑otimização/sugestões por IA**. O *stream* de `DiagnosticEvent` já nasce aberto para consumo futuro por IA, sem implementá‑lo no MVP/Centelha.

## Adotar / Adaptar / Adiar (síntese)

| Item da proposta | Decisão |
|---|---|
| Event Store como fonte de verdade; replay por seed | **Adotar** |
| Eventos estruturados com metadados causais (explainability) | **Adotar** (requisito de schema) |
| Quatro pilares (Events/Logs/Metrics/Traces) | **Adotar** |
| Três públicos consumindo visões distintas | **Adotar** (como projeções) |
| Métricas por Engine (tempo, organismos, eventos, memória) | **Adotar** (Prometheus) |
| Traces da cadeia causal | **Adotar** (OpenTelemetry) |
| Orçamento por tick → evento de diagnóstico | **Adotar** |
| Log Educacional gerado pelo Engine | **Adaptar** → projeção do Education/Tutor |
| Eventos por‑organismo sempre | **Adaptar** → agregado por padrão, drill‑down sob demanda |
| AI Diagnostic Log (cache/CPU/quadrático always‑on) | **Adaptar** → métricas+traces; profiler on‑demand |
| Detecção automática de gargalos além do orçamento | **Adiar** |
| Auto‑otimização e sugestões por IA | **Adiar** (dados prontos; implementação futura) |

## Consequências
- **Positivas:** Tutor explica a partir de uma trilha limpa e determinística; depuração e comparação entre versões por replay; separação de responsabilidades preservada; base pronta para pesquisa futura de auto‑otimização.
- **Custos:** todo Engine de simulação deve implementar o Contrato de Observabilidade (Spec §6) — parte do Definition of Done, não opcional; o event store precisa de política de granularidade e retenção (alinhada à LGPD para dados de menores).

## Alternativas consideradas
- **Logging *bolt‑on* (adicionar depois).** Rejeitado: incompatível com "plataforma explicável"; o Tutor ficaria sem trilha.
- **Profiling profundo always‑on.** Rejeitado agora: custo e perturbação do determinismo; movido para on‑demand.
