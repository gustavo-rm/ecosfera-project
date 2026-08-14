# ADR 0027 — RAG pedagógico: recuperação de REGISTRO, e a fronteira contra o fato

**Série:** serviço (`services/ai-sim-service/docs/adr/`).
**Status:** Aceito. Fecha a subetapa **M6.2**, ainda sem geração e sem LLM.
**Relacionados:** ADR-ARCH-0002 (Correção 1 — a Visão Educacional é renderizada
pelo consumidor), ADR 0025 (fundação factual do M6.0), ADR 0026 (piso de
qualidade por template do M6.1), ADR 0019 (extinção catastrófica × ecológica;
aptidão contextual), ADR 0023 (ancestral comum na especiação), ADR 0024 (o Tutor
fala da comunidade), ADR 0002 (regras primeiro, LLM depois),
`docs/decisions/tassia-validation.md`, `docs/decisions/deferred.md`,
Dossiê PD&I v3 §3.4/§3.5/§4.1 e §10.5.

## Contexto

O M6.0 entregou o fato verificável; o M6.1 entregou a frase correta por template.
Falta a última peça antes do gerador: de onde o Tutor tira a VOZ.

O M6.2 entrega a infraestrutura de recuperação. Não gera texto — o retriever
devolve passagens, e quem escreve é o M6.3.

## Decisão

### 1. O corpus é sobre REGISTRO, não sobre ciência

Este corpus existe para o Tutor **soar** como um professor alinhado ao currículo,
não para ele **saber** mais ciência. A distinção decide a arquitetura:

* o FATO sobre o planeta do aluno vem do Event Store e é inviolável;
* o corpus informa como dizer, com que palavras, em que ordem didática, com que
  vocabulário proibido.

Se o corpus disser *"extinções catastróficas ocorrem"* e a trilha daquele planeta
não tiver nenhuma, o Tutor não pode narrar uma.

### 2. Prioridade do corpus: a voz do projeto antes do livro-texto

1. `vocabulary_rule` — as regras de linguagem da Fase 0 (BIO-005, BIO-001, PED-003, Q5);
2. `validated_correction` — as decisões da especialista (Tássia, Q5/Q8/Q11 aplicadas; Q3/Q12/Q15 adiadas explicitamente para o M6 como currículo do Tutor);
3. `curriculum_objective` — objetivos BNCC realmente citados no Dossiê;
4. `external_reference` — por último, pouco, e só com licença verificada.

Livros-texto gerais de biologia/química/física foram **considerados e rejeitados**
como corpus primário. Dois motivos, e o segundo é o que decide: empurram o
registro do Tutor para a voz de um manual universitário — errada para a faixa
etária —, e duplicam mal a ancoragem que o Event Store já dá aos fatos. O corpus
não existe para o Tutor saber mais; existe para ele falar certo.

`test_the_corpus_priority_is_respected` guarda a proporção: se um dia o material
externo ou o currículo passar a dominar, a decisão terá de ser retomada
explicitamente em vez de derivar sozinha.

### 3. Uma passagem recuperada NÃO é um fato — garantia de forma

O risco concreto do M6.3: um LLM vai receber, no mesmo prompt, o dossiê factual
daquele aluno e algumas passagens deste corpus. Se as duas chegarem com a mesma
cara, uma passagem que diz *"extinções catastróficas são independentes de
aptidão"* pode ser lida como *"houve uma extinção catastrófica neste planeta"*. A
frase seria fluente, pedagogicamente correta em tese, e FALSA sobre o planeta da
criança — ancorada num corpus real e não no event log dela.

A defesa é estrutural, em três camadas:

1. **Campos disjuntos.** `RetrievedPassage` não tem `event_id`, `occurred_at`,
   `cause_code`, `causation_id` nem `participants`. Tratá-la como fato quebra na
   primeira leitura de atributo, em vez de produzir narrativa errada em silêncio.
2. **Sem parentesco.** Nenhuma herança comum, nenhum protocolo comum.
3. **O verificador de tipos recusa** — e isso é afirmado RODANDO o `mypy` sobre a
   atribuição proibida, não deduzido de que "os tipos são diferentes".

`relevant_cause_codes` é chave de ROTEAMENTO, e o nome é deliberado: `cause_code`
no singular é o campo do envelope §4, e reusá-lo aqui convidaria a confusão.

### 4. Proveniência é invariante de banco, não convenção

Toda entrada declara de qual documento do projeto saiu; `external_reference`
declara licença. O modelo recusa a entrada anônima e o banco também
(migration 0006: `NOT NULL` + `CHECK`).

A razão é operacional: quando alguém perguntar *"por que o Tutor falou assim com
meu filho?"*, a resposta precisa ser um documento, não uma lembrança. E é por isso
que o manifesto é YAML revisável por um humano — incluindo a especialista — **sem
rodar código**.

Guardar proveniência em `metadata jsonb` foi rejeitado: seria convenção, e nada
impediria uma linha sem origem. Este serviço já pagou duas vezes por campos
declarados que ninguém exercitava (o `atmosphere.oxygen` sem escritor, o
`EventQuery.planet_id` que não filtrava).

### 5. Nenhum conteúdo curricular foi inventado

Os códigos BNCC saem da matriz de alinhamento do Dossiê (§3.4), que traz a própria
ressalva: *"itens com (conferir) pedem validação do número exato (o objeto de
conhecimento está correto)"*.

Essa ressalva é PRESERVADA em `code_verified`. Uma entrada com `code_verified:
false` teve o objeto de conhecimento conferido e o número da habilidade não —
promovê-la a verificada fabricaria precisão que o projeto não tem.
`test_every_bncc_code_actually_appears_in_the_dossier` confere código a código
contra o texto do Dossiê: ter o FORMATO certo não basta, porque um `EF09CI99` bem
formado passaria por qualquer regex e seria pura invenção.

### 6. Nenhuma referência externa nesta rodada, e isso é decisão

O projeto cita Elton (1927), Verhulst (1838), Bogost (2007) e Sweller nos ADRs
como referência BIBLIOGRÁFICA. Não há neste repositório o texto integral delas com
licença verificada, e indexar paráfrase própria apresentando-a como "referência
externa" inventaria proveniência — exatamente o que a categoria existe para
impedir. A regra é dura: na dúvida sobre a procedência, o material fica de fora.

### 7. O embedder é PORTA, com uma implementação de referência determinística

Mesmo desenho das outras portas do serviço. E aqui não é conveniência, é
requisito: **o CI sincroniza `--extra sim --extra infra --group dev`, sem o extra
`ai`**. Um teste de pgvector que dependesse de `sentence-transformers` pularia
exatamente onde precisa rodar, e um pulo silencioso é o que a política de
zero-skip existe para impedir.

`DeterministicEmbedder` projeta tokens normalizados por hash estável (`blake2b`,
nunca o `hash()` do Python, que é aleatorizado por processo). É **léxico, não
semântico**: mede sobreposição de vocabulário. Suficiente para provar que a
infraestrutura devolve a entrada certa; insuficiente para o produto final.

`SentenceTransformerEmbedder` é a implementação de produção, com
`paraphrase-multilingual-mpnet-base-v2` — 768 dimensões (casa com a coluna) e
multilíngue. A escolha do idioma não é preferência: o corpus é material curricular
brasileiro, e registro e vocabulário só funcionam indexados na língua-alvo.

### 8. O nome do modelo viaja com cada vetor, e a consulta filtra por ele

Similaridade entre vetores de modelos diferentes não significa nada — são espaços
distintos. Se sobrassem linhas de um modelo anterior, a busca devolveria a
passagem errada com um número plausível ao lado, que é pior que um erro que
estoura. Por isso `model_name` entra na chave primária, no `WHERE` de toda
consulta, e a reindexação substitui apenas as linhas daquele modelo.

## O que está VERIFICADO, e o que não está

Honestidade sobre o alcance desta rodada.

**Verificado:** o corpus e sua proveniência; o pipeline de indexação; o retriever
com filtro por categoria e por código de causa; o determinismo do embedder de
referência (inclusive entre processos, com `PYTHONHASHSEED` variando); a separação
de tipos entre passagem e fato (com o `mypy` executado); e — no CI — o adaptador
pgvector, incluindo a paridade com a implementação de referência e a recusa de
misturar modelos.

**NÃO verificado:** a chamada real ao `sentence-transformers` com pesos baixados.
A política de rede deste ambiente nega `huggingface.co` (403 no CONNECT) e o CI
não instala o extra `ai`. A LÓGICA do adaptador (checagem de dimensão, nome do
modelo, normalização, formato) é exercitada com um carregador injetado; o que não
aconteceu foi uma execução ponta a ponta com o modelo semântico. Fica declarado
aqui em vez de implícito, e é a primeira coisa a provar num ambiente com acesso.

> **Adendo (M6.3, pre-flight): a lacuna acima está FECHADA.** Ver a seção
> "O modelo semântico real, finalmente medido", ao final deste ADR.

## O modelo semântico real, finalmente medido

Adendo escrito no pre-flight do M6.3, que tratou a lacuna acima como PORTÃO: não
se ancora geração não-determinística numa recuperação cuja qualidade ninguém
mediu.

**Onde a medição passou a caber.** A política de egresso do ambiente de
desenvolvimento continua negando `huggingface.co` (403 no CONNECT, confirmado
host a host). O runner do CI não a nega — `huggingface.co` responde 200. Então
vale aqui a mesma solução que o M5 deu ao Postgres: o que a máquina de quem
escreve não pode exercitar, o CI exercita, e REPROVA em vez de pular. O job
`embedder-gate` instala o extra `ai`, baixa
`paraphrase-multilingual-mpnet-base-v2` e roda `scripts/validate_real_embedder.py`.

**O que ele mede.** As mesmas consultas do roteiro de fumaça, indexadas duas
vezes — uma com cada embedder, cada qual no seu próprio espaço vetorial e sob o
seu próprio nome — imprimindo posição e nota dos dois lados antes de afirmar
qualquer coisa.

Resultado, com o modelo real:

| consulta | referência (léxico) | real (semântico) |
| --- | --- | --- |
| `CATASTROPHIC_EVENT` | VAL-Q8 0,101 | VOC-006 0,399 · VAL-Q8 0,322 |
| `DIVERGENT_NICHE` | VOC-002 0,196 | VOC-002 0,405 |
| `PREY_COLLAPSE` | VAL-Q12 0,264 | VAL-Q12 0,307 |
| "especiação ancestral comum linhagens" | VOC-002 0,416 | VOC-002 0,733 |
| "aptidão contextual ou absoluta" | VOC-005 0,545 | VAL-Q5 0,533 · VOC-005 0,462 |
| "efeito estufa gás carbônico temperatura" | BNCC-EFEITO-ESTUFA 0,604 | BNCC-EFEITO-ESTUFA 0,723 |

**A regra que governa a consulta chegou em 1º nos seis casos.** As notas subiram
de modo geral, o que era esperado: o modelo mede sentido, e não sobreposição de
vocabulário.

### O achado que quase virou reprovação, e por que não era defeito

Em dois casos o modelo real trocou QUAL entrada vem em primeiro. Em
`CATASTROPHIC_EVENT` pôs VOC-006 à frente de VAL-Q8; na consulta de aptidão pôs
VAL-Q5 à frente de VOC-005. O critério original exigia uma entrada específica, e
teria reprovado o modelo.

Investigadas uma a uma, nenhuma das trocas é recuperação errada: em cada par, as
duas entradas declaram o mesmo tópico e dizem a MESMA regra — uma como regra de
vocabulário, a outra como correção validada de onde a regra saiu. O corpus tem
essa forma de propósito, porque a prioridade declarada põe as duas categorias
lado a lado, e os conceitos de maior risco pedagógico aparecem nas duas. Além
disso `for_cause_code` devolve as duas categorias juntas, então o M6.3 recebe o
par de qualquer maneira.

O critério passou a ser um CONJUNTO fechado e justificado por consulta: em 1º tem
de vir uma entrada que carregue a regra pedida. A barra continua mordendo — na
consulta de aptidão, `BNCC-EVOLUCAO-ADAPTACAO` ficou em 2º, e um objetivo de
currículo em 1º reprovaria.

**A limitação a registrar, então, não é de qualidade — é de granularidade:** o
modelo semântico não distingue regra de vocabulário de correção validada quando
as duas dizem o mesmo. Quem, no M6.4, quiser priorizar uma categoria sobre a
outra terá de fazê-lo por FILTRO de categoria, e não esperando que a similaridade
o faça.

### Um defeito de produção que só o modelo real podia revelar

`sentence-transformers` renomeou `get_sentence_embedding_dimension` para
`get_embedding_dimension`, e o nome antigo — o que o adaptador usava — já emite
`FutureWarning`. **Nenhum teste com carregador injetado poderia ter encontrado
isso:** o falso implementava justamente o nome que o adaptador pedia, e a dupla
concordava sozinha enquanto a biblioteca real avisava.

O adaptador aceita os dois nomes, o novo primeiro, com contraprova que expõe só o
novo. Perder essa checagem numa atualização de dependência deixaria vetores do
tamanho errado chegarem ao `INSERT` — que é precisamente o que ela existe para
impedir.

## Duas limitações medidas do embedder de referência

Medidas, e não deduzidas — o roteiro de fumaça as encontrou.

**Viés de comprimento.** O cosseno sobre saco-de-palavras favorece entradas
curtas. A regra do ancestral comum aparecia em 4º lugar numa consulta que continha
as palavras "ancestral comum", porque ela carregava, além da regra, o parágrafo
que a justificava. **A correção foi no CORPUS, não no algoritmo:** a entrada voltou
a ser a regra curta e citável que o manifesto sempre pediu — a justificativa vive
no ADR citado como origem — e subiu para 1º com 0,42. É a razão de o manifesto
insistir em frases curtas.

**Similaridade não é comparável entre consultas de formatos diferentes.** Uma
busca de dois tokens contra um texto longo produz 0,10 mesmo sendo a resposta
certa; uma de quatro tokens bem casada produz 0,60. O ranking DENTRO de uma
consulta é significativo; o valor absoluto entre consultas distintas não é. Quem
for calibrar um corte de confiança no M6.4 precisa saber disso antes de escolher
um limiar único.

## Uma limitação medida da infraestrutura: o índice é aproximado

Também medida, e também pelo caminho difícil — o CI a encontrou.

O HNSW é um índice de **vizinhos aproximados**. Ele percorre um grafo de
vizinhança e devolve os melhores que encontrou, não os melhores que existem, e o
tamanho da lista de candidatos dessa varredura é o parâmetro `ef_search`. Com o
padrão do pgvector (40), uma busca com `limit=100` sobre as 21 entradas do corpus
devolveu **14**. Não foi falha de gravação: as 21 estavam na tabela.

Duas consequências, de gravidades bem diferentes:

* **No teste.** Perguntar "indexou tudo?" a uma busca por similaridade é a
  pergunta errada, e ela escondia um risco de verdade: uma gravação incompleta
  passaria despercebida sempre que a aproximação, por acaso, devolvesse tudo. O
  teste de completude agora lê `rag.corpus_entry` direto; recuperação é o que os
  testes de ranking verificam.
* **No produto.** A mesma aproximação pode descartar **a passagem mais
  relevante**, em silêncio e sem erro. Perder recall no fim da lista é tolerável;
  entregar ao Tutor a segunda melhor passagem achando que é a primeira, não.

Por isso toda busca fixa `SET LOCAL hnsw.ef_search` num piso de 100 candidatos
(ou `4 × limit`, o que for maior). Num corpus desta ordem de grandeza a varredura
fica praticamente exaustiva e não há desempenho a defender — o custo é de
microssegundos, e o índice segue valendo quando o corpus crescer. Se um dia ele
crescer a ponto de esse piso pesar, a decisão a tomar é sobre recall, com número
medido na frente; o que não se pode é herdá-la por omissão de um padrão.

## O que este marco NÃO faz

* **Nenhuma geração, nenhum LLM.** M6.3. Barrado por dois contratos de
  `import-linter` e por uma varredura que procura o sinal mais barato de
  composição (juntar textos de passagens).
* **Nenhuma avaliação adversarial da qualidade de recuperação.** M6.4.
* **Nenhuma rota HTTP.** Era opcional; ficou de fora para manter a rodada estreita,
  e a inspeção humana é feita por `scripts/smoke_m6_2.py`, que IMPRIME as
  passagens antes de afirmar qualquer coisa.
* **Nenhuma mudança no `FactualContext`, nos templates do M6.1 ou no Event Store.**
* **`rag.embedding` (migration 0001) fica intacta e sem uso.** Ela é baseline
  genérica de um plano anterior, sem escritor nem leitor. Fica registrada como
  candidata a remoção — decisão própria, fora do escopo desta rodada — para que
  ninguém a confunda com o corpus de verdade.

## Como o M6.3 deve consumir isto

O atalho central é `for_cause_code`: dado o `cause_code` de um evento REAL do
planeta — que veio do Event Store, **não** daqui —, quais regras de linguagem e
correções validadas governam a forma de contá-lo. O método não afirma que o
mecanismo ocorreu; o código é apenas a chave de busca.

A hierarquia de ancoragem do M6.3, agora com as três peças no lugar:

| Camada | Origem | Autoridade |
| --- | --- | --- |
| O QUE aconteceu | Event Store → `FactualContext` (M6.0) | **inviolável** |
| Como se diz corretamente | templates do M6.1 | o piso a superar |
| Em que registro e com que vocabulário | este corpus (M6.2) | informa, não decide |
| A frase final | LLM (M6.3) | reescreve, não decide o fato |

## Alternativas consideradas

* **Livros-texto externos como corpus primário.** Rejeitada — ver decisão 2.
* **Reusar `rag.embedding` da migration 0001.** Rejeitada: proveniência em
  `metadata jsonb` é convenção, e nada impediria uma entrada anônima ou uma
  referência externa sem licença.
* **Um só embedder, o semântico.** Rejeitada: tornaria os testes de pgvector
  impossíveis de rodar no CI, que não instala o extra `ai` — e um teste de
  persistência que pula é a verificação que não aconteceu com a árvore verde.
* **Ordenar em Python também no adaptador Postgres**, para ter uma cópia só da
  regra (como o ADR 0023 decidiu para o `EventQuery`). Rejeitada aqui porque a
  razão não se aplica: similaridade vetorial não é predicado que possa divergir —
  é função matemática fechada —, e ordenar no banco é o motivo de existir uma
  extensão vetorial. A paridade com a implementação de referência é testada.
* **Guardar `code_verified` fora do corpus**, só no Dossiê. Rejeitada: a ressalva
  precisa viajar com a passagem, senão o consumidor de cima a apresenta como
  certeza.

## Consequências

**Ganhamos.** O M6.3 tem de onde tirar registro sem inventar, com proveniência
auditável por documento e com uma fronteira de tipo que impede a confusão mais
cara que este desenho admite. O corpus é revisável por quem entende de pedagogia,
sem rodar código.

**Perdemos.** Mais um arquivo de conteúdo versionado a manter em dia, e um
embedder de referência cuja qualidade de recuperação é lexicamente limitada — o
que obriga a manter clara, em cada teste, a diferença entre "recupera a entrada
certa" e "ordena por importância pedagógica".

**Fica em aberto.** A execução real do modelo semântico (bloqueada por política de
rede aqui); a rota HTTP de auditoria; e a validação do corpus pela especialista —
o manifesto foi escrito para ser lido por ela, e essa leitura ainda não aconteceu.
