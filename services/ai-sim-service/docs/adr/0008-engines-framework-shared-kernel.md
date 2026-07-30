# ADR 0008 — Moldura de Engines: shared kernel e Planet Engine

## Status
Aceito. Implementa, no `ai-sim-service`, as decisões de projeto
**ADR-ARCH-0001** (Arquitetura de Engines) e **ADR-ARCH-0002** (Observabilidade
por Design), cujos contratos estão em
`docs/architecture/ECOSFERA_Engine_Framework_Spec.md`. Referências: Dossiê v3
§10.4/§10.5, RF-023 (determinismo/replay).

Escopo: **M0 — a moldura**. Nenhum Engine científico é criado aqui (isso é M1+).

## Contexto

O ADR-ARCH-0001 reenquadra o que já existe: o `TickOrchestrator` **é** o Planet
Engine, os `subsystems/*` são as sementes dos Engines científicos, e a
timeline/checkpoints são a base do Event Store. Nada é descartado — falta a
moldura comum que dê a todos a mesma interface, o mesmo envelope de evento, o
mesmo contrato de replay e o mesmo contrato de observabilidade.

Ao confrontar a Spec com o código, quatro pontos exigiam decisão antes de
qualquer linha.

## Decisão

### 1. O loop de simulação é SÍNCRONO; a borda de I/O permanece assíncrona

`Engine.tick()` é síncrono (Spec §5.2). Corrotinas introduzem a ordem de
escalonamento como variável oculta: sob `asyncio`, a mesma semente poderia
produzir intercalações distintas e o replay bit-a-bit deixaria de valer.

Os casos de uso (`run_tick`, `advance_era`, `replay_state`), o FastAPI, a
persistência e a fila ARQ **continuam `async`** e passam a orquestrar o loop
síncrono por fora. A fronteira síncrono/assíncrono é, deliberadamente, a mesma
fronteira determinístico/observável.

### 2. A composição de deltas é SEQUENCIAL, não simultânea

A leitura literal da Spec §5.3 ("publica snapshot read-only; cada Engine computa
lendo o snapshot; o Planet compõe os deltas em ordem") admitiria que todos os
Engines lessem o estado de abertura do tick. Adota-se a leitura oposta: o Planet
**republica** o snapshot após compor cada delta, então o Engine N enxerga o
efeito dos Engines 1..N-1.

Razões: (a) a própria Spec justifica a ORDEM pelos acoplamentos, o que só faz
sentido sob composição sequencial; (b) é o que o núcleo determinístico já faz — a
química atualiza o CO2 **antes** de o clima calcular a estufa; sob composição
simultânea o efeito estufa atrasaria um tick e a física mudaria, contrariando o
requisito de paridade determinística deste M0.

"Read-only" passa a significar **propriedade** (nenhum Engine escreve a fatia
alheia), não atualidade do dado.

### 3. Identificadores de evento são derivados, nunca sorteados

O envelope §4 pede `event_id`/`correlation_id`. `uuid4()` dentro do loop
quebraria o replay: a mesma semente produziria ids diferentes a cada execução.
Adota-se `uuid5` sobre (semente, era, tick, engine, tipo, sequência). Pela mesma
razão, a entropia do `engine_id` no RNG vem de BLAKE2b e não de `hash()`, que é
aleatorizado por processo.

`cause_code` é **enum extensível por Engine** (`CauseCodeEnum`, base vazia e
portanto herdável), validado em runtime: prosa pedagógica no lugar do código é
`TypeError`.

### 4. O adaptador do legado embrulha o ORQUESTRADOR, não cada subsistema

O plano do M0 previa embrulhar `climate/chemistry/geology/ocean` como Engines
individuais. A inspeção do código mostrou que isso **altera a física** — o que o
próprio M0 proíbe:

1. **Fluxo de RNG compartilhado.** `TickOrchestrator.tick` cria UM gerador por
   tick e o passa aos seis subsistemas em sequência; cada um consome sorteios de
   onde o anterior parou. A moldura, corretamente, dá a cada Engine um fluxo
   independente. Separar os seis trocaria todos os sorteios.
2. **Escrita através das fatias.** `chemistry` escreve `co2` (química),
   `ice_cover` (clima) e `water` (hidrologia); `ocean` escreve `temperature`, que
   é do clima. A regra "um Engine, uma fatia" seria violada por dois dos quatro.

Adota-se então **um Engine, `legacy_planet`, dono de uma fatia transitória
`LEGACY`** que espelha o `PlanetState`. O comportamento é bit-a-bit o de hoje
porque é literalmente o mesmo código. Cada Engine de M1/M2 tira campos da
`LegacySlice` e assume a autoria da sua fatia, até a fatia desaparecer. É o único
ponto que ignora `ctx.rng` de propósito, e a exceção morre junto com a fatia.

### 5. Uma fatia a mais que a Spec: `AstronomySlice`

A Spec §3 lista sete fatias mas inclui `physics` na ordem de tick (§5.3) sem lhe
dar fatia. Órbita e irradiância não são atmosfera nem clima, e o integrador
simplético precisa ser dono exclusivo delas. A lacuna é da Spec; a fatia a fecha
sem alterar nenhuma das sete.

### 6. Convivência atrás de flag

`ECOSFERA_ENGINES_FRAMEWORK` (padrão `off`) escolhe, na raiz de composição, entre
o `TickOrchestrator` direto e o `FrameworkTickOrchestrator`, que expõe a mesma
superfície e roda o tick pelo Planet Engine. Os casos de uso passam a depender do
Protocol `Ticker`, não do concreto — trocar a implementação não muda assinatura
alguma acima.

### 7. Numeração de ADR

A série de **projeto** usa `ADR-ARCH-` em `docs/architecture/adr/`; a série de
**serviço** continua numérica aqui. O último número de serviço em uso é 0007
(fila de jobs, PR aberto do Inc 3), portanto o M0 ocupa **0008 e 0009**. A
pendência histórica de numeração fica resolvida por escopo, como determina o
ADR-ARCH-0001 — sem fusão de séries.

## Consequências

+ Fronteiras verificadas por ferramenta (`import-linter`, cinco contratos), não
  por disciplina: Engine não importa Engine, Planet não conhece Engine algum,
  moldura e Engines não alcançam `infrastructure`/`interfaces`.
+ O grafo de dependências é validado no boot: dono duplicado de fatia, id
  duplicado e leitura para trás não declarada falham ao subir, com mensagem
  explicando o conserto.
+ Defasagem de um tick (a da geologia) deixa de ser folclore e vira declaração:
  `lagged_reads`. Não declarada, é erro.
+ Paridade determinística comprovada com o núcleo real, por semente e pela API
  (`ECOSFERA_ENGINES_FRAMEWORK=on|off` produz o mesmo estado, o mesmo delta, as
  mesmas observações e o mesmo `matches_checkpoint`).
− Duas rotas de tick a manter enquanto a flag existir. Mitigado pelo teste de
  paridade, que roda em três sementes por 40 ticks.
− A fatia `LEGACY` é dívida declarada: ela paga M1/M2 e deve encolher a cada
  Engine científico entregue. Se parar de encolher, virou permanente.
