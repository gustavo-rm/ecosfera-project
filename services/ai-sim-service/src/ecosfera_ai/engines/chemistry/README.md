# Chemistry Engine

Fecha o ciclo do carbono que o M1 abriu pela metade. A Atmosphere é dona do
estoque **atmosférico** desde o ADR 0010; este Engine é dono do estoque
**oceânico**, do sedimento, dos nutrientes e de N/P/S (ADR 0012).

## Documentação científica

### Troca ar–oceano — um fluxo, dois livros

O oceano absorve ou libera CO₂ conforme o desequilíbrio de pressão parcial entre
ar e água — a **lei de Henry**, linearizada em torno da referência
pré-industrial:

```
F = solubilidade · (pCO₂_ar − pCO₂_oceano) · (1 − saturação_do_oceano)
```

> Sabine, C. L. et al. (2004). *The oceanic sink for anthropogenic CO₂.*
> Science 305(5682), 367–371.

O **sinal** é a decisão de projeto que evita dupla contagem: `F > 0` significa
que o oceano **absorve**. Este Engine soma `F` ao próprio reservatório; a
Atmosphere subtrai exatamente o mesmo `F` do dela. Um fluxo, dois livros, sinais
opostos. Sem essa convenção, cada Engine teria a sua própria ideia de para onde
o carbono foi, e a soma dos reservatórios deixaria de fechar.

O termo de **saturação** impede que um oceano cheio continue absorvendo
indefinidamente. Sem ele o reservatório oceânico viraria um sumidouro infinito e
o carbono atmosférico simplesmente desapareceria — que é o oposto do que a
ciência do sumidouro oceânico descreve.

### Onde o carbono pode estar

```
atmosfera (Atmosphere)  ⇄  oceano (Chemistry)  →  sedimento (Chemistry)
        ↑                                              
   desgaseificação (Geology)
```

O soterramento é a única **saída** do sistema acoplado, e o soterrado não some:
vira `soil_carbon`. Contabilizá-lo é o que torna a conservação verificável — sem
esse livro, o teste de balanço não distinguiria sumidouro de vazamento.

### Acidificação

Mais carbono dissolvido, menos pH. A relação é logarítmica porque o pH é, por
definição, o logaritmo negativo da concentração de H⁺:

```
pH = pH_ref − sensibilidade · log10(C_oceano / C_ref)
```

### Nutrientes e N/P/S

Liberados pelo **intemperismo** (proporcional ao relevo e ao vulcanismo que a
Geology publica) e drenados por soterramento. É o mesmo braço "sumidouro" do
ciclo carbonato-silicato que a Atmosphere usa para o carbono, aplicado aos
demais elementos.

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `chemistry` |
| escreve | `ChemistrySlice` (`ocean_carbon`, `soil_carbon`, `nutrients`, `nitrogen`, `phosphorus`, `sulfur`, `ph`, `air_sea_flux`) |
| lê (mesmo tick) | `GeologySlice.relief`, `GeologySlice.volcanism` |
| lê (defasado) | `AtmosphereSlice.co2`, `HydrologySlice` |
| eventos | `OceanAcidification`, `NutrientDepletion`, `CarbonFluxShift` |
| parâmetros | `params.yaml` (versionado) |

**Por que a leitura da atmosfera é defasada.** O Chemistry roda ANTES da
Atmosphere na ordem canônica, então o CO₂ que ele lê é o do tick anterior. A
defasagem de um passo é o que quebra o ciclo `chemistry ⇄ atmosphere` sem
desfazer o acoplamento — a mesma técnica que a Geology já usava, e é declarada em
`lagged_reads` para que o `validate_graph` a aceite (declaração ausente = erro de
boot, não bug silencioso).

**Invariantes:** `ocean_carbon ≥ 0`; conservação do carbono no par
atmosfera+oceano+sedimento dentro de `carbon_tolerance`, verificada pelo Planet
Engine — a soma só muda pelo que entra da geologia.

**Eventos são travessias, não estados.** As três regras comparam *antes* e
*depois*. Um teste sobre o valor corrente (`nutrientes < limiar`) emitiria em
todo tick de todo planeta, já que a fatia nasce zerada — o ruído que o
ADR-ARCH-0002 (Correção 2) proíbe. Pelo mesmo motivo os zeros de abertura não
contam como travessia: zero não é "ácido" nem "sem fluxo", é ausência de medida.
