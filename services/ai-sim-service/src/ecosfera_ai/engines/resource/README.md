# Resource Engine

Último elo determinístico da cadeia. Responde a uma pergunta só: **quanta vida
este planeta comporta?** A resposta é um orçamento — a `carrying_capacity` — e a
biologia gasta dentro dele sem nunca escrever de volta (ADR 0006, ADR 0013).

## Documentação científica

### Lei do mínimo

O crescimento não é limitado pela soma dos nutrientes, e sim pelo **mais escasso
em relação à sua demanda**. Um oceano farto de nitrogênio e sem fósforo não
sustenta mais vida do que o fósforo permite:

```
limitante = min(N/demanda_N, P/demanda_P, S/demanda_S)
```

> Liebig, J. von (1840). *Die organische Chemie in ihrer Anwendung auf
> Agricultur und Physiologie.*

### Habitabilidade multiplicativa

```
h = aptidão_térmica × aptidão_hídrica × aptidão_nutriente × aptidão_energética
carrying_capacity = capacidade_máxima × h
```

Os quatro fatores **multiplicam-se**, não se somam. A diferença é física: um
fator nulo zera a habitabilidade, porque não existe vida sem água por mais
perfeita que seja a temperatura. Uma soma permitiria compensar a ausência de um
recurso com o excesso de outro — exatamente o que a lei do mínimo nega.

A aptidão térmica é uma gaussiana em torno do ótimo; as demais saturam no
requisito (mais do que o necessário não ajuda).

### O que veio do `life` e o que é novo

| Fator | Origem |
| --- | --- |
| aptidão térmica (gaussiana, ótimo 22 °C, tolerância 15 °C) | `life` determinístico, **valores inalterados** |
| aptidão hídrica (saturação em `water_requirement = 0,2`) | `life` determinístico, **valores inalterados** |
| aptidão de nutriente (lei do mínimo sobre N/P/S) | **novo no M2** |
| aptidão energética (fração útil da irradiância) | **novo no M2** |
| `max_carrying_capacity = 100` | `life` determinístico, **valor inalterado** |

Quem passou a derivar a capacidade foi este Engine — o `life` apenas a
consumia junto com a própria dinâmica. Separar as duas coisas é o que permite
ao M3 ler a capacidade da `ResourceSlice` em vez de instanciar um subsistema
(ADR 0013).

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `resource` |
| escreve | `ResourceSlice` (`water_available`, `nutrients_available`, `energy_available`, `carrying_capacity`, `consumed`) |
| lê (mesmo tick) | `AstronomySlice.solar_flux`, `ClimateSlice.temperature`, `HydrologySlice` (`ocean`, `freshwater`), `ChemistrySlice` (`nutrients`, `nitrogen`, `phosphorus`, `sulfur`) |
| lê (defasado) | `BiotaSlice.biomass` |
| eventos | `CarryingCapacityShift`, `ResourceScarcity` |
| parâmetros | `params.yaml` (versionado) |

**Por que a biomassa é leitura defasada.** O Biota roda DEPOIS do Resource — ele
precisa da capacidade deste tick para crescer. Logo o consumo contabilizado aqui
é o da biomassa do tick anterior. É a mesma técnica de quebra de ciclo usada em
`chemistry ⇄ atmosphere`, declarada em `lagged_reads` para que o
`validate_graph` a aceite.

**Eventos.** `CarryingCapacityShift` compara a variação **relativa**, porque a
escala absoluta é arbitrária: cinco unidades significam coisas opostas num
planeta de capacidade 10 e num de capacidade 500. `ResourceScarcity` reporta
quando o **limitante muda** — passa a existir, deixa de existir, ou troca de
identidade. Um planeta pobre em fósforo é pobre em fósforo para sempre; dizer
isso a cada tick afogaria a trilha (ADR-ARCH-0002, Correção 2). E emite-se **um**
evento, não três: a lei do mínimo diz que existe *um* limitante, e nomeá-lo é a
informação pedagógica.
