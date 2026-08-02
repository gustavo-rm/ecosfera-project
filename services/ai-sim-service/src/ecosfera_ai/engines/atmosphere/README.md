# Atmosphere Engine

Elo do meio da fatia vertical do M1. Dono **único** do ciclo do carbono e do
forçamento radiativo (ADR 0010).

## Documentação científica

### Estoque de CO₂
Um reservatório com uma fonte e dois sumidouros:

```
dC/dt = desgaseificação − intemperismo(C) − absorção biótica(biomassa)
```

A fonte chega pronta da geologia pelo Canal A. O intemperismo é proporcional ao
próprio estoque — é o **termostato de longo prazo** do ciclo carbonato-silicato
(Walker, Hays & Kasting, 1981): mais CO₂ → mais intemperismo → remoção maior. A
absorção biótica entra quando houver biomassa (M3); até lá o termo é nulo.

### Forçamento radiativo — por que logarítmico
```
ΔF = α · ln(C/C₀),   α = 5,35 W/m²
```

> Myhre, G., Highwood, E. J., Shine, K. P., & Stordal, F. (1998). *New estimates
> of radiative forcing due to well mixed greenhouse gases.* Geophysical Research
> Letters 25(14), 2715–2718.

As bandas de absorção do CO₂ **saturam**: cada duplicação do estoque acrescenta
aproximadamente o mesmo forçamento (~3,7 W/m²), não o dobro. O subsystem
`climate` legado usava `coeficiente × CO₂`, uma relação linear que não satura e
ensinaria ao aluno uma resposta climática que a física não tem.

| CO₂ (ppm) | linear (antes) | log (agora) |
| --- | --- | --- |
| 280 (referência) | 2,80 | 0,00 |
| 560 (2×) | 5,60 | 3,71 |
| 1120 (4×) | 11,20 | 7,42 |

O piso numérico no logaritmo evita `ln(0) = −∞`: um planeta que perdesse todo o
carbono ficaria "muito frio", não com forçamento infinito.

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `atmosphere` |
| escreve | `AtmosphereSlice` (`co2`, `greenhouse_forcing`, `pressure`) |
| lê (mesmo tick) | `GeologySlice.co2_flux` |
| lê (defasado) | `LegacySlice.biomass` |
| eventos | `GreenhouseForcingChanged` — `CO2_ACCUMULATION` / `CO2_DRAWDOWN` |
| parâmetros | `params.yaml` (versionado) |

**Invariantes:** `co2 ≥ 0` (recortado pelo Planet Engine, com registro em
`DiagnosticEvent`); conservação do carbono que entra — sem sumidouros, todo fluxo
recebido vira estoque, verificado em teste.

O evento é emitido na travessia de **faixa** de forçamento, não a cada tick: é a
granularidade agregada por padrão do ADR-ARCH-0002 (Correção 2).
