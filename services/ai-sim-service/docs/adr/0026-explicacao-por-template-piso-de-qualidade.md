# ADR 0026 — Explicação por template: o piso de qualidade que o LLM terá de superar

**Série:** serviço (`services/ai-sim-service/docs/adr/`).
**Status:** Aceito. Fecha a subetapa **M6.1**, ainda sem LLM.
**Relacionados:** ADR-ARCH-0002 (Correção 1 — a Visão Educacional é RENDERIZADA
pelo consumidor a partir de eventos neutros), ADR 0025 (fundação factual do
M6.0), ADR 0019 (extinção catastrófica × ecológica; aptidão CONTEXTUAL),
ADR 0023 (ancestral comum na especiação; planeta como escopo de armazenamento),
ADR 0024 (coortes: o Tutor fala da comunidade), ADR 0011 (feedback derivado do
Event Store), ADR 0002 (regras primeiro, LLM depois),
`docs/decisions/deferred.md`.

## Contexto

O M6.0 entregou o `FactualContext`: o dossiê neutro do que aconteceu, derivado só
do Event Store, determinístico e escopado por planeta. Ele não contém uma frase.

Falta o outro lado da Correção 1 do ADR-ARCH-0002, que está escrita desde o
começo do projeto e nunca tinha sido cumprida por inteiro: *"a frase educacional
é renderizada pelo Education/AI Tutor Engine"*. O Engine entrega o esqueleto
causal como dado; alguém precisa transformá-lo em português.

O M6.1 faz isso **por template**, e a razão de fazê-lo antes do LLM é o objetivo
declarado desta subetapa: estabelecer um **piso de qualidade**.

### Por que o piso vem antes do gerador

O M6.3 vai colocar um LLM neste caminho. Quando isso acontecer, a pergunta *"o
modelo está ajudando?"* precisa ter resposta — e ela só existe se houver um
ANTES contra o qual comparar. Sem piso, qualquer saída fluente pareceria
progresso, e um LLM que piorasse a explicação não teria como ser reprovado.

Há um efeito colateral que vale mais que o próprio piso: construir a explicação
por template é o teste mais duro que o dossiê do M6.0 podia receber. Se um
template consegue explicar corretamente uma extinção catastrófica, é porque o
dossiê carrega tudo de que a explicação precisa. Se não conseguisse, o buraco
estaria no M6.0 — e teria sido descoberto agora, com um template, e não daqui a
duas subetapas com um modelo no meio do caminho, onde a mesma falta apareceria
como "o LLM inventou".

### Um template também alucina

Não ter modelo generativo não é imunidade, e este é o mal-entendido que a
subetapa precisa desfazer. Um template que diga *"a espécie não conseguiu se
adaptar"* numa extinção catastrófica afirma algo que o dossiê **não contém**, e a
criança que o lê fica com a concepção equivocada exatamente como ficaria se um
modelo o tivesse escrito.

A diferença entre template e LLM é a facilidade de AUDITAR, não a existência do
risco. E é essa facilidade que o M6.1 cobra de si mesmo.

## Decisão

### 1. O explicador existente EVOLUIU; não nasceu um segundo

`ExplainFromEventsUseCase` existe desde o M1 e já traduzia evento em prosa. A
saída rápida era deixá-lo em paz e escrever um segundo explicador ao lado — e o
custo apareceria depois: duas prosas para a mesma trilha, duas correções a cada
revisão pedagógica, e uma delas esquecida.

Ele foi evoluído. Depois deste marco há **um** narrador de eventos.

O que ele fazia antes era propagar VARIÁVEIS. O evento virava
`Observation(variável, delta)`, e o motor de regras derivava `co2↑ ⇒
temperatura↑`, em busca em largura até a profundidade três. Duas consequências,
e a segunda é a que decidiu esta subetapa:

* **A identidade do evento se perdia.** `Observation` não sabe qual meteoro, qual
  tick, quais linhagens. A frase não tinha como nomear o que aconteceu.
* **Os saltos seguintes afirmavam efeitos que o log pode não conter.** A partir
  de `co2↑` o motor conclui `temperatura↑` sem conferir se houve
  `TemperatureShift` naquele planeta. Como ciência geral está certo; como
  narração daquela corrida é uma afirmação não derivável da trilha — que é a
  definição de alucinação adotada pelo M6.

Desde o M6.1 a narração vem do `ExplanationRenderer`: um fato por evento, slots
preenchidos com campos do dossiê, e a atribuição causal saindo do `causation_id`
REAL.

### 2. O motor de regras continua vivo, no lugar em que projetar é o serviço

Evoluir o narrador não é aposentar o motor de regras, e confundir as duas coisas
teria quebrado um endpoint que nada tem a ver com narrar eventos.

| Caminho | Entrada | Modo | Motor |
| --- | --- | --- | --- |
| `/ai/explain` | observações do cliente | PROJEÇÃO ("o que decorre disto") | regras |
| recuo do `AdvanceEraUseCase` | delta agregado de estado | PROJEÇÃO | regras |
| narração de era/fatia | trilha de eventos | NARRAÇÃO ("o que aconteceu") | templates |

Em `/ai/explain` não existe trilha: o cliente manda observações, e projetar para
a frente é exatamente o que se pede. O recuo por delta agregado só ocorre quando
não houve evento algum a narrar (ADR 0011) — também não é narração de trilha.

Nenhum dos dois é um segundo narrador de eventos, e
`test_single_explainer_after_integration` guarda a distinção pelos dois lados:
que a narração seja uma só, e que a projeção continue existindo.

### 3. Os templates são DADO versionado, não prosa espalhada pelo código

`configs/explanation_templates.yaml`, ao lado de `causal_rules.yaml` e pela mesma
razão: a frase que chega ao aluno é objeto de revisão PEDAGÓGICA, não de
refatoração. Quem entende de ensino corrige uma palavra sem abrir um módulo
Python, e sem arrastar a lógica de seleção junto.

O arquivo separa três coisas, e a separação importa:

* **`nouns`** — como um `event_type` se chama em português;
* **`mechanisms`** — como um `cause_code` vira oração causal. É aqui, e em
  nenhum lugar antes, que o enum neutro do Engine encontra a prosa;
* **`templates`** — a frase, com slots.

Nenhum dos três decide O QUE aconteceu: isso já está decidido no dossiê. Eles
decidem apenas COMO se conta.

### 4. Ancoragem: toda afirmação aponta para um campo do dossiê

Cada fato renderizado carrega um `Grounding` — o `event_id` de onde saiu e os
campos que preencheram seus slots. `test_every_claim_is_grounded_in_context`
verifica quatro coisas, e nenhuma delas depende de alguém achar que a frase está
boa:

1. todo fato aponta para um evento que está no dossiê;
2. todo campo declarado resolve de fato (nada de campo decorativo — a família do
   `planet_id` fantasma do M5);
3. todo número da frase veio de um slot, e todo slot veio de valor derivável do
   dossiê;
4. o `summary` é EXATAMENTE a junção dos fatos.

O item 4 fecha a porta mais provável de um renderizador. Um resumo que
SINTETIZASSE teria de afirmar algo que nenhum fato isolado afirma ("a era foi
turbulenta"), e esse algo não teria origem no dossiê. A junção literal é
deliberadamente burra.

### 5. A especiação é inexprimível como "A deu origem a B" — por FORMA

O M6.0 travou a garantia no tipo. O M6.1 fecha o último trecho, que é onde ela
ainda podia se perder: alguém escreve um template correto na estrutura e errado
na frase, e a ancestralidade chega ao aluno invertida.

A defesa não é uma lista de frases proibidas — embora ela exista e seja herdada
da Fase 0. É estrutural: **o template de especiação não recebe linhagem alguma
como slot**. A frase "A deu origem a B" precisaria de dois sujeitos nomeados, e
não há onde recebê-los. Uma lista negra protege contra o que alguém lembrou de
proibir; a ausência de slot protege contra o que ninguém lembrou.

Os três identificadores continuam no `Grounding`, para quem audita. Um UUID no
meio da frase não ensina nada à criança, e o modelo é de COMUNIDADE — identidade
de espécie é camada pós-M6 (ADR 0024).

### 6. Vocabulário reusado da Fase 0, e não redefinido

As três regras de linguagem (BIO-005 anti-teleologia, PED-003 adaptação ×
especiação, BIO-001 ancestral comum) e a formulação de aptidão CONTEXTUAL (Q5)
valem para a prosa nova. O que **não** aconteceu foi copiá-las para perto dos
templates novos: a guarda da Fase 0 (`test_no_teleological_language`) foi
ESTENDIDA para ler os dois arquivos de prosa.

O motivo é operacional. Duas listas negras divergiriam, e a que envelhecesse
seria justamente aquela que alguém consultaria ao escrever a frase seguinte,
porque estaria ao lado do template que está editando.
`test_non_teleological_wording_preserved` afirma que a guarda antiga realmente
ALCANÇA o arquivo novo — cobertura verificada, não suposta.

### 7. Cobertura de `cause_code`: frase ou silêncio DECLARADO

Todo `cause_code` que algum Engine declara tem oração de mecanismo, ou está em
`not_narrated` com a razão registrada. Um código sem nenhum dos dois reprova o
teste, nomeando o código.

É a lição do `solar_flux` do M2 aplicada à prosa. Um código sem frase não estoura
nada: o narrador pula o evento, e o aluno lê uma era em que aquele acontecimento
não existiu. O sintoma é ausência, e ausência não se denuncia sozinha.

Os cinco códigos silenciados são da moldura (fecham tick e era, ou relatam
estouro de orçamento). Narrar "o motor excedeu o tempo previsto" a uma criança
confundiria o funcionamento do simulador com o que aconteceu no mundo que ela
estuda.

### 8. Registro de leitura: a costura decidida, não o sistema construído

`Register` tem dois valores — `STANDARD` e `SIMPLE` — e o `SIMPLE` existe hoje
apenas para os três fatos de maior risco pedagógico: as duas famílias de extinção
e a especiação. São aqueles em que uma frase longa demais faz o aluno perder a
lição.

Quando um template não tem variante no registro pedido, o renderizador **cai para
`STANDARD`**, e o fato declara o registro REALMENTE usado. Três consequências
buscadas:

* o M6.3 acrescenta registros linha a linha no YAML, sem tocar em assinatura;
* nenhum template precisa ganhar todas as variantes de uma vez para o registro
  novo existir;
* não se improvisa simplificação em tempo de execução — uma frase padrão correta
  é melhor que uma simplificada na hora, e é na hora que a frase erra.

**O que NÃO foi construído:** diferenciação por faixa etária de verdade, perfil de
aluno, adaptação de vocabulário por série. Isso é produto, depende do M6.2 e do
M6.3, e construí-lo agora fixaria decisões pedagógicas que ninguém tomou.

### 9. O que é narrado uma vez por ocorrência, e o que é agrupado

Uma era real produz centenas de eventos. Enfileirar uma frase por evento não é
explicação — é despejo. Mas resumir "houve muita atividade vulcânica" seria
afirmar uma avaliação que o dossiê não contém.

A saída é contar o que o dossiê SABE contar:

* **Marcos** (extinção, especiação, surgimento da vida) — um a um. São raros e
  cada ocorrência muda o estado qualitativo do planeta.
* **Processos recorrentes** (temperatura, vulcanismo, química, capacidade,
  deslocamento de traço, perdas PARCIAIS de população) — uma ocorrência, com a
  contagem. A contagem é derivada do dossiê, então "isso se repetiu 80 vezes" é
  tão ancorado quanto a primeira frase.

**A divisão saiu de medição, não de intuição, e a primeira versão estava errada.**
Mortandade em massa parece marco e não é: numa corrida de 400 ticks com meteoro
há 9 extinções, 7 especiações e 10 surgimentos de vida — mas **257 mortandades**
e 130 deslocamentos de traço, porque a comunidade perde população em ticks
consecutivos enquanto o ambiente aperta. A versão inicial classificou mortandade
como marco e produziu 300 parágrafos quase idênticos. O roteiro de fumaça contra
uma corrida real foi quem mostrou; com a correção, a mesma corrida rende 37
frases.

A ocorrência escolhida para falar pelo grupo é a primeira **que tem causa
registrada**, e não a primeira de todas. A diferença não é cosmética: numa corrida
vulcânica a primeira `TemperatureShift` costuma ser raiz, enquanto as seguintes
decorrem do acúmulo de gás carbônico — escolher cegamente a primeira apagaria a
cadeia vulcanismo → carbono → temperatura da narração, que é o elo mais
pedagógico da fatia vertical.

### 10. A fatia sem nada a narrar

Frase curta e neutra: *"Neste período o planeta seguiu sem acontecimentos
notáveis."* Sem drama fabricado e sem pedido de desculpas.

A especiação é praticamente inalcançável até a Fase 2 (~6 σ; medido: zero
especiações em 200 ticks nas sementes 2027 e 99 —
`docs/decisions/deferred.md`), então uma era sem linhagem nova é o caso COMUM. A
ausência não vira frase: dizer "nenhuma espécie nova surgiu" a cada era ensinaria
que a especiação é o padrão de que este planeta está desviando, quando é o
contrário. E "infelizmente não há muito a explicar" transformaria o normal em
falha, mandando quem for avaliar o Tutor caçar um defeito que não existe.

### 11. `Direction.NONE`

O `CausalStep` do contrato de saída nasceu para propagação de variáveis e tem um
campo de direção. Uma narração por evento nem sempre mede grandeza que sobe ou
desce — uma especiação não é aumento de nada.

Antes, o único jeito de preencher o campo seria escolher `UP` por convenção. Uma
direção escolhida por convenção é uma afirmação sem origem no Event Store
chegando à resposta da API como se fosse dado — a alucinação que este marco
existe para impedir, sem nenhum LLM envolvido. `NONE` é a ausência de afirmação
direcional, dita explicitamente.

## O que este marco NÃO faz

* **Nenhum LLM, embedding ou RAG.** M6.2/M6.3. O contrato de import-linter passou
  a cobrir o caminho INTEIRO de evento até prosa — inclusive
  `application.feedback`, que é o caminho mais curto para um gerador entrar sem
  ninguém notar.
* **Nenhum sistema de diferenciação etária.** Só a costura (seção 8).
* **Nenhuma camada de identidade de espécie.** Pós-M6 (ADR 0024).
* **Nenhuma mudança no contrato de leitura do M6.0.** Os templates consomem o que
  o dossiê já carrega; nenhum precisou de campo novo — que é, em si, a evidência
  de que o M6.0 acertou o escopo.

## Dois testes que mudaram, e por quê

Evoluir o narrador tinha de mexer em duas asserções existentes. As duas afirmavam
`rule_id` do motor de regras no caminho de EVENTOS; a propriedade de produto foi
preservada e, num dos casos, fortalecida.

* `test_the_narrated_chain_covers_the_vertical_slice` afirmava `R-VOLC-CO2` e
  `R-CO2-TEMP`. Esses ids vinham da projeção por regras, que conclui
  `temperatura↑` sem conferir se houve `TemperatureShift` — a asserção passava
  mesmo que o planeta não tivesse encadeado nada. Agora afirma os pares
  (causa, efeito) reconstruídos do `causation_id` real: se o planeta não
  encadeou, o teste falha, que é o que se quer de um teste de cadeia. A cobertura
  da projeção não se perdeu — mudou para o caminho de observações, onde o motor
  de regras de fato vive.
* `test_causal_explanation_mentions_emergent_biology` afirmava regras biológicas
  no rastro; passou a afirmar os templates biológicos. A promessa verificada é a
  mesma: uma era não pode ser narrada só como física.

## Alternativas consideradas

* **Escrever um segundo explicador ao lado do antigo.** Rejeitada: duas prosas
  para a mesma trilha, e a divergência apareceria como duas explicações
  diferentes do mesmo acontecimento — sem que nada acusasse qual é a válida.
* **Manter o motor de regras narrando eventos e só melhorar os templates dele.**
  Rejeitada: as regras casam por VARIÁVEL, e a variável descarta a identidade do
  evento. Nenhuma redação recupera o meteoro que a `Observation` jogou fora.
* **Restringir o motor de regras a só emitir passos cujo efeito esteja no
  dossiê.** Não rejeitada por princípio, e sim por custo/risco: manteria os
  `rule_id` antigos, mas exigiria dois modos no mesmo motor (um para
  `/ai/explain`, outro para narração) e tornaria a asserção da fatia vertical
  dependente de qual evento aquela corrida produziu. A narração por template
  chega ao mesmo lugar com uma fronteira mais simples.
* **Um resumo que sintetizasse os fatos.** Rejeitada: é a alucinação mais provável
  de um renderizador, e a junção literal a torna impossível.
* **Registro único.** Rejeitada: o M6.3 teria de fazer retrofit da costura no
  mesmo marco em que introduz o gerador — dois riscos juntos.
* **Registro por faixa etária completo.** Rejeitada: fixaria decisões pedagógicas
  que dependem do M6.2 e do M6.3.

## Consequências

**Ganhamos.** Existe uma explicação correta, determinística e auditável frase a
frase, produzida sem nenhum modelo. O dossiê do M6.0 foi validado pelo uso: todos
os templates couberam nos campos que ele já carregava. A distinção catastrófica ×
ecológica e o ancestral comum atravessaram até a prosa, travados na FORMA e não
na disciplina de quem escreve. E o M6.3 nasce com um alvo mensurável.

**Perdemos.** Mais um arquivo de prosa versionada a manter em dia (mitigado pela
guarda compartilhada), e um agrupamento de recorrências que é decisão editorial
dentro do renderizador — defensável, testada, e ainda assim uma decisão que
alguém pode querer diferente. A narração também ficou mais VERBOSA que a antiga
em eras movimentadas: 37 frases contra o punhado que a projeção por regras
produzia, porque agora cada acontecimento real é narrado em vez de alguns poucos
saltos de variável.

**Fica em aberto.** Quantas frases uma era deve render é pergunta de produto, e a
resposta atual (marcos individuais + processos agrupados) é a mais defensável sem
um professor na sala. O M6.2 e o M6.3 provavelmente vão querer selecionar e
ordenar por relevância pedagógica — e aí a decisão terá insumo para ser tomada.
