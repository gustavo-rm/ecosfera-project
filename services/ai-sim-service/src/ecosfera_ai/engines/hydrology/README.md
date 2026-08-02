# Hydrology Engine

Fecha o ciclo da água. Substitui o subsystem `ocean` e absorve o ciclo
gelo↔água que estava embutido no `chemistry` legado (ADR 0012).

## Documentação científica

### Quatro reservatórios, cinco fluxos

```
evaporação   : oceano  → vapor      (cresce com a temperatura)
precipitação : vapor   → água doce
escoamento   : doce    → oceano
degelo       : gelo    → oceano     (acima do limiar térmico)
congelamento : oceano  → gelo       (abaixo do limiar térmico)
```

Nenhum fluxo cria nem destrói água — cada um apenas **move massa** de um
reservatório para outro. É isso que torna a conservação uma invariante
verificável (Spec §3): `ocean + ice + vapour + freshwater` é constante dentro de
`conservation_tolerance`.

Cada fluxo é limitado pelo **reservatório de origem**, o que garante a
não-negatividade *antes* da invariante: não se evapora mais oceano do que existe,
nem se derrete mais gelo do que há. A invariante do Planet Engine fica sendo uma
rede de segurança, não o mecanismo.

### Evaporação e temperatura

A dependência real é de **Clausius–Clapeyron**, em que a pressão de vapor de
saturação cresce exponencialmente com a temperatura. Na faixa habitável
(~0–40 °C) a curva é bem aproximada por uma reta, e é essa linearização que se
usa aqui — explicitamente, para que o aluno veja "mais calor, mais evaporação"
sem que o modelo finja uma precisão que não tem.

### Criosfera e o acoplamento com o clima

Degelo e congelamento são proporcionais ao excesso térmico sobre o limiar e ao
estoque disponível. O gelo realimenta o clima pelo **albedo** — mas essa seta é
do Climate Engine, que lê o gelo daqui com um tick de atraso.

A `ice_cover` saiu da `ClimateSlice` no M2 justamente por isso: a criosfera é um
reservatório de **água**, não uma variável climática. Quem a governa é a
hidrologia; o clima apenas a enxerga.

### Circulação termohalina

```
circulação_alvo = base + k_sal·(S − S_ref) − k_temp·(T − T_ref) + marés
```

Água fria e salgada afunda e fortalece a circulação; o aquecimento a enfraquece.
As marés das luas somam mistura mecânica constante. A salinidade é sal conservado
diluído na água líquida — dilui quando o oceano cresce, concentra quando encolhe.

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `hydrology` |
| escreve | `HydrologySlice` (`ocean`, `ice`, `vapour`, `freshwater`, `salinity`, `ocean_circulation`, `evaporation`, `precipitation`) |
| lê (mesmo tick) | `ClimateSlice.temperature` |
| lê (defasado) | — |
| eventos | `IceSheetChanged`, `WaterBalanceShift` |
| parâmetros | `params.yaml` (versionado) |

**Como o acoplamento bidirecional se resolve sem ciclo.** A hidrologia lê a
temperatura do Climate no MESMO tick (ele roda antes): evaporação e degelo são
função direta do calor recém-resolvido. O Climate, por sua vez, lê o gelo e a
circulação daqui com UM tick de atraso, declarado em `lagged_reads`. A defasagem
é a técnica que quebra o ciclo água↔clima sem desfazer o acoplamento — e
declará-la é o que faz o `validate_graph` aceitar a ordem em vez de rejeitá-la.

**Invariantes:** água total conservada dentro de `conservation_tolerance`;
reservatórios não-negativos.

`evaporation` e `precipitation` são **diagnóstico do tick**, não reservatórios:
carregam a taxa daquele passo, não um acumulado.
