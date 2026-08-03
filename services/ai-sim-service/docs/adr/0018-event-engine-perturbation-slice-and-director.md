# ADR 0018 — Event Engine: perturbação por fatia própria, e o Diretor determinístico

## Status
Aceito. Abre o M4. Depende do **ADR 0016** (fatias da biota) e do **ADR 0012**
(ciclos fechados). Referências: Dossiê v3 §10.4/§10.5, GDD §10 (IA como Mestre),
RF-019/020 (eventos telegrafados), RF-023 (replay), Spec §3/§4/§5.3/§6/§7,
ADR-ARCH-0001, ADR-ARCH-0002.

## Contexto

O M4 acrescenta os eventos extraordinários — meteoro, seca, incêndio, era
glacial, tempestade, supervulcanismo — e o Diretor que decide quando eles
acontecem.

O problema central não é modelar um meteoro. É que **um evento perturba
grandezas cujas fatias já têm dono**: o meteoro esfria (clima), a seca reduz
precipitação (hidrologia), o supervulcão injeta carbono (geologia). A moldura
admite **um escritor por fatia** (Spec §3), e `validate_graph` recusa um segundo
no boot. O Event Engine, portanto, não pode aplicar a perturbação onde ela cai.

## Decisão

### 1. A perturbação viaja pelo Canal A, numa fatia PRÓPRIA

O Event Engine é dono da `EventSlice` e publica ali a perturbação como
**escalar**. Cada Engine afetado **lê** esse escalar e o incorpora à própria
dinâmica, na própria fatia. O Event Engine descreve a CAUSA; quem decide o
EFEITO é quem detém a grandeza.

Isso mantém três coisas de pé ao mesmo tempo:

1. **um dono por fatia**, verificado no boot;
2. **a perturbação no Canal A** — float, aditivo, replayável. O Canal B narra a
   OCORRÊNCIA (`MeteorImpact`); o Canal A carrega a CONSEQUÊNCIA física contínua.
   Trocar isso — mandar a perturbação pelo Canal B e fazer os Engines lerem
   eventos — obrigaria cada Engine a interpretar o catálogo de eventos, e o
   acoplamento que a moldura evita voltaria por dentro;
3. **nenhum Engine lendo o estado interno de outro**.

`WORLD_STATE_VERSION` sobe 3 → 4. Checkpoints da versão 3 leem com a `EventSlice`
zerada — o mundo sem perturbação ativa, que é degradação correta e não silenciosa.

**Perturbação é estoque que decai, não pulso.** Um meteoro não esfria o planeta
num tick e pronto: injeta poeira que permanece e decai. Um pulso instantâneo
produziria um degrau na temperatura e nenhum inverno de impacto — que é o
fenômeno a ensinar. Cada evento declara duração e perfil de decaimento; os
Engines afetados leem a intensidade CORRENTE e não sabem qual evento a produziu,
o que os mantém ignorantes do catálogo.

**O bookkeeping mora na fatia.** Qual evento está ativo, há quantos ticks e com
que severidade são estado — e ficam na `EventSlice`, não num atributo do Engine.
`tick()` tem de ser função pura do snapshot ou o replay bit-a-bit para de
funcionar (Spec §7). É o mesmo motivo pelo qual a Evolution carrega o genoma
médio na fatia em vez de guardar a lista de espécies (ADR 0016).

### 2. `event` fecha o tick; quem o lê, lê DEFASADO

A Spec §5.3 lista `event` por último, e mantivemos. O Diretor observa o mundo JÁ
RESOLVIDO deste tick para decidir se um evento cabe no contexto — leituras do
mesmo tick, sem defasagem, porque clima, recurso e biota correm todos antes dele.

A defasagem está do outro lado: a perturbação escrita no tick N é lida no tick
N+1, e os cinco Engines afetados declaram `SliceRef.EVENT` em `lagged_reads`. É a
mesma disciplina de água↔clima (M2) e biomassa (M3), e `validate_graph` recusa a
leitura para trás não declarada.

Nenhum efeito exigiu aplicação no mesmo tick, então não houve reordenação nem
ciclo síncrono.

### 3. Fronteira vulcanismo BASAL × supervulcanismo, por POSSE ÚNICA

A Geology (M1) já desgaseifica CO₂ do vulcanismo contínuo. O supervulcanismo é
extraordinário, mas o carbono que injeta continua sendo carbono VULCÂNICO — e
quem detém o fluxo vulcânico é a Geology.

Então o Event Engine publica só a **intensidade**, e a Geology a incorpora ao
próprio `outgassing`. Existe UM fluxo de carbono vulcânico no mundo, e a
atmosfera segue lendo UM termo.

A alternativa — o Event publicar um pulso de CO₂ que a atmosfera somasse ao lado
de `geology.co2_flux` — criaria duas entradas, e a ausência de dupla contagem
passaria a depender de disciplina em vez de estrutura. **O M2 já pagou esse
preço uma vez.** Com posse única, a dupla contagem é impossível por construção:
não existe onde publicar o segundo fluxo, e o teste que verifica isso confere que
a `EventSlice` não tem campo de carbono algum.

### 4. O Diretor é determinístico e PURO — e não aprende

O Diretor é função de `(world-state, RNG semeado)`. Ele **não lê logs, métricas
nem o Event Store**.

A tentação é evidente: "agendar uma seca porque o aluno vem prosperando há muitas
eras" pede o histórico. É exatamente o que a moldura proíbe — a observabilidade é
LATERAL e não realimenta a simulação (ADR-ARCH-0002). Um Diretor que lesse a
trilha tornaria o replay impossível a partir de `(seed, checkpoint)`, porque a
trilha é EFEITO da execução, não entrada dela.

O que ele PODE ler é o world-state, que é entrada legítima e replayável. É o
bastante para **recusar o absurdo**: era glacial num planeta a 45 °C não ensina
nada — ensina que o simulador sorteia. Isso não é roteiro: o Diretor não escolhe
o evento "certo" para a lição, apenas descarta o incoerente e sorteia entre o que
resta, com pesos versionados.

**SEM RL, e a ausência é decisão.** Um agente treinado seria estatal e dependeria
de histórico — as duas coisas que a pureza acima recusa. Introduzi-lo exige antes
decidir onde o estado do agente vive e como o replay o reconstrói; não é
extensão, é outro desenho. Fica adiado explicitamente.

### 5. Os eventos são TELEGRAFADOS (RF-019/020)

O evento é agendado com antecedência, anunciado por `EventForecast` no Canal B e
exposto na `EventSlice` para a API avisar o jogador. Um evento que chega sem
aviso não ensina antecipação — ensina azar.

O horizonte é por evento, não constante: a era glacial é lenta e muito anunciada;
o incêndio quase não avisa. É parâmetro versionado.

### 6. `consequences` é PROJETADO, nunca declarado na emissão

O `MeteorImpact` não declara `consequences=["extinction"]`. Ele pode cair num
planeta sem vida, ou não matar ninguém — declarar seria profetizar. A relação
causa→efeito é derivada do Event Store DEPOIS do fato, invertendo os
`causation_id` (ADR-ARCH-0002). O envelope carrega `cause_detail`, que é o que o
consumidor precisa para descobrir sozinho.

## Consequências

**Ganhamos.** O aluno vê o meteoro chegar, escolhe o que fazer, e a consequência
física emerge da mesma composição de Engines que já rodava — sem que nenhum deles
saiba que existe um catálogo de eventos.

**Perdemos.** Uma perturbação nova exige um campo novo na `EventSlice` e uma
leitura no Engine afetado. É mais cerimônia do que deixar o Event escrever onde
quisesse — e é precisamente a cerimônia que impede a dupla escrita.

**Aberto.** A linha de base física do planeta NÃO converge em horizonte longo
(ver ADR 0019, "o pino de CO₂"), e isso precede o M4.
