# ADR 0013 — `physics` → Astronomy Engine, e a fronteira do Biota provisório

## Status
Aceito. Parte do M2. Complementa o **ADR 0012** (ciclos fechados) e é
pré-requisito do **ADR 0014** (aposentadoria do legado). Preserva o **ADR 0006**
(fronteira determinístico × emergente). Referências: Dossiê v3 §8/§10.4,
Spec §3/§5.1/§5.3, RF-014, RF-023.

Este ADR trata de **fronteiras de domínio**. A decisão de remover o legado e a
flag é outra, e está registrada separadamente no ADR 0014 — de propósito: são
decisões diferentes, com consequências diferentes, e merecem rastreabilidade
separada.

## Contexto

Ao preparar a aposentadoria do `LegacySubsystemAdapter`, dois dos seis
subsistemas legados apareceram como **órfãos**: nenhum Engine do M0/M1 assumiria
o que eles faziam.

- **`physics`** integrava a órbita e publicava `solar_flux`. A `AstronomySlice`
  existia desde o M0 e nunca teve escritor.
- **`life`** produzia a biomassa agregada e publicava a capacidade de suporte —
  o único acoplamento entre a física e a biologia (ADR 0006).

Retirar o adaptador sem resolvê-los deixaria duas fatias sem dono, e o efeito no
caso do `physics` seria **silencioso**, que é o pior tipo.

## Decisão

### 1. `physics` vira o Astronomy Engine — porte, não ciência nova

O subsystem `physics` foi portado para `engines/astronomy/` sem recalibração:
mesmo integrador de velocity Verlet, mesma lei do inverso do quadrado, mesmos
valores de GM, `dt`, luminosidade e raio orbital.

Não é ciência nova, é uma grandeza recebendo dono. A `AstronomySlice` foi criada
no M0 exatamente para isto e estava órfã desde então.

**Ele abre a ordem do tick.** A insolação é a entrada de energia de tudo o que
vem abaixo: o Climate a consome no balanço radiativo, o Resource a converte em
energia biologicamente útil. Por isso `astronomy → geology → chemistry →
atmosphere → climate → hydrology → resource → biota`.

É o único Engine com `reads` vazio, e isso é uma afirmação física: a órbita é
condição de contorno externa, não resposta ao planeta. Se um dia ele passar a ler
algo, é sinal de que uma retroalimentação indevida entrou no modelo.

### 2. Por que a fatia órfã exigia um teste anti-regressão

`incident_flux()` tem um recuo deliberado para `params.insolation` quando o fluxo
é zero, criado para permitir testar o clima isoladamente.

Com a `AstronomySlice` órfã, esse recuo viraria o caminho de PRODUÇÃO. E o
sintoma seria invisível: o planeta perderia estações e excentricidade, a
temperatura continuaria plausível, a suíte continuaria verde, e ninguém saberia
que a astronomia havia sumido. Uma constante de referência é exatamente o tipo de
erro que não se denuncia.

`tests/unit/test_solar_flux_has_writer.py` fixa três coisas: a fatia TEM
escritor, o valor VARIA ao longo do tempo (a órbita está viva, não é uma
constante escrita à mão), e o Climate LÊ o world-state em vez do recuo — provado
por dois fluxos distintos produzirem energias absorvidas distintas.

### 3. `life` vira o Biota Engine — **provisório**, com fronteira dura

O Biota Engine porta a física determinística do `life` e **nada mais**:
crescimento logístico da biomassa até a capacidade de suporte, abiogênese por
limiar e ruído demográfico. Escreve a `BiotaSlice`, que existia vazia desde o M0.

Ele existe por uma razão só: dar dono à fatia para que o adaptador pudesse ser
aposentado. **É substituído pela evolução emergente no M3.**

**Fronteira dura:**

| Aqui dentro | Aqui **nunca** |
| --- | --- |
| biomassa agregada (um número) | espécies, populações, genomas |
| abiogênese por limiar | especiação, extinção de espécie |
| crescimento logístico | seleção, mutação, cruzamento |
| ruído demográfico semeado | agentes, dinâmica trófica, predação |

Nenhum import de `deap`, `mesa` ou `simulation_engine/biology/`.

**Isso é verificado pelo import-linter, não pela revisão humana.** Um contrato
`forbidden` liga `ecosfera_ai.engines.biota` a esses três alvos: violar a
fronteira quebra o build. Uma fronteira que depende de alguém lembrar dela numa
revisão não é uma fronteira, é uma intenção.

Todo módulo do pacote carrega no topo:

```python
# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)
```

para que ninguém construa em cima dele achando que é definitivo.

**A biologia emergente não se mexeu.** `simulation_engine/biology/` (DEAP, Mesa,
códex, genoma) continua onde está, fora da moldura de Engines, e o Biota não a
conhece. A verificação de que o porte era seguro foi feita antes: o `life.py`
importava apenas `math`, `dataclass`, `numpy` e `simulation_engine.state` —
nenhuma dependência de `biology/`. A fronteira `life` (determinístico) × `biology`
(emergente) já estava limpa no código, e o porte não a borrou.

### 4. Quem deriva a capacidade de suporte passa a ser o Resource

Esta é a mudança de fronteira que o porte tornou possível, e vale ser explícita
porque muda um consumidor fora da moldura.

O `life` fazia duas coisas: derivava a capacidade de suporte E crescia a biomassa
dentro dela. O M2 separa as duas.

- O **Resource Engine** deriva a capacidade a partir da física — quatro fatores
  multiplicativos, com a lei do mínimo de Liebig sobre os macronutrientes. Os
  termos térmico e hídrico são os do `life`, com os mesmos valores; nutriente e
  energia são novos.
- O **Biota Engine** apenas a consome. Ele não sabe o que é temperatura, água ou
  nutriente — e é por não saber que a fronteira física/biologia se sustenta.

O limiar de abiogênese foi **reparametrizado**, não alterado. O `life` testava
`habitabilidade ≥ 0,35`; como `capacidade = 100 × habitabilidade`, a mesma
desigualdade em unidades de capacidade é `capacidade ≥ 35`. É a mesma condição
escrita na grandeza que o Resource publica.

### 5. A costura do M3: `carrying_capacity` é publicada no estado

`EvolveBiologyUseCase` recebia um `LifeSubsystem` no construtor só para chamar
`carrying_capacity(state)`. Ele passou a ler `state.carrying_capacity`, mapeado
da `ResourceSlice` pela ponte.

A dependência que sumiu importa: com o `LifeSubsystem` injetado, o caso de uso
continha uma SEGUNDA cópia da ciência de habitabilidade, que podia divergir da do
Engine sem que nada acusasse. Ler o valor publicado torna a divergência
impossível por construção — existe um número, calculado num lugar, e é o mesmo
que a biologia consome.

O mesmo vale para `GET /planets/{id}/ecology`: a resposta não mudou de forma, mas
o número agora é o que a simulação de fato usou.

Isso responde à pergunta de fiação do M3: quando a evolução emergente substituir
o Biota provisório, ela lê a capacidade da `ResourceSlice` (via `PlanetState`), e
não de um subsistema instanciado à parte. A costura já está feita e testada
(`test_carrying_capacity_is_the_only_coupling_point`).

## Consequências

+ `solar_flux` e o estado orbital têm dono; estações e excentricidade continuam
  vivas e agora são testáveis.
+ Toda fatia do world-state tem um Engine escritor — o pré-requisito do ADR 0014.
+ A capacidade de suporte tem UMA fonte, e o M3 já sabe de onde lê.
+ A fronteira do Biota é executável: quebrar quebra o build.
− Existe um Engine provisório em produção. O risco é alguém tratá-lo como
  definitivo, e é contra isso que os marcadores de módulo, o README e o contrato
  de import-linter foram escritos.
− O Resource acrescentou dois fatores (nutriente e energia) que o `life` não
  tinha, então a capacidade não é numericamente idêntica à do legado fora do
  estado inicial. É melhoria deliberada de modelo, não porte infiel: os termos
  portados mantêm os valores originais, e o ADR 0012 registra por que as
  condições iniciais dos nutrientes precisaram ser explicitadas.
