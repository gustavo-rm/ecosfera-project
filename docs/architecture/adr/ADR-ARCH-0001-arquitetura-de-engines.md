# ADR‑ARCH‑0001 — Arquitetura de Engines do ECOSFERA

**Série:** projeto/arquitetura (raiz do monorepo — `docs/adr/`), distinta da série interna do `ai-sim-service` (0001 hexagonal, 0002 rules‑first, 0003+ incrementos).
**Status:** Aceito.
**Decisão relacionada:** ADR‑ARCH‑0002 (Observabilidade por Design). Especificação de implementação: `ECOSFERA_Engine_Framework_Spec.md`.

> **Nota sobre a dívida de numeração de ADR.** O projeto tinha duas séries iniciando em 0001 (projeto × serviço) sem escopo definido. Este ADR **resolve a dívida por definição de escopo**, não por fusão: a série **projeto/arquitetura** cobre decisões transversais entre Engines/serviços (prefixo `ADR‑ARCH‑`); a série **serviço** cobre decisões internas a um serviço. Fundir séries de escopos diferentes seria pior que mantê‑las separadas com regra clara.

## Contexto

O ECOSFERA é uma **plataforma de simulação científica** que também é educacional — não um jogo convencional. Propôs‑se organizá‑lo em ~15 "Engines", cada um representando um domínio científico independente, desacoplado, orientado a eventos, determinístico por seed e evoluível isoladamente, com a diretriz estratégica de que **nenhum Engine contém conhecimento pedagógico ou de outro domínio** (Climate só simula clima; Education/Tutor interpretam eventos, não recalculam ciência).

A direção é acertada, mas quatro pontos precisam de decisão explícita para não recair no risco RSK‑07 do Dossiê (microsserviços/over‑engineering prematuros) nem quebrar a simulação física acoplada e o replay determinístico já implementados (timeline/checkpoints do núcleo determinístico).

## Decisão

Adota‑se a **arquitetura de Engines como modelo lógico de domínio dentro de um serviço hexagonal (`ai-sim-service`)**, com as quatro emendas abaixo como parte integrante da decisão.

### Emenda 1 — Engines são módulos in‑process, não serviços
Cada Engine é um **módulo dentro de um único deployable** (`ai-sim-service`), comunicando por um event bus **em memória**, com as costuras (contratos + eventos) prontas para extrair um Engine para serviço próprio *se e quando* volume/escala exigirem. Preserva‑se todo o benefício (isolamento, testabilidade, evolução independente) sem 15 pipelines/deployables — coerente com o monólito modular do Dossiê §1.2 e com a equipe enxuta.

### Emenda 2 — Dois canais de comunicação
Comunicação por evento **não** é universal. Há dois canais (detalhados na Spec §2):

| Canal | Natureza | Para quê | Consumidores |
|---|---|---|---|
| **World‑State + deltas por tick** | ordenado, síncrono, determinístico | acoplamento físico contínuo (vulcanismo→CO₂→estufa→temperatura→gelo→albedo) | Engines de simulação |
| **Domain Events** | discreto, append‑only, no event store | ocorrências notáveis (erupção, especiação, extinção, início de seca) | Consumidores read‑side (Tutor, Education, Analytics, Observability) |

Nenhum Engine lê o **estado interno** de outro; todos leem um snapshot **read‑only versionado** do world‑state e devolvem **deltas** da própria fatia, ou emitem eventos discretos. A regra "não acessar estado interno de outro Engine" é honrada pelos dois canais.

### Emenda 3 — Três camadas, não um template único para os 15
Forçar Persistence/Observability/Analytics/Education/Tutor no mesmo template de "tick/replay determinístico" dos Engines científicos é erro de categoria. Classificam‑se em:

| Camada | Engines | Padrão |
|---|---|---|
| **Simulação** (loop determinístico por tick) | Planet (orquestrador), Geology, Atmosphere, Climate, Hydrology, Chemistry, Evolution, Ecology, Resource, Event | Template completo de Engine (Spec §5) |
| **Plataforma/Infra** | Persistence, Observability (Event Store) | *Ports & Adapters* — não têm "tick" nem replay próprio |
| **Consumidores** (read‑side) | Analytics, Education, AI Tutor | Assinam o event store; **fora** do loop determinístico; nunca recalculam ciência |

### Emenda 4 — Projetar a moldura comum + fatia vertical; não congelar 15 contratos
Especifica‑se **agora e em profundidade** o que é comum a todo Engine (interface, envelope de evento, protocolo de tick, contrato de world‑state, contrato de observabilidade, replay — a Spec) e valida‑se com uma **fatia vertical de 3 Engines** (Geology → Atmosphere → Climate, que já exercita acoplamento e feedback). O contrato específico de cada Engine firma‑se ao construí‑lo, evitando *Big Design Up Front* especulativo — coerente com o Scrumban/walking‑skeleton do projeto.

### Decisão adicional — Evolução emergente supersede o AG de fitness global
O RF‑031 do Dossiê ("Motor evolutivo (AG)") baseava‑se em algoritmo genético com **função de fitness global**. Fica **superado**: a evolução deve **emergir da interação local organismo↔ambiente** (sobrevivência/reprodução individuais, no espírito de vida artificial — Avida/Tierra), sem otimização teleológica global.

- **Ciência:** fitness global é teleológico e reforça a concepção equivocada de que a evolução "mira" um ótimo — exatamente o que o jogo não pode ensinar. Emergência é mais fiel à seleção natural.
- **Educação:** produz eventos causais legíveis ("espécie X extinta porque a tolerância térmica foi excedida") — insumo direto do AI Tutor.
- **Computação:** exige o **tick ordenado e determinístico por seed** (Emenda 2) para manter o replay bit‑a‑bit; sem isso, o timeline já implementado deixa de funcionar.

## Alternativas consideradas

- **Microsserviços (um deployable por Engine).** Rejeitado: imposto operacional inviável para a equipe; RSK‑07. As costuras da Emenda 1 permitem extrair depois sem reescrita.
- **"Tudo é evento" (inclusive o acoplamento físico por tick).** Rejeitado: quebra a convergência dos feedbacks contínuos, adiciona latência (RSK‑02) e torna o determinismo/replay muito mais difícil com entrega assíncrona entre 15 Engines. Resolvido pela Emenda 2 (dois canais).
- **Manter AG de fitness global (Dossiê original).** Rejeitado pelas três razões acima; superação registrada em revision notebook.

## Consequências

- **Positivas:** domínios científicos isolados e testáveis; Tutor auditável (consome eventos, não memória); determinismo/replay preservados; caminho de extração para serviço mantido aberto; alinhamento com a diretriz de separação de conhecimento.
- **Negativas/custos:** disciplina de contratos e de fronteira exige *enforcement* em CI (regras de dependência); a moldura comum precisa estar madura antes de escalar em largura. Mitigado pela Emenda 4 (fatia vertical primeiro).
- **Reenquadramento do que já existe:** `TickOrchestrator` **é** o Planet Engine; `subsystems/{climate,chemistry,geology,ocean}.py` são as sementes dos respectivos Engines; timeline/checkpoints são a base de Persistence + Event Store; o feedback causal por regras é o embrião do AI Tutor consumindo eventos. Nada é descartado.
