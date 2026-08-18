# ADR 0030 — Consumidores generalistas (ECO-001): a onivoria como primeira teia

**Status:** aceito
**Marco:** Fase 1 (Relações ecológicas) — primeiro incremento, pós-M6
**Relacionados:** PLANO_EVOLUCAO_ECOSFERA.md (§5.2 ECO-001, §9 Fase 1, §11, §13) ·
ADR 0016 (a Ecology reparte, não escreve o total) · ADR 0019 §6 (teto eltoniano
em todos os níveis, Q11) · ADR 0020 (instabilidade de carbono em horizonte longo,
dívida herdada) · ADR 0017 (Caminho B dormente; os Engines rodam sem `sim`)

## Contexto

A validação da especialista (Tássia) apontou a **maior lacuna científica** da
ecologia do ECOSFERA (Plano, Div. 3): a cadeia linear estrita — cada predador
come **só** o nível imediatamente abaixo — empobrece o modelo, porque a maioria
das espécies reais é **generalista**. O Plano posiciona `ECO-001` (teias e
generalistas) como a **fundação** da Fase 1, pré-requisito de tudo o que vem
depois (competição/mutualismo/parasitismo em `ECO-002`, decomposição em
`ECO-003`, impactos antrópicos na Fase 4).

Esta fase é a de **maior risco técnico** do plano: mexe na dinâmica emergente do
Ecology Engine, já corrigida duas vezes — a reescrita síncrona do M3 (predação
fantasma) e a ancoragem eltoniana do M4 (colapso de capacidade). Qualquer termo
ecológico novo é candidato a reabrir conservação de biomassa e estabilidade de
longo prazo. A regra de trabalho foi a lição do M4: **não basta passar nos testes
por tick — é preciso medir a trajetória longa.**

O modelo ativo (o Engine, não o ABM legado dormente do Caminho B) representa a
comunidade como **três agregados**: `(produtor, herbívoro, predador)`. Nesse
modelo, o único consumidor que PODE comer de mais de um nível é o predador — a
onivoria (comer produtor além de herbívoro) é a forma concreta de "generalista"
que cabe aqui. Dieta por espécie é território da Fase 2 (identidade de espécies).

## Decisão

### 1. O predador ganha uma DIETA — pesos de preferência sobre níveis de presa

Onde antes a predação era fixa (`herbívoro→produtor`, `predador→herbívoro`), o
predador passa a ter uma dieta `(herbivore, producer)` — pesos que **somam 1**. O
generalista **reparte** o esforço de forrageio entre as duas fontes; não o
duplica. Não há ganho de captura "de graça" por drenar dois poços: a demanda
total continua sendo `taxa × predador × (w_h·herbívoro + w_p·produtor)`.

A dieta abre um **segundo caminho de propagação**: um choque nos produtores
alcança o topo por dois trajetos (`produtor→herbívoro→predador` E
`produtor→predador`), que é exatamente o critério de validação do Plano §13
("efeitos propagados pelas relações — teia, não cadeia linear única").

### 2. Progressão por era (PED-001; compromisso da Tássia): cadeias → teias

A onivoria não liga de uma vez. Sua **força** (`generalist_strength`) sobe em
rampa linear da era `unlock_era` (ainda cadeia estrita) à `full_era` (dieta
plena). Antes de `unlock_era` — e portanto em **toda a era 0** — a dieta é
`(1, 0)`: o passo trófico reduz **bit a bit** ao do M4. É um parâmetro contínuo
que a era desloca, não um roteiro que decide o que cada era faz — a mesma forma
da sucessão ecológica emergente que o Engine já tinha.

Consequência de projeto: como toda a linha de base física e toda a suíte de
replay do M4 rodam na **era 0** (o loop de tick não promove era; quem promove é a
borda de linha do tempo, `open_next_era`), elas ficam **inalteradas** por
construção. A compatibilidade com o predador de nível único é estrita, provada em
`test_backward_compatible_single_level_diet` (igualdade EXATA contra a fórmula do
M4 numa grade que inclui os casos em que o teto de captura morde).

### 3. Teto global de captura por POÇO, com racionamento proporcional (estende M3)

Quando o predador onívoro come do **mesmo poço** que o herbívoro (o produtor
sofre pastagem E onivoria no mesmo tick), a soma das capturas não pode exceder o
estoque. O teto do M3 (`min(presa, demanda)`) vira `_ration_pool`: se a demanda
somada cabe, cada um leva o que pediu; se excede, todos escalam pelo mesmo fator
até a soma igualar o estoque. Para um consumidor único reduz a `min` **sem erro
de 1 ULP** — o que preserva a linha de base da cadeia estrita. Provado em
`test_no_prey_pool_over_predated` e `test_conservation_holds_with_generalist_predation`.

### 4. O teto eltoniano (M4, Q11) NÃO é furado pela onivoria

O ganho do predador é convertido da captura das DUAS fontes, mas o mesmo termo de
Verhulst `_room(predador, teto)` amortece o ganho **total**, e a `_renormalised`
segue amarrando a soma dos níveis à biomassa da Evolution (ADR 0016) e limitando
os consumidores a `max_consumer_share`. A onivoria não compra capacidade extra
nem inverte a pirâmide. Provado em `test_eltonian_capacity_ceiling_still_holds`.

### 5. Dado versionado (params.yaml v2), não código

`unlock_era`, `full_era` e os pesos da dieta vivem em `params.yaml`. A ausência do
bloco (params v1) assume cadeia estrita (`producer=0`), então a versão anterior
continua reconstruível.

## O achado de horizonte longo, e a MAGNITUDE conservadora

A lição do M4 se cumpriu: os testes por tick passavam, mas a medição de
**trajetória longa** (regime de eras, o jogo real) revelou que a onivoria, embora
**cientificamente correta**, **amplifica a dívida de carbono do ADR 0020**.

O mecanismo é honesto: a onivoria muda a `predation_pressure` → a Evolution a lê
defasada → a biomassa muda → o sumidouro biótico de carbono muda. Em **força
plena** (peso do produtor 0,30), isso empurra a amplitude de CO₂ de algumas
sementes **acima do teto de 60 ppm** e, no horizonte da dívida (3000 ticks),
acelera o colapso da biosfera.

### O padrão medido (16 sementes, regime de eras, 500 ticks)

- **O teto de 60 ppm é propriedade das 4 sementes escolhidas** da baseline
  (2027, 99, 11, 5), **não do modelo**: na cadeia estrita, 7 de 16 sementes já
  passam de 60 ppm — a dívida do ADR 0020, anterior a esta fase.
- **A amplificação é ESPECÍFICA DE SEMENTE, não geral.** A maioria das sementes é
  insensível à onivoria (dominadas pela dívida de carbono). Poucas viram: a
  semente 5 cruza 60 em peso ≥ 0,04 (43→66 ppm); a 17 em peso ≥ 0,10; a 2027 e a
  50 só em 0,30.
- **Em peso 0,02 a amplificação é NULA:** o conjunto de sementes acima de 60 é
  **idêntico** ao da cadeia estrita (nenhuma nova, nenhuma removida) — a semente 5
  fica em 43,6, a 99 em 45,7, com margem abaixo do ponto de virada da 5 (0,04).
- No horizonte da dívida, o colapso é um **RESHUFFLE caótico**: em peso 0,30 a
  biomassa da semente 5 decai a ~3,6e-26 (extinta) onde a estrita a mantinha em
  ~28,8; em 0,15, a semente afetada era a 99 (viva na estrita em ~21,8). QUAL
  semente cai depende do peso — típico de um regime caótico sem termostato de
  carbono, não um agravamento sistemático.

### Decisão: default CONSERVADOR agora, força plena represada até a Fase 3

Amplificar uma dívida conhecida além do teto aceito **não é aceitável como
comportamento default**, mesmo sendo cientificamente correto. Seguindo o mesmo
padrão do M1 (framework de Engines default-off até maduro) e do M3
(`biology_enabled` default-off), a **magnitude** da onivoria é versionada e o
default de fábrica é **conservador**:

> **Peso do produtor = 0,02** — MEDIDO como não-amplificante (mesma disciplina do
> M4 que fixou `consumer_capacity_share=0,60`). O mecanismo existe, é exercido, é
> versionado e testado; a FORÇA fica represada.

O teto de 60 ppm **não foi movido** e a Fase 3 **não foi puxada para este turno**.
O achado de força plena não é apagado: fica reproduzido, como resultado ESPERADO,
em dois testes `xfail` de `test_long_horizon_stability_not_worsened`
(amplitude > 60 na semente 5; colapso da biosfera no horizonte da dívida). Quando
a Fase 3 pagar a dívida, eles viram `xpass` e o relatório avisa sozinho que a
força plena foi destravada — o mesmo mecanismo de `test_carbon_stable_long_horizon`.

## Dependência entre fases (registro para o arquiteto)

> **A predação generalista de FORÇA PLENA (Fase 1) está BLOQUEADA pela correção de
> carbono de longo prazo (Fase 3, ADR 0020).** A onivoria é dinamicamente correta,
> mas amplifica a instabilidade de carbono herdada além do teto de estabilidade
> aceito (60 ppm). Enquanto não existir o termostato de silicatos dependente de
> temperatura (Walker/Hays/Kasting 1981, hipótese do ADR 0020), a magnitude da
> onivoria fica represada num default conservador (produtor 0,02). A configuração
> de força plena (0,30) só se torna disponível quando a Fase 3 landar.

**Recomendação:** a Fase 3 pode precisar subir na prioridade em relação à ordem
original do Plano (§9), porque destrava o valor pedagógico pleno da Fase 1. E o
alerta se agrava com `ECO-002` (competição/mutualismo/parasitismo): esses termos
são candidatos a **compor a mesma amplificação** sobre a biomassa e, por ela, o
carbono. Convém avaliar se a Fase 3 deve preceder `ECO-002`, ou ao menos se cada
incremento de `ECO-002` precisa da mesma verificação de horizonte longo antes de
sair do default conservador.

## Consequências

**Ganhamos.** A ecologia deixa de ser uma cadeia linear estrita: o predador é um
generalista de fato, e uma perturbação nos produtores se propaga por dois
caminhos até o topo — a fundação que `ECO-002`/`ECO-003` e os impactos antrópicos
(Fase 4) exigem. As invariantes do M3 (conservação, teto de captura) e do M4
(teto eltoniano, não-inversão da pirâmide) foram **estendidas, não reescritas**, e
seguem provadas. A linha de base é preservada bit a bit.

**Contivemos.** A força plena, que entregaria a teia visível, fica represada por
uma dependência real e documentada — não por medo, mas por medição. O default é
tão conservador que seu rastro de carbono está dentro do ruído da cadeia estrita.

**Aberto / o que os próximos incrementos herdam.**
- `ECO-002` e `ECO-003` constroem sobre esta dieta: novos tipos de relação
  (competição por um mesmo poço; mutualismo; parasitismo; decomposição que devolve
  nutriente) entram como novas **fontes de demanda** sobre os mesmos poços, e o
  `_ration_pool` já é o ponto onde essa concorrência é resolvida sem criar
  biomassa. Cada um precisa da **mesma verificação de horizonte longo** antes de
  qualquer default não-conservador.
- `ECO-005` (destaque das oscilações predador-presa) e as mudanças de
  Tutor/frontend dependem deste incremento e vêm depois.
- A dependência da Fase 3 acima é a peça a resolver antes de destravar a força
  plena da onivoria.
