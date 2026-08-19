# Ecology Engine

Fecha o tick. Recebe a comunidade que a Evolution já resolveu e decide a **forma
da pirâmide trófica**: quanto da biomassa é produtor, herbívoro e predador, e que
pressão de predação isso devolve à evolução.

## Documentação científica

### O que ele decide, e o que não é dele decidir

A Ecology decide a **forma** da pirâmide; o **tamanho** é da Evolution. Se ela
escrevesse um total próprio, haveria duas fontes de biomassa no world-state — a
dupla contagem que o ADR 0016 proíbe. Por isso a repartição é renormalizada ao
total publicado na `BiotaSlice`, e a soma dos três níveis é exatamente esse
total (afirmado em `test_the_ecology_redistributes_without_creating_biomass`).

### A pirâmide de biomassa não inverte

Renormalizar de forma ingênua — escalar os três níveis pelo mesmo fator — tem um
defeito **medido**: quando os produtores colapsam e os predadores sobrevivem, o
fator escala os predadores para cima até absorverem todo o total, produzindo um
planeta de predadores sem nada para comer.

Cada nível trófico carrega menos biomassa que o de baixo, porque a conversão
dissipa energia. Isso vira restrição explícita: os consumidores somados não
passam de `max_consumer_share` (0,50) do total, e o produtor é a **base** que
absorve o restante.

> Elton, C. (1927). *Animal Ecology.* — a pirâmide de biomassa.

### Sucessão ecológica emergente

Uma comunidade recém-nascida chega como um número só. Níveis superiores **não
são semeados de saída**: eles se estabelecem quando o nível de baixo passa a
comportá-los. O limiar é **derivado das próprias taxas**, não arbitrado — um
consumidor ganha `conversão × predação × presa` por unidade de si e perde
`mortalidade`, logo só se sustenta quando

```
conversão × predação × presa  >  mortalidade
⟹  presa_mínima = mortalidade / (conversão × predação)
```

Calcular o limiar em vez de configurá-lo é o que impede que ele fique incoerente
com as taxas quando alguém as recalibrar.

Semear os níveis superiores antes disso plantaria herbívoros num mundo sem o que
comer: eles morreriam no primeiro passo e **nunca mais voltariam**, porque o
semeio só acontece uma vez — a pirâmide degenerada que este mecanismo corrige. É
a disponibilidade de recurso que abre o nicho, não um roteiro que decide quando
cada nível aparece.

### Passo trófico síncrono, com teto de captura

```
pastagem  = min(produtor,  taxa_predação × herbívoro × produtor)
caça      = min(herbívoro, taxa_predação × predador  × herbívoro)
crescimento_produtor = taxa_crescimento × produtor × (1 − produtor/capacidade)
```

Duas correções do M3 sobre o modelo anterior:

1. **Atualização síncrona** — todos leem a mesma fotografia do passo. Na versão
   sequencial, quem agia depois via o estado já alterado por quem agiu antes, e a
   ordem de iteração virava ciência.
2. **Teto global de captura por nível, com racionamento proporcional** — sem ele,
   os predadores somados comem mais presa do que existe, e a diferença vira
   biomassa do nada.

O crescimento do produtor é logístico (Verhulst, 1838) contra a
`carrying_capacity` publicada pelo Resource. Sem capacidade, resta a mortalidade.

### Consumidores generalistas (ECO-001, Fase 1)

A cadeia acima é ESTRITA: o predador come só herbívoro. A validação da Tássia
apontou isso como a maior lacuna — a maioria das espécies é generalista. O
predador passa a ter uma **dieta**: pesos de preferência sobre mais de um nível
de presa, que somam 1. Como onívoro, ele drena o produtor além do herbívoro,
abrindo um **segundo caminho de propagação** (um choque nos produtores alcança o
topo por dois trajetos, não um só).

```
caça      = min(herbívoro, taxa × predador × herbívoro × peso_herbívoro)
onivoria  = min(produtor,  taxa × predador × produtor  × peso_produtor)   # NOVO
# o poço do produtor é racionado entre pastagem + onivoria (nenhum poço negativo)
ganho_predador = conversão × (caça + onivoria) × teto_eltoniano(predador)
```

Os pesos **somam 1**: o generalista reparte o forrageio, não ganha captura "de
graça"; o teto eltoniano do M4 segue amortecendo o ganho TOTAL. Conservação e
não-inversão da pirâmide preservadas (ADR 0030).

**Progressão por era (cadeias → teias).** A onivoria não liga de uma vez: sua
força cresce da era `unlock_era` (cadeia estrita) à `full_era` (dieta plena). Em
toda a **era 0** os pesos são `(1, 0)` — o passo reduz bit a bit ao do M4, e a
linha de base fica intacta.

**Magnitude CONSERVADORA de fábrica (produtor 0,02).** A onivoria de força plena
(0,30) é dinamicamente correta mas AMPLIFICA a dívida de carbono de longo prazo
(ADR 0020) acima do teto de 60 ppm — está **bloqueada pela Fase 3** (correção de
carbono). O default de fábrica é medido como não-amplificante; a força plena fica
represada até a Fase 3 landar (ver ADR 0030, "Dependência entre fases").

**Ainda pendente na Fase 1:** `ECO-002` (competição, mutualismo, parasitismo),
`ECO-003` (decomposição/ciclo de nutrientes) e `ECO-005` (destaque das oscilações
predador-presa). Cada um constrói sobre esta dieta e precisa da mesma verificação
de horizonte longo.

### Cadência (mudou no M3)

Roda `steps_per_tick` passos **por tick** (padrão 1), e não um lote por era.
Antes o modelo rodava 12 passos no fecho da era, sobre um instantâneo congelado
do início dela. Com `era_length: 10` o trabalho total por era é equivalente, mas
a ecologia passa a ler um ambiente **atualizado entre os passos**.

É melhor cientificamente e **muda a trajetória numérica**. Como o M3 é o marco
que introduz a biota no world-state, não há baseline anterior a preservar:
qualquer baseline de replay da ecologia é novo a partir daqui (ADR 0016).

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `ecology` |
| escreve | `EcologySlice` (`producer_biomass`, `herbivore_biomass`, `predator_biomass`, `predation_pressure`, `total_population`) |
| lê (mesmo tick) | `BiotaSlice.biomass`, `ResourceSlice.carrying_capacity` |
| lê (defasado) | — |
| eventos | `TrophicCollapse`, `PopulationDeclined` |
| parâmetros | `params.yaml` (versionado) |
| posição no tick | 9ª — fecha o tick, porque precisa da comunidade já resolvida |

**Por que fecha o tick.** Lê a `BiotaSlice` do MESMO tick: precisa da comunidade
já resolvida pela Evolution para reparti-la. O acoplamento de volta
(pressão de predação → seleção) é que se resolve por defasagem, declarada do lado
da Evolution.

**Este Engine não usa `mesa`.** Ele PORTA a ciência do modelo por agente para
aritmética pura sobre três agregados; não o envolve. O ABM opera sobre populações
por espécie, e este Engine opera sobre níveis tróficos — que é o que cabe no
Canal A (aditivo, de floats). Envolvê-lo exigiria materializar a lista de
espécies a cada tick só para agregá-la de volta.

A consequência é que os nove Engines importam e rodam **sem o extra `sim`**
instalado (verificado em `test_app_boots_without_sim.py`). O ABM com `mesa`
segue vivo no caminho de biologia por era, atrás de fábrica preguiçosa
(ADR 0017).

**Eventos por NÍVEL, nunca por organismo.** `TrophicCollapse` e
`PopulationDeclined` reportam **travessia de limiar** por nível trófico agregado.
Emitir por indivíduo afogaria a trilha e violaria a granularidade agregada
padrão (ADR-ARCH-0002, Correção 2).
