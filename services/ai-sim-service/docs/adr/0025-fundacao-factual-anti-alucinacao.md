# ADR 0025 — A fundação factual anti-alucinação: o Event Store como verdade do Tutor

**Série:** serviço (`services/ai-sim-service/docs/adr/`).
**Status:** Aceito. Abre o M6 pela subetapa **M6.0**, sem LLM.
**Relacionados:** ADR-ARCH-0002 (observabilidade por design; três públicos, três
projeções; a Visão Educacional é RENDERIZADA pelo consumidor), Spec §1 (camada de
consumidores), §2 (regra de ouro), §4 (envelope de evento), §8 (M6 — consumidores),
Dossiê PD&I v3 §10.5, ADR 0019 (extinção catastrófica × ecológica), ADR 0021
(Event Store persistente e contrato de query), ADR 0022 (quatro pilares e
projeções), ADR 0023 (planeta é dimensão de armazenamento; ancestral comum na
especiação), ADR 0024 (coortes: comunidade **e** espécies), `docs/decisions/deferred.md`.

## Contexto

O M6 introduz um LLM, e com ele um tipo de defeito que nenhum marco anterior
tinha: **não determinístico, sem invariante de correção, e que falha de um jeito
que nenhum `assert` pega**. Um planeta que perde massa quebra um teste de
conservação. Um Tutor que narra uma extinção que não aconteceu não quebra nada —
soa bem, cita números plausíveis e é aceito.

Por isso o M6 é executado em subetapas, e o LLM entra o mais tarde possível,
sobre a base factual mais sólida que se conseguir montar antes dele. Esta é a
primeira: **o dossiê do que de fato aconteceu**.

### O princípio que vale para o M6 inteiro

> A verdade sobre o planeta do aluno é o **Event Store**. Um consumidor está
> **correto** quando o que ele afirma é DERIVÁVEL da trilha de eventos, e
> **alucina** quando não é.

Toda a arquitetura de observabilidade já apontava para cá: o ADR-ARCH-0002 fez da
explicabilidade um **requisito de esquema** justamente para que o Tutor
explicasse o fenômeno **sem recalcular ciência** e **sem inspecionar memória de
Engine**. O que faltava era o consumidor que transforma essa trilha em matéria
consumível — e que o faça sem, ele próprio, começar a inventar.

## Decisão

### 1. Um dossiê FACTUAL, neutro, entre o Event Store e qualquer narrador

Entra o `FactualContext` (`domain/consumers/`): dado um planeta e um recorte, ele
é o **dossiê estruturado do que aconteceu**. Contém a linha do tempo ordenada com
os campos de explicabilidade da Spec §4 íntegros, as cadeias causais reconstruídas
nas duas direções, os fatos de especiação e de extinção, e os marcadores de era.

E **não contém**: nem uma frase, nem um `cause_code` traduzido, nem faixa etária,
nem escolha de registro, nem material da BNCC. A regra é dura porque é ela que
sustenta a definição de correção acima: a partir do momento em que o dossiê narra,
a fronteira entre *"o que aconteceu"* e *"como se conta"* desaparece — e com ela
desaparece o único critério que separa o Tutor certo do Tutor que inventa.

A tradução é do consumidor de CIMA. É a Correção 1 do ADR-ARCH-0002 aplicada mais
uma vez, agora um andar acima: o Engine entrega o esqueleto causal como dado, o
M6.0 o organiza como dado, e a prosa é do M6.1 (template) e do M6.3 (LLM).

### 2. As subetapas seguintes REESCREVEM o dossiê; nenhuma decide o que aconteceu

É a hierarquia de ancoragem do M6, e ela nasce aqui:

| Subetapa | O que acrescenta | O que NÃO pode fazer |
| --- | --- | --- |
| **M6.0** (esta) | o fato verificável | narrar |
| M6.1 | frase por template — o **piso de qualidade** que o LLM terá de bater | inventar fato |
| M6.2 | RAG pedagógico sobre material BNCC | inventar fato |
| M6.3 | LLM (Ollama) reescreve | decidir o que aconteceu |
| M6.4 | avaliação adversarial + guardrails | — |

O fato do Event Store é **inviolável**; o RAG informa registro e linguagem; o LLM
**reescreve, não decide**. O M6.0 existe para que essa hierarquia tenha um chão.

### 3. Especiação é ancestral comum **por construção do tipo**, não por convenção

`SpeciationFact` tem um ancestral e **duas** linhagens irmãs, e um `__post_init__`
que recusa qualquer outra forma — inclusive a disfarçada, em que o ancestral
reaparece como uma das linhagens resultantes ("ancestral A, linhagens A e B"),
que é como "A→B" se esconde dentro do vocabulário certo.

A Fase 0 corrigiu o SIGNIFICADO do evento (BIO-001, ADR 0023) antes de o Tutor
existir. Este ADR fecha o outro lado: a estrutura que o M6.1 e o M6.3 vão receber
**não consegue** representar uma progenitora viva. A distinção não é de redação —
no modelo "A→B" a espécie que continua existindo aparece como progenitora da
outra, e o aluno conclui que B é "mais evoluída" que A, que é exatamente a escada
de progresso que a plataforma existe para desfazer.

Uma `SpeciationOccurred` malformada **falha alto** (`MalformedSpeciationError`)
em vez de degradar. As duas degradações possíveis são piores que o erro: pular o
evento emudece o Tutor sobre uma especiação que ocorreu; aceitá-lo com uma
linhagem só o faz narrar ancestralidade errada com autoridade.

### 4. Especiação RARA é normal, e a ausência é um fato

Até a Fase 2 a especiação é praticamente inalcançável: o limiar vale 0,12 e um
passo de mutação anda ~0,02 — ~6 σ num tick. Medido: zero especiações em 200
ticks nas sementes 2027 e 99 (`docs/decisions/deferred.md`).

O dossiê trata **fatia vazia como fato, nunca como erro**, e um dossiê vazio ainda
diz de qual planeta e de qual recorte ele fala — é o que distingue *"nada
aconteceu na era 4"* de *"ninguém perguntou pela era 4"*. Tratar a ausência como
falha transformaria o caso comum em exceção e mandaria quem for avaliar o Tutor
caçar um defeito de prompt ou de RAG que não existe.

### 5. A cadeia causal passa a ser navegável nas DUAS direções

O lado de leitura já sabia **subir**: `walk_causal_chain` (contrato de query do
M5) vai do efeito à raiz e responde *"por que isto aconteceu?"*. O M6.0 acrescenta
a **descida** — `build_causal_forest` / `descendants_of` —, que responde *"e daí o
que aconteceu?"*, a pergunta de quem vai narrar em ordem cronológica.

Descer não é subir ao contrário, e a diferença é estrutural: cada evento tem no
máximo UMA causa, então subir é uma lista; um mesmo meteoro causa resfriamento,
incêndio e extinção, então descer é uma **árvore**. Uma travessia descendente
implementada como "a lista da subida invertida" entregaria um ramo só, e o Tutor
narraria a cascata do meteoro citando um efeito como se fosse todo o resultado.

Isto é o espelho, no lado da LEITURA, do defeito que o M4 encontrou no lado da
escrita: lá, uma extinção catastrófica encadeava ao `TemperatureShift` do mesmo
tick em vez de ao meteoro (ADR 0019, decisão 4). Por isso os testes **andam** a
cadeia pelo `causation_id` e afirmam a ÁRVORE — coocorrência num mesmo tick não
prova elo nenhum.

### 6. A distinção catastrófica × ecológica atravessa como DADO

`ExtinctionNature` classifica a extinção pela FAMÍLIA da causa (ADR 0019):
`CATASTROPHIC_EVENT` é a única independente de aptidão; todo o resto é ecológico.
O `cause_code` original viaja intacto ao lado, então um mecanismo ecológico novo
não é achatado — o que o M6.0 classifica é a família, não o mecanismo.

Classificar não é traduzir. Uma classificação o consumidor de cima traduz como
quiser, para a idade que quiser; uma frase já teria decidido por ele. Perder a
distinção devolveria o Tutor a narrar toda extinção como falha de adaptação, que é
a concepção equivocada que o M4 existiu para desfazer.

### 7. O recorte é por planeta, sempre, pelo caminho da persistência

O `ContextAssembler` consome `EventStoreQuery` com `planet_id` como primeiro
parâmetro, sem default (ADR 0023). O planeta **não** entra no `EventQuery`: ele é
dimensão de armazenamento, não predicado sobre o fato.

É a fronteira mais crítica deste marco. Um recorte que não recorta entrega ao
Tutor a trilha de dois planetas parecendo escopada, e ele narra ao aluno — com
total confiança, citando eventos REAIS — a catástrofe do planeta de OUTRO aluno.
Toda afirmação seria derivável de um event log; só não do dele. Nenhuma avaliação
adversarial do M6.4 pegaria isso, porque a resposta estaria **ancorada**. Apenas na
trilha errada. `test_context_scoped_to_single_planet` é adversarial: dois planetas,
a mesma semente, identificadores que colidem byte a byte, e uma marca em
`cause_detail` que permite afirmar que veio o evento do planeta CERTO — e não
apenas a quantidade certa.

### 8. O grão é a COMUNIDADE, e o encaixe da camada de espécies fica MARCADO

O ADR 0024 decidiu comunidade **e** espécies, com a camada de identidade adiada
para depois do M6. O dossiê é construído sobre o modelo de comunidade, e o ponto
de encaixe está marcado no código (`SpeciationFact.lineages`,
`ExtinctionFact.participants`): hoje esses campos carregam identificadores de
linhagem e papéis; quando a camada de coortes existir, passam a carregar
identidades de espécie **sem que o formato do dossiê mude**. O que muda é a
montante. A camada **não** é implementada aqui.

### 9. Onde a camada de consumidores vive neste serviço

A Spec §1 desenha os consumidores como `consumers/analytics|education|ai_tutor`.
Este serviço os acomoda na estratificação hexagonal que ele de fato usa e que o
`import-linter` verifica — `domain/consumers/` (modelo puro) e
`application/consumers/` (caso de uso) —, do mesmo modo que já fez com
`platform/persistence` (aqui `infrastructure/persistence`) e com o explicador de
regras (`domain/feedback` + `application/feedback`).

Um pacote `consumers/` no topo seria uma segunda hierarquia com as mesmas
responsabilidades, fora dos contratos de camada. O que a Spec pede é a
**fronteira**, e a fronteira está declarada em `pyproject.toml`, não no nome do
diretório.

### 10. Duas fronteiras barradas por ferramenta

* **`Consumidores read-side so alcancam o Event Store`** — a metade da regra de
  ouro da Spec §2 que o M5 ainda não tinha barrado. Sem ela, o caminho mais curto
  para o dossiê responder uma pergunta difícil é espiar o world-state ou chamar um
  Engine — e aí ele deixa de ser derivável do event log, que é a única definição de
  correção que o M6 tem.
* **`A fundacao factual do M6.0 nao depende de LLM nem de RAG`** — fronteira de
  SUBETAPA. Enquanto a subetapa for esta, uma dependência de Ollama, de embeddings
  ou de RAG é regressão de escopo, e o contrato a nomeia em vez de confiar na
  memória de quem revisa o PR.

## O que este marco NÃO faz

Nenhuma destas ausências é esquecimento:

* **Nenhum LLM, embedding ou RAG.** M6.2/M6.3, barrado por contrato e por teste.
* **Nenhum template de explicação.** M6.1 — o `ExplainFromEventsUseCase` existente
  passa a ser CONSUMIDOR do `FactualContext`, e essa ligação é do M6.1, não desta
  subetapa. Nada foi dobrado dentro dele aqui.
* **Nenhuma tradução de `cause_code`**, nenhuma decisão de faixa etária, nenhum
  material da BNCC.
* **Nenhuma camada de identidade de espécie** (pós-M6, ADR 0024).
* **Nenhuma alteração em Engine, world-state ou Event Store.** M6.0 é leitura.

### O endpoint HTTP ficou de fora, e a razão é a dívida declarada no ADR 0023

O recorte previa um endpoint read-only opcional devolvendo o dossiê em JSON. Ele
**não entrou**, e isto é decisão, não corte por tempo.

O Event Store do processo (`InMemoryEventStore`, injetado como sink de
observabilidade) é uma lista única, **não escopada por planeta**, e não implementa
`EventStoreQuery`. Servir um endpoint a partir dele reintroduziria exatamente o
vazamento entre planetas que o ADR 0023 corrigiu — e reintroduzi-lo na FUNDAÇÃO
anti-alucinação seria o pior lugar possível.

Ligá-lo honestamente exige o rewire que o ADR 0023 deixou declarado: `advance_era`
e `evolve_biology` ainda gravam pelo caminho `EventLogEntry` do M2, e o
`PostgresEventStore` só é alimentado por quem o chama explicitamente. Esse rewire
**escreve** no caminho da simulação, o que está fora da fronteira "M6.0 é leitura".

Fica registrado como o próximo passo natural, e o `FactualContext.to_dict()` já
entrega o JSON — hoje inspecionável por `scripts/smoke_m6_0.py`, e pronto para a
rota no dia em que houver um Event Store escopado atrás dela.

## Alternativas consideradas

* **Estender o `ExplainFromEventsUseCase` em vez de criar o dossiê.** Rejeitada: ele
  já traduz evento em observação e produz frase. Pendurar o fato dentro do narrador
  mistura de novo as duas responsabilidades que o ADR-ARCH-0002 separou — e o M6.1
  precisa que o narrador seja SUBSTITUÍVEL sobre um fato estável, que é o teste de
  cuja comparação o M6.3 depende.
* **Remodelar o evento num tipo próprio do dossiê.** Rejeitada: duas cópias do
  envelope §4 divergiriam, e a cópia empobrecida obrigaria o narrador a completar de
  memória — a definição operacional de alucinar. O dossiê carrega o `DomainEvent`.
* **Importar o vocabulário de evento dos Engines.** Rejeitada: trocaria duplicação
  por acoplamento, contra a Spec §2. O consumidor repete as constantes e um teste
  (`test_consumer_vocabulary_matches_engines`) exige igualdade termo a termo — a
  mesma escolha que `configs/event_observations.yaml` já fez.
* **Tolerar especiação malformada, pulando o evento.** Rejeitada: o sintoma seria
  ausência, e ausência não se denuncia sozinha — é a mesma classe de defeito do
  `solar_flux` do M2 e do `planet_id` fantasma do M5.

## Consequências

**Ganhamos.** O M6 tem chão: existe uma fonte de verdade consumível, determinística
e escopada por planeta, sobre a qual o template e o LLM só reescrevem. A cadeia
causal ficou navegável nas duas direções. A distinção catastrófica × ecológica e o
ancestral comum atravessam a fronteira travados no TIPO, e não na disciplina de
quem escrever o prompt. E a avaliação adversarial do M6.4 ganha uma entrada
estável — sem isso, toda diferença de saída do Tutor seria ruído inconclusivo.

**Perdemos.** Mais uma camada entre o Event Store e a frase, e um vocabulário
duplicado que só um teste mantém em dia. O recorte por evento lê a trilha do
planeta inteira antes de recortar — mesmo preço consciente que o ADR 0023 já
aceitou para não ter duas cópias do predicado.

**Fica em aberto.** O rewire do escritor do envelope §4 no laço da simulação
(dívida do ADR 0023), sem o qual não há endpoint honesto; e a ligação do
`ExplainFromEventsUseCase` como consumidor do dossiê, que é o M6.1.
