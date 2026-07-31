# Geology Engine

Primeiro elo da fatia vertical do M1. Modela tectônica, vulcanismo e erosão, e é
a **fonte de carbono** do planeta.

## Documentação científica

### Vulcanismo como processo pulsante
O vulcanismo relaxa exponencialmente para uma linha de base e recebe pulsos
tectônicos amostrados de uma normal semeada. O pulso entra em **módulo**: não
existe vulcanismo negativo — um pulso é sempre fonte, nunca sumidouro.

### Relevo como estoque disputado
Dois fluxos opostos: soerguimento (∝ vulcanismo) e erosão (∝ água × relevo). O
relevo é confinado a [0,1] pela invariante do Planet Engine.

### Desgaseificação — por que a fonte de CO₂ mora aqui
A desgaseificação vulcânica é a fonte primária de CO₂ atmosférico em escala
geológica. Sem ela o intemperismo de silicatos zeraria o carbono atmosférico em
poucos milhões de anos. É o braço "fonte" do **ciclo carbonato-silicato**:

> Walker, J. C. G., Hays, P. B., & Kasting, J. F. (1981). *A negative feedback
> mechanism for the long-term stabilization of Earth's surface temperature.*
> Journal of Geophysical Research 86(C10), 9776–9782.

O fluxo emitido é publicado em `GeologySlice.co2_flux`. Este Engine **nunca**
escreve na `AtmosphereSlice` — a seta vulcanismo→CO₂ cruza a fronteira só pelo
Canal A (Spec §2).

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `geology` |
| escreve | `GeologySlice` (`volcanism`, `relief`, `co2_flux`) |
| lê (defasado) | `LegacySlice.water`, para a erosão |
| eventos | `VolcanicEruption` — `cause_code: TECTONIC_PULSE` |
| parâmetros | `params.yaml` (versionado) |

A leitura de `water` é **defasada e declarada**: o adaptador legado roda depois
na ordem do tick, então o valor visto é o do tick anterior. Sem a declaração em
`lagged_reads`, o Planet Engine recusaria o registro no boot.

Roda antes de todos porque é a origem física da cadeia. `eruption_threshold`
mantém o evento como ocorrência **notável**: se toda a série virasse evento, o
Event Store deixaria de ser trilha e viraria log de depuração.
