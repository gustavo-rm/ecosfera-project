# ADR 0006 — Biologia emergente dentro do simulation_engine

> **Débito ainda em aberto (não tratado aqui): numeração de ADRs.** Continua
> valendo o registrado no ADR 0004 — esta série é local ao `ai-sim-service`
> (`docs/adr/0001..`), enquanto o Dossiê PD&I numera decisões de projeto a partir
> de 0001 também. Neste repositório só a série do serviço está versionada. A
> unificação segue adiada de propósito: renumerar agora quebraria referências já
> feitas em código, ADRs e PRs.

## Status
Aceito.

## Contexto
Este é o primeiro incremento que cruza a fronteira determinístico × IA, e o
Dossiê é **ambíguo sobre onde a IA emergente mora**:

| Fonte | O que diz |
| --- | --- |
| §3.1 | lista AG e ABM como **subsistemas do Motor da Simulação** |
| §7 | reserva `ai-engine/` para **tutor, stealth assessment e adaptação** |
| §8 / GDD §10 | rotula evolução e ecologia como **"IA emergente"** |

Ler "IA emergente" como "vai para `ai_engine/`" seria o erro fácil. Mas o rótulo
descreve o *comportamento* (não roteirizado), não a *dependência arquitetural*.

## Decisão

**AG e ABM são EMERGENTES, mas são SUBSISTEMAS DE SIMULAÇÃO.** Vivem em
`simulation_engine/biology/`, não em `ai_engine/` — que permanece reservado ao
Inc 6/7. O critério que decide é observável, não estético: estes motores
**leem o `PlanetState`, threadam a semente do planeta, entram no event log e
participam do replay**. Tudo isso é comportamento de simulação. O tutor LLM do
Inc 6, ao contrário, não terá nenhuma dessas propriedades.

**Emergente porém reproduzível por semente (RF-023).** Sem isso, o replay do
Inc 2 (ADR 0004) deixaria de reconstruir o passado — a linha do tempo inteira
perderia sentido. Cada era deriva sua semente de `SeedSequence([seed, era, sal])`,
o mesmo mecanismo do orquestrador determinístico. Duas armadilhas concretas:

- o **DEAP** usa o módulo `random` GLOBAL. A execução salva o estado global,
  semeia, roda e **restaura** no `finally` — reprodutível sem poluir o processo
  (há teste explícito de vazamento);
- o **Mesa** é semeado por `Model(seed=...)`, e a ordem de ativação usa
  `shuffle_do`, que consome o RNG semeado do modelo.

**A fronteira é uma regra de escrita, não de intenção.** A camada emergente
**nunca escreve no `PlanetState`**. O único ponto de acoplamento é o
`life.py` determinístico, que passou a publicar `carrying_capacity(state)`: a
biologia consome essa capacidade como orçamento e distribui espécies e populações
DENTRO dela. Consequência verificável: ligar ou desligar
`ECOSFERA_BIOLOGY_ENABLED` não muda um bit da física, química, clima ou geologia
para a mesma semente — é exatamente o que
`tests/unit/test_deterministic_layer_unaffected.py` verifica campo a campo.

**Composição, não duplicação, no feedback causal.** Os resultados biológicos
viram observações (`extinction`, `biodiversity`) passadas ao
`ExplainCausalUseCase` **já existente**. As regras que ligam pressão ambiental a
extinção/prosperidade são dados em `configs/causal_rules.yaml` (version 3).
Nenhum LLM participa: o tutor continua sendo o Inc 6 (ADR 0002).

## Consequências
+ O replay reconstrói a biologia junto com a física, reexecutando o motor era a
  era — sem ler o códex gravado, o que torna a igualdade uma prova, não um cache.
+ Novos processos emergentes entram como mais estratégias, sem tocar nas camadas
  superiores; `ai_engine/` continua limpo para o Inc 6/7.
− **Custo computacional** é o risco declarado do incremento. Mitigação em três
  camadas: agentes são POPULAÇÕES (não organismos), tetos configurados
  (`max_agents`, `max_steps`, `max_species`, `generations`) e o job pesado sai do
  ciclo request/response pela porta `JobQueue` (ADR 0007). Há teste de orçamento
  de tempo em `tests/performance/`.
− O modelo trófico é deliberadamente simples (três níveis). Foi preciso uma regra
  explícita de **repovoamento do nicho produtor**: a mutação podia empurrar todos
  os produtores para níveis consumidores, deixando uma teia alimentar sem base —
  ecologicamente impossível. Documentado no código.
− A biologia depende dos parâmetros versionados; reproduzir uma era antiga exige
  a mesma `version` do `simulation_params.yaml`. Ligar a versão de parâmetros ao
  checkpoint segue como evolução natural (já anotado no ADR 0004).
