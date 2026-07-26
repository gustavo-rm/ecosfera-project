# ADR 0004 — Linha do tempo por checkpoints + log de eventos (event-sourcing-lite)

> **Débito registrado (não tratado aqui): numeração de ADRs.** A numeração desta
> série é local ao `ai-sim-service` (`docs/adr/0001..`). O Dossiê PD&I mantém sua
> própria numeração de decisões em nível de projeto, também começando em 0001 —
> ou seja, o mesmo número identifica decisões diferentes conforme o nível. Neste
> repositório só a série do serviço está versionada. A unificação (prefixo por
> escopo, ex. `SRV-0004`/`PRJ-0004`, ou índice cruzado) fica para um incremento
> próprio; unificar agora renumeraria ADRs já referenciados em código e PRs.

## Status
Aceito.

## Contexto
O núcleo determinístico (ADR 0003) já produz o estado do planeta tick a tick, mas
só guardava o estado corrente. Faltava a **memória** exigida pelo Dossiê §9
(checkpoints por era + log de eventos) e o RF-016 (rebobinar a simulação): o aluno
precisa poder voltar a uma era anterior e comparar trajetórias.

A alternativa óbvia — gravar o estado de cada tick — é cara e redundante: com uma
era de dezenas de ticks e muitos planetas, o volume cresce sem limite para
armazenar informação **derivável**. O motor é determinístico por semente
(RF-023): dado o mesmo estado inicial, a sequência de ticks é sempre a mesma.

## Decisão
Adotamos **event-sourcing-lite**: em vez do log completo de mutações do
event-sourcing clássico, gravamos apenas o que o motor NÃO consegue derivar.

1. **Checkpoint append-only por era** (`EraCheckpoint`): o estado imutável ao fim
   de cada era, com a semente junto — o checkpoint é autossuficiente para o replay.
2. **Log de eventos append-only** (`EventLogEntry`), de dois tipos:
   - `intervention` — ação do aluno; **muta** o estado no replay (é a única
     entrada de informação externa que o motor não reproduz sozinho);
   - marcos (`life_emerged`, `snowball`, `ice_free`) — anotações narrativas;
     **no-ops** no replay, existem para dar significado à linha do tempo.
3. **`replay(base, events, until_tick, stepper, bounds)`**: função pura que
   reexecuta o motor a partir do checkpoint reaplicando os eventos. Como não faz
   I/O nem usa relógio, o resultado é idêntico ao original — e o
   `ReplayStateUseCase` **verifica** essa igualdade (`matches_checkpoint`),
   promovendo o determinismo de premissa a garantia observável em produção.

Convenção de ordenação única: **eventos do tick T são aplicados ao estado em T,
antes do passo que leva de T para T+1** — gravação e replay concordam por
construção.

A era 0 é a **gênese**, gravada na criação do planeta: sem ela a primeira era não
teria checkpoint anterior de onde rebobinar.

## Ordem de acoplamento dos subsistemas
Este incremento também completou os subsistemas (física, geologia, oceano). A
ordem canônica é **dado explícito** (`SUBSYSTEM_ORDER`), não convenção implícita:

    physics -> chemistry -> climate -> geology -> ocean -> life

Cada posição tem justificativa física (ver docstring do `orchestrator`). Um ponto
merece destaque: a geologia mantém o `volcanism` que a química lê para escalar a
desgaseificação, mas roda **depois** dela — o efeito no CO2 aparece no tick
seguinte. Essa **defasagem de um passo é deliberada**: quebra a dependência
circular geologia↔química sem recorrer a solver iterativo, mantendo o tick um
passo explícito e reprodutível.

## Consequências
+ Armazenamento proporcional ao nº de **eras** (e intervenções), não de ticks.
+ Replay verificado vira teste de regressão vivo do determinismo (RF-023).
+ O log de intervenções é exatamente o material do Stealth Assessment (Inc 7).
− Reconstruir uma era distante custa CPU (reexecutar ticks) em vez de I/O; com
  `era_length` na casa das dezenas isso é irrelevante, mas a mitigação, se
  necessário, é aumentar a frequência de checkpoints — sem mudar o modelo.
− O replay depende de os parâmetros (`simulation_params.yaml`) serem os mesmos da
  gravação. Por isso o arquivo é versionado com o campo `version`; associar a
  versão de parâmetros a cada checkpoint fica como evolução natural.
