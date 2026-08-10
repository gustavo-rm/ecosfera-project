# Fase 0 — Correções conceituais (pré-requisito do M6)

Registro do que a Fase 0 do `docs/decisions/PLANO_EVOLUCAO_ECOSFERA.md` (raiz do
monorepo) entregou, do que deixou de fora **de propósito**, e do que ficou aberto.

**O princípio da fase:** o Tutor narra a ciência da simulação. Se a ciência de
base estiver errada, o Tutor ensina o erro com autoridade — e com mais eficácia
do que ensinaria o acerto. Esta fase corrige os erros de base **antes** de o Tutor
existir.

**A regra de fronteira:** uma mudança é pré-M6 se, sem ela, o Tutor narraria algo
**cientificamente errado** — não apenas "menos rico". Ancestralidade errada é
pré-M6; teias alimentares ausentes é pós-M6.

---

## O estado encontrado (pre-flight)

| Verificação | Achado |
| --- | --- |
| M0–M5 | mesclados; a base é o merge do M5 (Event Store + persistência) |
| M6.0 / `FactualContext` | **não existe** — o M6 não foi iniciado. O read-side que o M6.0 vai estender é `ExplainFromEventsUseCase` + `causal_trace` |
| Modelo de especiação | **dois**, e os dois falhavam o BIO-001 (ver abaixo) |

### Os dois modelos de especiação encontrados

**Caminho A — Evolution Engine (vivo).** `SpeciationOccurred` significava "o
genoma médio da comunidade divergiu além do limiar" (ADR 0016), com
`participants: ["species:community"]` — **um sujeito só**. Não afirmava "A gerou
B", mas também não oferecia outra leitura: um evento de divisão com um único
sujeito só pode ser lido como "aquele sujeito produziu a novidade".

**Caminho B — biologia por era (dormente desde o M3, ADR 0017).**
`SpeciesRecord(ancestor_id=...)` escolhe o ancestral **entre as espécies vivas** —
é o "A→B" literal que o BIO-001 nomeia. Continua dormente
(`biology_enabled=False`) e sai no tempo 3 do ADR 0017.

Dois achados colaterais, registrados porque são achados e não escolhas:

1. **A especiação não tinha causa, tinha régua.** `GENETIC_DIVERGENCE` era o
   critério ("os genomas ficaram distantes"), não o motivo da divisão.
2. **A especiação era inarrável.** Virava observação de `species_richness`, e
   **nenhuma regra causal partia dessa variável** — a cadeia morria ali.

---

## O que foi entregue

| Requisito | Entrega |
| --- | --- |
| **BIO-001** · ancestral comum | `SpeciationOccurred` nomeia `ancestor:` + dois `lineage:`; genoma das três no `cause_detail`; identidades por `uuid5`. Caminho B **marcado** como superado, não reescrito. ADR 0023 |
| **BIO-002** (parte pré-M6) · causa no evento | 4 causas novas (`DIVERGENT_NICHE`, `ENVIRONMENTAL_PRESSURE`, `REPRODUCTIVE_ISOLATION`, `GEOGRAPHIC_BARRIER`); `GENETIC_DIVERGENCE` superada e mantida só para trilhas antigas. ADR 0023 |
| **BIO-005** · anti-teleologia | regras causais v5 com a ordem correta (variação aleatória → ambiente decide); `test_no_teleological_language` varre templates, código e ADRs |
| **PED-003** · adaptação × especiação | regra `R-TRAIT-ADAPTATION` (frequência de traços, uma linhagem só) contra `R-SPECIATION-COMMON-ANCESTOR`; distinção escrita no vocabulário de evento e no domínio |
| **BIO-006** · catastrófica × ecológica | **preservação + teste**, nada reimplementado. `test_catastrophic_extinction_preserved` guarda contra os dois modos de a Fase 0 tê-la quebrado em silêncio |
| **BIO-003** · decisão de coortes | **comunidade + espécies**; camada de espécies OPCIONAL e **pós-M6**. ADR 0024, que fecha a P-01 |

Sete arquivos de teste novos, 247 casos. Determinismo por semente e replay
bit-a-bit conferidos **envelope a envelope** (e não só por `event_id`, que
continuaria batendo mesmo com um `cause_detail` sorteado).

---

## O que ficou de fora, de propósito

Nada de: camada de espécies com identidade, teias alimentares, relações
ecológicas novas, ciclo do carbono, oxigênio/Grande Oxidação, impactos
antrópicos, Tutor/LLM. Tudo isso é pós-M6 no Plano.

O códex do caminho B **não foi reescrito**. Reescrevê-lo seria implementar a
camada de espécies, que o ADR 0024 colocou depois do M6. Ele foi **marcado**, em
`codex.py` e no ponto exato da escolha do ancestral.

---

## Aberto — dívida declarada

**A especiação é praticamente inalcançável com o limiar de produção.** Medido:
com `speciation_threshold: 0,12`, a distância de um passo de mutação vale ~0,02 e
chegar ao limiar num tick exigiria ~6 σ. O evento existe, está corretamente
descrito e quase nunca acontece.

Não foi consertado aqui, e a razão é a mesma que sustenta o escopo da fase:
calibrar o limiar trataria o sintoma e mudaria a dinâmica no marco que corrige o
envelope. A correção certa é a **mecânica gradual do BIO-002** — divergência
acumulada ao longo de gerações em vez de exigida de um salto —, que é **Fase 2 do
Plano, pós-M6**. Os testes declaram o cenário (limiar baixado por parâmetro),
mesma técnica do `build_volcanic_planet`.

**`GEOGRAPHIC_BARRIER` sem emissor** até existirem regiões. Declarada porque o
vocabulário do Tutor a exige, registrada em `CAUSES_WITHOUT_EMITTER` com a razão
ao lado, e coberta por um teste que exige que todo código do enum ou tenha
emissor ou esteja lá — o buraco é ruidoso, e não silencioso como foi o do
`solar_flux` no M2.

**`TUT-002` (contraste entre espécies) fica fora do M6**, por consequência direta
do ADR 0024: exige espécies, e a camada é pós-M6. O Tutor do M6 fala da
**comunidade**.
