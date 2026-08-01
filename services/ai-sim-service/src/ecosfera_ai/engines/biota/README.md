# Biota Engine — **PROVISÓRIO**

> `# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)`

Este Engine é temporário e existe por uma razão só: dar dono à `BiotaSlice` para
que o `LegacySubsystemAdapter` pudesse ser aposentado no M2 (ADR 0013/0014). É o
porte do subsistema `life` determinístico, sem alteração de ciência. **Ninguém
deve construir em cima dele achando que é definitivo.**

## Fronteira dura (ADR 0013)

| Aqui dentro | Aqui **nunca** |
| --- | --- |
| biomassa agregada (um número) | espécies, populações, genomas |
| abiogênese por limiar | especiação, extinção de espécie |
| crescimento logístico | seleção, mutação, cruzamento |
| ruído demográfico semeado | agentes, dinâmica trófica, predação |

Nenhum import de `deap`, `mesa` ou `simulation_engine/biology/`. Isso é
verificado pelo **import-linter**, não pela revisão humana: violar a fronteira
quebra o build.

A biologia emergente do M3 vive em `simulation_engine/biology/` e continua onde
está — este Engine não a conhece, e ela não o conhece.

## Documentação científica

### Abiogênese

A vida surge de uma vez, em quantidade fixa, quando o ambiente cruza um limiar
de viabilidade — e só quando ainda não há vida alguma.

O `life` testava `habitabilidade ≥ 0,35`. Aqui a mesma condição está em unidades
de **capacidade**, porque a capacidade é o que o Resource publica e a
habitabilidade deixou de ser grandeza deste Engine:

```
capacidade = capacidade_máxima × habitabilidade = 100 × h
h ≥ 0,35   ⟺   capacidade ≥ 35,0
```

É reparametrização, não mudança de ciência: a desigualdade é a mesma.

### Crescimento logístico

```
dB/dt = r · B · (1 − B/K)
```

> Verhulst, P.-F. (1838). *Notice sur la loi que la population suit dans son
> accroissement.* Correspondance mathématique et physique 10, 113–121.

`K` é a `carrying_capacity` que o Resource Engine publica. Quando `K` é zero — um
ambiente inviável — o crescimento vira declínio à mesma taxa: a vida existente
não se sustenta.

### Ruído demográfico

Proporcional à população, e não aditivo. A escolha vem do `life` e tem razão:
perto de zero o ruído é desprezível, então a abiogênese "pega" em vez de ser
sorteada de volta ao nada; e a variação absoluta cresce com a biomassa, como numa
população real.

O sorteio é feito com o desvio-padrão do parâmetro (`normal(0, σ) · biomassa`), e
não normalizado-e-multiplicado. As duas formas têm a mesma distribuição mas não a
mesma sequência de bits — e a fidelidade do porte é o ponto.

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `biota` |
| escreve | `BiotaSlice.biomass` |
| lê (mesmo tick) | `ResourceSlice.carrying_capacity` |
| lê (defasado) | — |
| eventos | `Abiogenesis`, `BiomassCollapse` |
| parâmetros | `params.yaml` (versionado) |

`species_richness` fica em zero: é campo da camada emergente, e escrevê-lo aqui
seria fingir uma riqueza que este Engine não modela.

**A única entrada é a capacidade.** Este Engine não sabe o que é temperatura,
água ou nutriente. Quem traduz física em orçamento é o Resource — e é por o Biota
não saber que a fronteira física/biologia se sustenta.
