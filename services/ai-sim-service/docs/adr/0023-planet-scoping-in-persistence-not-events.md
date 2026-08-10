# ADR 0023 — O planeta é dimensão de armazenamento, não do fato

**Série:** serviço (`services/ai-sim-service/docs/adr/`).
**Status:** Aceito. Corrige dívida do M5, antes de qualquer consumidor do M6.
**Relacionados:** ADR-ARCH-0002 (observabilidade por design), Spec §4 (envelope
de evento), ADR 0021 (Event Store persistente e contrato de query).

## Contexto

O M6.0 seria o primeiro consumidor real do contrato de leitura entregue pelo M5.
O pre-flight parou antes de escrever código, e o motivo é o pior tipo de defeito
que esta plataforma admite.

`EventQuery` declarava um campo `planet_id`. O `matches()` testava oito campos, e
`planet_id` não era um deles. Nenhum teste o exercitava. O filtro existia, era
aceito, e não filtrava nada.

**Por que isso é crítico e não cosmético.** O M6 inteiro se apoia numa definição:
um consumidor está correto quando o que afirma é derivável do event log. Um
recorte por planeta que não recorta entrega ao Tutor a trilha de dois planetas
parecendo escopada — e ele narra ao aluno, com total confiança, citando eventos
reais, a catástrofe do planeta de OUTRO aluno. Toda afirmação seria derivável de
um event log; só não do dele. Nenhuma avaliação adversarial do M6.4 pegaria isso,
porque a resposta estaria ancorada. Apenas na trilha errada.

## A varredura

Aplicou-se à superfície do contrato a mesma varredura que o M5 fez com `oxygen`.
Onde há um campo decorativo, costuma haver mais:

| Campo | Aplicado? | Testado? | Evidência |
| --- | --- | --- | --- |
| `planet_id` | **não** | não | fantasma — `matches()` nunca o lia |
| `era` | sim | **não** | `by_era_and_tick` não passava era |
| `from_tick` | sim | sim | mesmo teste |
| `to_tick` | sim | sim | mesmo teste |
| `correlation_id` | sim | sim | `by_correlation_groups_one_tick` |
| `causation_id` | sim | **não** | nenhum teste passava o campo |
| `cause_codes` | sim | sim | `by_cause_code` |
| `event_types` | sim | **não** | `by_engine_and_event_type` não passava tipo |
| `engine_ids` | sim | sim | mesmo teste |
| `include_diagnostics` | sim | **parcial** | só o default `False` |

Dois nomes de teste prometiam cobertura que não davam. Um nome que afirma cobrir
o que não cobre é da mesma família do filtro decorativo: os dois deixam um leitor
confiante sobre algo que nada verifica.

## Decisão

### 1. O planeta sai do predicado e vira escopo da porta

A Spec §4 mantém planeta fora do envelope **de propósito**, e essa decisão
continua certa: uma "erupção no tick 1200" é o mesmo fato em qualquer planeta. Em
QUAL planeta ele está é onde está guardado, não o que ele é.

A consequência coerente é que o recorte por planeta não é predicado sobre o
evento — é escopo de armazenamento. `planet_id` passa a ser o **primeiro**
parâmetro de `query` e `causal_chain`, **sem default**: um default silencioso
degradaria para "todos os planetas" no primeiro esquecimento, que é exatamente
como o defeito do M5 já se comportava.

### 2. `event_id` é único POR PLANETA (migration 0005)

A verificação de pre-flight pedida era "as cadeias causais cruzam planetas?". A
resposta é mais dura: **elas não cruzam, elas colidem**. `event_id = uuid5(seed,
era, tick, engine_id, event_type, sequência)` e `correlation_id = uuid5(seed,
era, tick)` — nenhum inclui planeta. Dois planetas de mesma semente produzem
identificadores byte a byte idênticos. Medido:

```
event_id planeta A : b7ef9f5d-52e7-5495-9fc4-cd105a01045d
event_id planeta B : b7ef9f5d-52e7-5495-9fc4-cd105a01045d
```

A migration 0004 criara `UNIQUE (event_id)` global. Logo **gravar dois planetas
de mesma semente era impossível**: o banco recusava a corrida do segundo aluno
como reprocessamento da do primeiro. E dois alunos com a mesma semente não é caso
de laboratório — é uma turma a que se disse "usem a semente 2027".

A chave passa a ser `(planet_id, event_id)`. Isto **reforça** a decisão 1 em vez
de contradizê-la: o mesmo fato pode existir em dois planetas, e quem os distingue
é o armazenamento. A idempotência que a 0004 buscava fica preservada no grão
correto — reprocessar a corrida de um planeta continua não podendo duplicá-la; o
que deixa de acontecer é um planeta bloquear o outro.

Descartou-se pôr planeta na derivação do id: tornaria o id globalmente único sem
migration, mas colocaria identidade de planeta **dentro** do evento por via
indireta — contra a Spec §4 — e invalidaria todo `event_id` já gravado.

### 3. A porta passa a ser assíncrona

O M5 declarou-a síncrona porque só existia a implementação em memória. O Event
Store de verdade é o Postgres, async como todas as outras portas de persistência
deste serviço. Uma porta síncrona forçaria o adaptador a não implementar a porta
(e então não há paridade a testar — a implementação de referência seria a única a
satisfazer o contrato) ou a bloquear o event loop. As duas trocam desconforto de
teste por defeito de produção.

### 4. Um único lugar decide o que casa

Os filtros de campo **não** são reescritos em SQL. A consulta escopa o planeta no
`WHERE` e aplica `EventQuery.matches()` sobre a trilha já escopada — o mesmo
predicado que a implementação em memória usa.

É deliberado, e o motivo é esta própria dívida: o M5 tinha a regra num lugar e a
declaração noutro, e as duas divergiram sem que nada acusasse. Duas cópias do
predicado — uma em SQL, uma em Python — divergiriam do mesmo jeito, e a
divergência apareceria como o Tutor citando um evento que o filtro dizia ter
excluído. O custo é ler a trilha do planeta inteira: centenas de eventos numa
corrida de 500 ticks. Se um dia doer, o caminho sem reintroduzir a divergência é
**gerar** o `WHERE` a partir do `EventQuery`, nunca escrevê-lo à mão em paralelo.

## A garantia

`test_planet_isolation_no_cross_leak` é adversarial, não caso feliz: dois
planetas, a mesma semente, eventos do mesmo tipo nos mesmos ticks.

Contar não bastaria — com os ids colidindo, uma trilha vazada teria o mesmo
tamanho. Os eventos levam uma marca em `cause_detail` (que **não** entra na
derivação do id), então dois eventos podem ter o mesmo identificador e conteúdos
distintos. É isso que permite afirmar que a consulta devolveu o evento do planeta
CERTO, e não apenas a quantidade certa.

O teste cobre sete recortes, a cadeia causal, o planeta inexistente (que devolve
vazio, nunca "tudo") e a idempotência do reprocessamento.

## O que acontece com as linhas gravadas antes destas migrations

Fronteira explícita, para não morder no primeiro ambiente com dados de teste.

**`planet_id` não é coluna nova.** Existe em `simulation.event_log` desde a
migration 0002 (M2), como `text NOT NULL`. Nenhuma linha jamais foi gravada sem
planeta, e não há órfão possível nessa coluna — nem backfill a fazer.

**As colunas novas são as do envelope §4** (0004): `event_id`, `engine_id`,
`era`, `seed`, `cause_code`, `correlation_id`, `causation_id`, `granularity`.
São *nullable* de propósito (ADR 0021), então as linhas gravadas pelo caminho do
M2 têm `event_id NULL`. Elas continuam válidas e continuam legíveis pelo
`load_events` do M2, que é quem as escreveu.

**O leitor novo as ignora, e isso é decisão, não descuido.** `PostgresEventQuery`
consulta `WHERE planet_id = :planet_id AND event_id IS NOT NULL`. Uma linha sem
envelope não tem `cause_code`, `correlation_id` nem `causation_id` — não é um
`DomainEvent` empobrecido, é outra coisa. Reconstruí-la com campos inventados
entregaria ao Tutor um fato que o Event Store não contém, que é exatamente a
alucinação que este ADR existe para impedir. Ficam invisíveis à porta de leitura,
por onde nunca deveriam ter entrado.

**A 0005 não pode falhar sobre dado existente.** O índice é parcial
(`WHERE event_id IS NOT NULL`), então linhas do M2 nunca conflitam. E a
restrição que ela substitui — `UNIQUE (event_id)` global — é *estritamente mais
forte* que `UNIQUE (planet_id, event_id)`: qualquer base que satisfazia a antiga
satisfaz a nova por construção. A migração é segura em qualquer banco que já
tivesse a 0004 aplicada.

**Em desenvolvimento não há dado a preservar.** Não existe produção; os bancos
são efêmeros (Testcontainers) ou locais. Se algum ambiente de teste ficar em
estado estranho, a resposta correta é **recriar do zero**, não escrever
backfill. Só o `downgrade` da 0005 pode falhar legitimamente — se dois planetas
de mesma semente já convivem, a restrição global não é satisfazível, e restaurá-
la significaria descartar a trilha de um deles.

## Dívida declarada, não fechada

O M5 nunca ligou um escritor do envelope §4: `append_event` grava as quatro
colunas do M2, e as oito do envelope ficam NULL em toda linha que o **serviço**
escreve. Este ADR fecha a ponta da persistência — `PostgresEventStore` grava o
envelope inteiro e `PostgresEventQuery` o lê de volta — mas **não** rewira
`advance_era`/`evolve_biology`, que seguem no caminho `EventLogEntry` do M2.

Fica declarado: enquanto esse rewire não acontecer, o Event Store persistente é
alimentado por quem chamar `PostgresEventStore` explicitamente, não pelo laço da
simulação. O M6 depende disso e é o marco natural para fazê-lo.

## Consequências

**Ganhamos.** O escopo por planeta passou de promessa a barreira, com um teste
que falha se vazar. A varredura virou teste (`test_no_phantom_filters`), então a
combinação "campo declarado, nunca aplicado" não volta em silêncio. E o Event
Store persistente ganhou, enfim, uma porta de leitura consultável.

**Perdemos.** Uma migration a mais e uma garantia do M5 reescrita; a porta
assíncrona torna a implementação em memória menos confortável nos testes rápidos;
e a consulta lê a trilha do planeta inteira antes de filtrar, que é o preço
consciente de não ter duas cópias do predicado.
