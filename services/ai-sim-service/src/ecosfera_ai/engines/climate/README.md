# Climate Engine

Último elo da fatia vertical do M1. Resolve a temperatura a partir do forçamento
radiativo. **Não sabe o que é CO₂** — e é por não saber que a fronteira se
sustenta.

## Documentação científica

### Balanço de energia de caixa única
O modelo mais simples que ainda é fisicamente coerente:

```
absorvida  = irradiância · (1 − albedo(gelo))
equilíbrio = offset + k_energia · absorvida + λ · ΔF
dT/dt      = inércia · (equilíbrio − T) + tempo + oceano
```

> Budyko, M. I. (1969). *The effect of solar radiation variations on the climate
> of the Earth.* Tellus 21(5), 611–619.
> Sellers, W. D. (1969). *A global climatic model based on the energy balance of
> the earth-atmosphere system.* Journal of Applied Meteorology 8(3), 392–400.

`λ` é a **sensibilidade climática** em °C por W/m². O valor 0,8 equivale a ~3 °C
por duplicação de CO₂ (3,7 W/m²), a faixa central do IPCC AR6.

### Retroalimentação do gelo (positiva)
O albedo cresce com a cobertura de gelo: gelo reflete, o planeta esfria, forma-se
mais gelo. É um dos raciocínios que o aluno precisa reconstruir, e por isso está
explícito no domínio em vez de embutido num coeficiente.

### Sequestro de calor oceânico (negativa)
A circulação termohalina leva calor da superfície para o fundo, amortecendo a
resposta. Este termo **veio do subsystem `ocean`** no M1: mudou de dono, não de
física. `temperature` precisa de um escritor único, e o oceano legado continua
dono de salinidade e circulação, que este Engine apenas lê.

### Calibração do offset
Era `−5,0` quando o termo de estufa linear somava +2,8 °C no CO₂ de referência.
Com o forçamento logarítmico valendo **zero** na referência, o offset absorve
esses +2,8 (passa a `−2,2`). O planeta parte do mesmo equilíbrio de antes
(~17,6 °C); só a **resposta** a mudanças de CO₂ muda de forma.

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `climate` |
| escreve | `ClimateSlice` (`temperature`, `energy`) |
| lê (mesmo tick) | `AtmosphereSlice.greenhouse_forcing` |
| lê (defasado) | `LegacySlice` (`ice_cover`, `solar_flux`, `ocean_circulation`) |
| eventos | `TemperatureShift`, `ClimateThresholdCrossed` — `RADIATIVE_FORCING` |
| parâmetros | `params.yaml` (versionado) |

`ice_cover` continua no ciclo água/gelo do `chemistry` legado e migra no M2 junto
com a hidrologia — por isso o campo existe na `ClimateSlice` mas ainda não é
escrito aqui.

Dois gatilhos de evento, deliberadamente distintos: variação grande num único
tick (`TemperatureShift`, interessa a quem investiga um transiente) e travessia
de patamar climático (`ClimateThresholdCrossed`, interessa ao aluno).
