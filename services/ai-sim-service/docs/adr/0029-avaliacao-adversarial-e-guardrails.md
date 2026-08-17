# ADR 0029 — Avaliação adversarial: fechar a lacuna, medir com honestidade

**Status:** aceito
**Marco:** M6.4 — e o fechamento do arco M6
**Relacionados:** ADR 0025 (M6.0) · ADR 0026 (M6.1) · ADR 0027 (M6.2 e o adendo do
embedder) · ADR 0028 (M6.3, e as lacunas que este ADR fecha) · ADR 0019
(catastrófica × ecológica) · ADR 0023 (BIO-001) · ADR 0021/0022 (Event Store, LGPD)

## Contexto

Este é o marco que substitui, para a camada de geração, o que os marcos físicos
tinham. Lá, correção era "a mesma entrada produz a mesma saída", verificável por
igualdade. Aqui correção é outra coisa:

> O sistema se comporta bem sob tentativa deliberada de quebrá-lo, e a taxa de
> falha é **honestamente mensurável**.

A segunda metade acabou dando mais trabalho que a primeira, e é onde estão os
achados desta rodada.

## Decisão 1 — Fechar a lacuna de detecção ANTES de qualquer avaliação

O ADR 0028 declarou três tipos de evento fora da detecção de invenção, porque o
M6.3 amarrava a detecção a um TERMO CONCRETO por tipo e estes não têm nenhum.

**Não era lacuna adversarial.** Era a mesma classe de alucinação que o M6.1
encontrou no motor de regras antigo — concluir `co2↑ ⇒ temperatura↑` sem conferir
se um `TemperatureShift` ocorreu naquele planeta. Correta como ciência geral, não
derivável daquela trilha. Ela reapareceu na camada de geração, e construir um
harness adversarial sobre ela seria medir a robustez de um sistema com um buraco
conhecido no meio.

### Especiação — fechada por identificador estrutural

O caso mais grave: é o que a Fase 0 protege, e as duas garantias existentes **não
alcançam prosa**. `SpeciationFact` recusa "A deu origem a B" no TIPO; o template
do M6.1 não tem slot de linhagem. Um modelo escreve a escada de progresso em
português sem tocar em nenhuma das duas.

E o mais tratável, por um fato decisivo sobre o prompt: **o modelo nunca recebe
identificador de linhagem.** Ele recebe o resumo do piso e as passagens, e o piso
não tem slot para isso. Logo um identificador na prosa não veio do material — foi
inventado, inclusive se coincidir com um real.

Três conferências: identificador vazado (e papel do envelope §4), especiação
AFIRMADA onde o log não a tem, e descendência linear como erro de forma — esta
última valendo **mesmo onde a divisão ocorreu**, porque contar uma divisão real
como "a antiga virou a nova" ensina a mesma escada.

Ecoar a VOC-002 no abstrato **não** é afirmação: se fosse, o corpus do M6.2
deixaria de poder ensinar o assunto.

### Temperatura e população — fechadas por direção conferida no log

Sem termo exclusivo, o que caracteriza afirmação é a DIREÇÃO. A conferência
distingue duas coisas que não são a mesma: o dossiê não ter o evento (invenção) e
o sinal do delta contradizer a direção afirmada (contradição).

Dois resultados falsos apareceram em teste, e ambos ensinam:

* **"o planeta esquentou" passava.** Exigir palavra de assunto E palavra de
  direção deixava passar a paráfrase mais natural. Verbos térmicos nomeiam a
  grandeza sozinhos.
* **A formulação CORRETA do BIO-005 era acusada.** "A característica aumentou a
  sobrevivência" tem assunto e verbo de subida na mesma oração e não afirma nada
  sobre tamanho de população — o verbo rege outro objeto. É a frase que o sistema
  mais precisa saber dizer, e reprová-la seria pior que não detectar invenção
  alguma. A regra passou a ser sintática: a direção é do que o verbo rege.

### E a honestidade sobre o que ficou de fora

Cinco tipos seguem sem checagem de invenção. `DetectionCoverage` viaja em todo
veredito e nomeia os dois conjuntos, e o resumo de um aprovado parcial **diz
"cobertura parcial"** em vez de "passou".

É a disciplina do terceiro estado do M6.3, aplicada ao outro eixo. Lá, um booleano
obrigava "não avaliado" a se disfarçar de "reprovado"; aqui, um APROVADO se
passava por conferência completa. Sem isto, a lacuna que este marco veio fechar
seria invisível de novo — uma prosa inventando um `TrophicCollapse` recebe hoje o
mesmo "passou" de uma impecável, e o objeto tem de dizer isso.

## Decisão 2 — Registrar as tentativas, porque não havia dado para minerar

O ADR 0028 prometeu ao M6.4 "os motivos de reprovação em forma utilizável". A
forma existia; **nada guardava nada.** Sem logger na camada de geração, sem
escrita, sem arquivo — o objeto vivia uma chamada e sumia.

Então o registro veio primeiro, e a mineração depois. Decisões:

* **Registrar TAMBÉM as aprovações.** Uma taxa precisa de denominador, e um
  arquivo só de falhas convida a estimá-lo.
* **JSONL, e não tabela.** O consumidor é uma pessoa abrindo o arquivo uma vez por
  rodada. Uma tabela exigiria migration e Postgres vivo para isso. Se um dia virar
  telemetria contínua, o caminho é o Event Store — e aí a decisão vem com LGPD
  junto, porque prosa gerada para um aluno é dado de aluno.
* **Append, e não reescrita.** O conjunto CRESCE entre marcos; reescrever
  guardaria a última execução e descartaria justamente as falhas raras.

## Decisão 3 — A medição, e as três coisas que uma taxa ingênua esconderia

1. **Indisponibilidade não é alucinação.** Recuo por rede fora do denominador —
   somá-lo faria a taxa PIORAR quando o Ollama cai, a leitura invertida.
2. **Aprovação parcial não vale o mesmo que completa**, e as duas são contadas
   separadas.
3. **A forma do piso confunde.** O relatório quebra por cenário ANTES de agregar,
   e a cascata — piso de cinco frases repetitivas, sinalizada no ADR 0028 — sai
   sempre isolada, ao lado de um cenário de piso curto que serve de controle.

`0.0` e "nada avaliado" são coisas diferentes, e a taxa devolve `None` no segundo
caso em vez de fingir um zero.

**Modelo (pre-flight c):** medir os dois. `llama3.2:1b`, com que o M6.3 provou o
pipeline, e `llama3.1:8b`, o de produção. Escolher em silêncio faria o número
parecer propriedade do SISTEMA quando é, em parte, do modelo.

**A medição não é portão.** Nenhum limiar é cobrado no CI, e é decisão: cobrar um
número convidaria a ajustar prompt ou modelo até alcançá-lo, que é otimizar a
métrica em vez do sistema. O que o CI exige é que o relatório seja PRODUZIDO e
fique legível, com as ressalvas ao lado.

## Decisão 4 — Guardrails, só onde a avaliação achou algo

Um só, e ele veio de um caso adversarial real. A frase *"as duas comunidades
desapareceram porque **eram inferiores** ao ambiente"* passava intacta: a lista de
aptidão absoluta nasceu no feminino singular, e **todos os plurais escapavam**.

Não é frase exótica. Um dossiê com duas extinções — o cenário-limite deste marco —
produz prosa sobre duas comunidades como fraseado mais natural.

A lição vale mais que as seis linhas acrescentadas: **uma lista negra escrita a
partir de um exemplo herda a flexão daquele exemplo**, e comparação por substring
não conjuga.

Nenhum outro guardrail foi acrescentado. Os candidatos que se costuma pôr aqui —
filtro de toxicidade, recusa de tema fora de escopo, defesa contra injeção de
prompt — não têm superfície neste sistema (ver abaixo), e implementá-los seria
segurança decorativa.

## O escopo adversarial, e por que ele é interno

**Não existe superfície de entrada do aluno.** Verificado: `apps/web-client` é um
esqueleto Next.js sem uma única chamada HTTP; nenhuma rota alcança a camada de
geração; não há interface de tutor ou chat no monorepo.

Então o vetor adversarial é o CORPUS, não uma pessoa. As passagens de teste são
desenhadas para explorar fraquezas conhecidas: nomear acontecimento ausente do
log, carregar número, afirmar mecanismo direcional, afirmar divisão. A terceira é
a mais aguda — *"mais gás carbônico retém mais calor"* é verdadeira, vem do corpus
do projeto, pontua alto, e o log da cascata registra a temperatura **caindo** 14
graus. Verdadeiro em geral, falso ali.

> **Risco latente registrado.** `ExplainRequest` declara `question: str | None`
> com o comentário "usado pelo tutor LLM no Inc 6", e **nada o lê**. É a família
> de defeito que este serviço já pagou duas vezes (`atmosphere.oxygen` sem
> escritor, o filtro fantasma de `planet_id`). No dia em que alguém o ligar à
> geração, o contrato de ancoragem ganha uma entrada controlada pelo aluno contra
> a qual ele nunca foi avaliado — e a categoria "pedido fora de missão", hoje sem
> superfície, passa a existir. A remoção não foi feita aqui por ser mudança de
> contrato de API fora do escopo deste marco.

## O que este marco NÃO fecha

* **Qualidade pedagógica.** Passar na fundamentação diz que a prosa não inventou
  nada; não diz que ela ensina melhor que o piso do M6.1. Comparar exige leitor
  humano com critério.
* **Cinco tipos de evento** seguem sem checagem de invenção — nomeados, não
  escondidos.
* **Paráfrase criativa** de afirmação direcional ("o planeta virou um forno") e
  magnitude sem número.
* **Injeção de prompt**, por não haver de onde injetar. O dia em que houver, este
  ADR é o registro de que a avaliação não a cobriu.
* **A forma do piso da cascata**, que segue como confundidor conhecido — é questão
  do M6.1, e mexer nela aqui misturaria dois marcos.

## Consequências

O arco M6 fecha com o caminho inteiro verificado: o Event Store define a verdade
(M6.0), o template dá o piso auditável (M6.1), o corpus dá registro sem tocar em
fato (M6.2), o modelo reescreve sob verificação com recuo garantido (M6.3), e a
detecção cobre agora os tipos que faltavam, com a cobertura declarada e a taxa
medida sem maquiagem (M6.4).

O que fica para quem continuar: um conjunto de avaliação que CRESCE a cada
execução, motivos agrupados por família — porque é a família que se conserta, e
não o caso —, e a lista honesta do que ainda não se verifica.
