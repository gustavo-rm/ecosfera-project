# ADR 0023 — Especiação por ancestral comum, e a causa dentro do evento

## Status
Aceito. Abre a **Fase 0** do `PLANO_EVOLUCAO_ECOSFERA.md` — o único pré-requisito
do M6 (Tutor). Aplica **BIO-001** (ancestral comum), a parte pré-M6 de
**BIO-002** (causa no evento), **BIO-005** (linguagem anti-teleológica),
**PED-003** (adaptação × especiação) e valida **BIO-006** (extinção catastrófica).
Referências: ADR-ARCH-0001, ADR-ARCH-0002 (Correção 1), ADR 0016, ADR 0017,
ADR 0019, ADR 0024, Spec §4/§7.

## Contexto

O M6 é o Tutor. O Tutor **narra a ciência da simulação**: ele não recalcula
ciência, ele lê a trilha de eventos e a traduz em explicação (ADR-ARCH-0002,
Correção 1). A consequência disso é assimétrica e é o que motiva esta fase — se a
ciência de base estiver errada, o Tutor **ensina o erro com autoridade**, e com
mais eficácia do que ensinaria o acerto, porque a explicação é justamente o que a
plataforma tem de mais convincente.

A regra de fronteira que separa o que é pré-M6 do que é pós-M6: uma mudança é
pré-M6 se, sem ela, o Tutor narraria algo **cientificamente errado** — não apenas
"menos rico". Ancestralidade errada é pré-M6. Teias alimentares ausentes é pós-M6.

### O que a inspeção encontrou

Havia **dois** modelos de especiação no binário, e os dois falhavam o BIO-001 por
razões diferentes:

| | Caminho A — Evolution Engine | Caminho B — biologia por era |
| --- | --- | --- |
| estado | vivo, roda todo tick | **dormente** desde o M3 (ADR 0017 tempo 1) |
| modelo | genoma médio da comunidade (ADR 0016) | códex de espécies com identidade |
| especiação | `SpeciationOccurred` com `participants: ["species:community"]` | `SpeciesRecord(ancestor_id=<espécie VIVA>)` |
| defeito | **um sujeito só** — um evento de divisão com um único sujeito só pode ser lido como "aquele sujeito produziu a novidade" | **"A→B" literal** — o ancestral é escolhido entre as espécies vivas |

O caminho B é o caso que o BIO-001 descreve ao pé da letra. O caminho A é o caso
mais sutil e mais urgente, porque é o que de fato alimenta a trilha que o Tutor
vai ler: ele não *afirmava* "A gerou B", mas também não oferecia nenhuma outra
leitura — e a leitura que um consumidor faz de um evento de especiação com um
único participante é exatamente a proibida.

Duas outras coisas apareceram na inspeção e estão registradas aqui porque são
achados, não escolhas:

1. **A especiação não tinha causa, tinha régua.** O `cause_code` era
   `GENETIC_DIVERGENCE` — o critério de decisão ("os genomas ficaram distantes"),
   e não o motivo da divisão.
2. **A especiação era inarrável.** `SpeciationOccurred` virava uma observação de
   `species_richness`, e **nenhuma regra causal partia dessa variável**. A cadeia
   morria ali. O aluno via a riqueza mudar e não ouvia nada — e num tema em que a
   intuição espontânea é "a espécie A virou a B", o silêncio é a intuição
   espontânea sendo confirmada.

## Decisão

### 1. O evento de especiação registra UM ancestral e DUAS linhagens

`SpeciationOccurred` passa a nomear três papéis no `participants` do envelope §4:

```
participants = ("ancestor:<id>", "lineage:<id_a>", "lineage:<id_b>")
```

O ancestral é a população **como ela era antes da divisão**; as duas linhagens
são **irmãs**, e o ancestral não é nenhuma das duas. A linhagem A segue com os
traços ancestrais, a B com os divergentes — e o `cause_detail` carrega o genoma
das **três**, explicitamente. A redundância (A é igual ao ancestral) é
deliberada: deixá-la implícita obrigaria o consumidor a conhecer a regra, e um
consumidor que erra a regra narra ancestralidade errada, que é o defeito que este
ADR fecha.

**Por que a diferença não é de redação.** No modelo "A→B" a espécie que continua
existindo aparece como progenitora da outra, e daí sai a escada de progresso: o
aluno conclui que B é "mais evoluída" que A e que A é uma versão antiga de B. No
modelo de ancestral comum não existe progenitora viva — existe uma população
ancestral que se dividiu e duas linhagens contemporâneas.

**Regra dura para todo consumidor** (regras causais de hoje, Tutor do M6): é
proibido gerar texto que afirme que uma espécie deu origem a outra. A forma
correta é *"duas linhagens compartilham um ancestral comum que sofreu
especiação"*.

### 2. As identidades são derivadas, nunca sorteadas

`lineages_for(seed, era, tick)` deriva os três identificadores por `uuid5` sobre
(semente, era, tick, papel) — a mesma técnica dos `event_id`. Um `uuid4()` aqui
quebraria o replay bit-a-bit tanto quanto quebraria no envelope: a mesma semente
produziria trilhas diferentes, a simulação continuaria "funcionando" e o passado
deixaria de ser reconstruível (Spec §7, RF-023).

Os identificadores são de **linhagem naquele instante**, e não de espécie ao
longo do tempo. Rastrear identidade de linhagem através dos ticks exigiria estado
no Engine, e `tick()` é função pura do snapshot — é disso que o replay depende
(ADR 0016 §2). Identidade persistente de espécie é a camada que o ADR 0024
deixou para depois do M6.

### 3. A especiação carrega a CAUSA que a disparou (BIO-002, parte pré-M6)

Quatro códigos novos, com a correspondência aos nomes do Plano registrada no
próprio vocabulário:

| `cause_code` | Plano | Diagnosticado quando |
| --- | --- | --- |
| `DIVERGENT_NICHE` | NICHO_DIVERGENTE | a linhagem divergente cruzou de classe trófica |
| `ENVIRONMENTAL_PRESSURE` | PRESSAO_AMBIENTAL | o ambiente saiu da janela térmica do ancestral, ou o orçamento ambiental estourou |
| `REPRODUCTIVE_ISOLATION` | ISOLAMENTO_REPRODUTIVO | nenhum dos dois: a diferença acumulada é o próprio motivo |
| `GEOGRAPHIC_BARRIER` | BARREIRA_GEOGRAFICA | **nunca — não há geografia neste modelo** |

`GENETIC_DIVERGENCE` fica **superada**: nomeava a régua, não o motivo. O membro
do enum continua declarado porque `event_from_dict` recusa um `cause_code` fora de
todo vocabulário carregado — removê-lo tornaria ilegível toda trilha gravada
antes da Fase 0.

**`GEOGRAPHIC_BARRIER` é declarada e não é emitida, de propósito.** É a causa
canônica da especiação alopátrica e o vocabulário do Tutor a exige; o modelo, por
outro lado, não tem regiões (toda `location` é `region_id: global`), então não há
barreira a detectar. Um código anunciado e nunca produzido é a mesma família de
furo silencioso que o M2 encontrou no `solar_flux`: o vocabulário promete uma
explicação que a simulação nunca entrega, e nada estoura. Por isso o registro
`CAUSES_WITHOUT_EMITTER` existe, com a razão escrita ao lado, e um teste exige
que todo código do enum ou tenha emissor ou esteja lá — o buraco é **ruidoso**.

### 4. A mecânica GRADUAL não entra nesta fase, e isso é a decisão

A especiação continua sendo divergência acima de um limiar, num único passo. O
BIO-002 pede que ela seja gradual e mantida ao longo de gerações; isso é **Fase 2
do Plano, pós-M6**, e está declarado em `has_speciated`.

Duas razões. A primeira é de escopo: o que bloqueia o Tutor é a ancestralidade
errada e a causa ausente, não a granularidade temporal do mecanismo. A segunda é
que tornar a divergência gradual muda a **trajetória numérica** de toda a
biologia, e uma mudança dessas no mesmo marco que corrige o envelope tornaria
impossível separar o que quebrou o quê.

**Consequência medida, e registrada porque é desconfortável:** com o limiar de
produção (`speciation_threshold: 0,12`) o evento é praticamente **inalcançável**.
A distância de um passo de mutação vale ~0,02, e chegar a 0,12 num tick exigiria
um desvio de ~6 σ. Ou seja: a especiação existe no modelo, está corretamente
descrita e quase nunca acontece. Isso **não é** consertado aqui — calibrar o
limiar mudaria a dinâmica, e a correção certa é a mecânica gradual da Fase 2, que
acumula divergência em vez de exigi-la de um salto. Os testes declaram o cenário
(limiar baixado por parâmetro), mesma técnica do `build_volcanic_planet`.

### 5. A especiação passa a ser NARRÁVEL, e a narração distingue os fenômenos

`configs/causal_rules.yaml` sobe 4 → 5 com três regras:

- `R-SPECIATION-COMMON-ANCESTOR` — parte de `species_richness` (a variável em que
  a especiação já era traduzida) e narra a divisão a partir de um ancestral
  comum. Fecha a cadeia que morria;
- `R-TRAIT-ADAPTATION` — narra a mudança de traço médio como **adaptação**:
  frequência dos traços mudando dentro de uma linhagem que continua sendo uma só,
  e diz explicitamente que **não** é o surgimento de uma linhagem nova (PED-003);
- `R-ADAPTATION-RANDOM-VARIATION` — põe a ordem correta na frase: a variação vem
  antes e sem propósito ("surgiu uma mutação aleatória"), o ambiente decide
  depois ("porque aumentou a sobrevivência") (BIO-005).

### 6. Linguagem: as três proibições ficam sob teste, não sob boa vontade

`test_no_teleological_language` varre os `template` das regras causais (a prosa
que chega ao aluno, sem exceção), o código-fonte e os ADRs (com a distinção
**uso × menção** — citar a formulação errada para rejeitá-la é o oposto do
defeito, mesma técnica de `test_contextual_fitness_wording`).
`test_adaptation_vs_speciation_wording` exige a distinção do PED-003 onde ela
precisa estar. Ambas incluem contraprova do próprio filtro: sem ela, uma lista
negra errada passaria despercebida.

### 7. O que NÃO foi tocado

- **O códex do caminho B não foi reescrito.** Ele é a única ancestralidade "A→B"
  que resta no código, e continua dormente (ADR 0017 tempo 1). Reescrevê-lo seria
  implementar a camada de espécies, que o ADR 0024 colocou depois do M6. O que a
  Fase 0 fez foi **marcá-lo**, em `codex.py` e no ponto exato da escolha do
  ancestral, para que ninguém o tome pelo modelo vigente.
- **A dinâmica não mudou.** Nenhum sorteio novo, nenhuma leitura nova, nenhum
  parâmetro recalibrado. `test_determinism_after_envelope_change` compara a
  trilha **envelope a envelope** (e não só os `event_id`, que continuariam
  batendo mesmo com um `cause_detail` sorteado) e confere que a trajetória física
  não se moveu.
- **Nada do pós-M6.** Sem teias alimentares, sem relações ecológicas novas, sem
  ciclo do carbono, sem oxigênio, sem impactos antrópicos, sem Tutor.

## Alternativas consideradas

- **Emitir dois eventos, um por linhagem.** Rejeitado: a divisão é UM fenômeno, e
  dois eventos obrigariam o consumidor a reconstruir por correlação que eles são
  a mesma coisa — reintroduzindo a chance de lê-los como sequência (A, depois B).
- **Guardar identidade de linhagem através dos ticks.** Rejeitado nesta fase:
  exigiria estado no Engine e quebraria a pureza de que o replay depende
  (ADR 0016 §2). É a camada de espécies, e é pós-M6 (ADR 0024).
- **Calibrar `speciation_threshold` para o evento acontecer.** Rejeitado: muda a
  dinâmica no marco que corrige o envelope, e trata o sintoma. A correção é a
  mecânica gradual da Fase 2.
- **Remover `GENETIC_DIVERGENCE`.** Rejeitado: tornaria ilegível toda trilha já
  gravada, porque a desserialização recusa códigos desconhecidos — e recusar é o
  comportamento certo (`UnknownCauseCodeError`).

## Consequências

**Ganhamos.** O Tutor do M6 nasce sobre uma ancestralidade correta: o evento que
ele vai ler nomeia um ancestral e duas irmãs, e diz o que causou a divisão. A
especiação deixou de ser um fenômeno que a simulação registra e ninguém narra. As
três proibições de linguagem (teleologia, adaptação-como-especiação,
ancestralidade "A→B") estão sob teste e falham o build em vez de sobreviverem
como boa intenção.

**Perdemos.** O `cause_detail` da especiação engordou: 22 chaves, das quais 12 são
genoma redundante entre o ancestral e a linhagem A. Foi escolha consciente —
ambiguidade num contrato pedagógico custa mais do que bytes num evento raro.

**Aberto.** A mecânica gradual do BIO-002 (Fase 2), e com ela a raridade prática
do evento sob o limiar de produção. `GEOGRAPHIC_BARRIER` sem emissor até existir
geografia. A camada de espécies com identidade, decidida no ADR 0024 e
implementada depois do M6 — é ela que habilita `TUT-002` (contraste entre
espécies) e o `BIO-004` (filogenia visual).
