# ADR 0014 — Aposentadoria do legado, e a perda deliberada do rollback

## Status
Aceito. Fecha o M2. Encerra o **ADR 0008** (moldura atrás de flag) e o
**ADR 0011** (flag ligada por padrão). Depende do **ADR 0012** e do **ADR 0013**,
que deram dono a todas as fatias. Referências: Dossiê v3 §10.4/§10.5, Spec §5.3,
RF-016, RF-023.

Este ADR trata **só da remoção**. As decisões de fronteira científica estão nos
ADRs 0012 e 0013 — separá-las é proposital: são decisões distintas, e misturá-las
tornaria impossível rastrear qual delas se questiona quando algo der errado.

## Contexto

O M0 entregou a moldura atrás de `ECOSFERA_ENGINES_FRAMEWORK`, desligada, com o
núcleo determinístico inteiro atravessando-a por um adaptador. O M1 ligou a flag
por padrão e migrou três subsistemas. O ADR 0011 já dizia o que fazer em seguida:

> Ela deve ser removida quando o M2 esvaziar a `LegacySlice`; mantê-la além disso
> preservaria a ciência antiga em produção sem motivo.

Com o M2, a `LegacySlice` esvaziou. Os ADRs 0012 e 0013 deram dono às oito
fatias, e o adaptador deixou de ter o que adaptar.

## Decisão

### 1. O `LegacySubsystemAdapter` e os seis subsistemas são removidos

`engines/legacy/` inteiro sai. Com ele saem `simulation_engine/subsystems/`
(`physics`, `chemistry`, `climate`, `geology`, `ocean`, `life`) e o
`TickOrchestrator` monolítico, que ficaria sem subsistemas para orquestrar.

Onde cada um foi parar:

| Subsystem | Destino |
| --- | --- |
| `physics` | Astronomy Engine (ADR 0013) |
| `geology` | Geology Engine (M1) |
| `climate` | Climate Engine (M1) |
| `chemistry` | Atmosphere (carbono, M1) + Chemistry (N/P/S, oceano) + Hydrology (gelo↔água) |
| `ocean` | Hydrology Engine (salinidade, circulação) |
| `life` | Resource (capacidade) + Biota provisório (crescimento) |

### 2. `ECOSFERA_ENGINES_FRAMEWORK` é removida

A flag some de `Settings`, do `.env.example` e do composition root, junto com o
ramo condicional em `get_orchestrator()` e o `if settings.engines_framework` que
decidia se o Tutor consumiria a trilha de eventos.

Uma flag que escolhe entre dois caminhos quando só existe um não é um recurso: é
uma promessa falsa. Definir a variável de ambiente hoje não faz nada, e é melhor
que ela não exista a que finja oferecer uma escolha já inexistente.

### 3. **Não há mais rollback para a ciência anterior ao M1 — e isso é intencional**

Esta seção existe porque a perda precisa ser uma decisão consciente no registro,
e não um efeito colateral descoberto depois.

O que se perdeu, dito sem eufemismo: **não é mais possível rodar a trajetória
anterior ao M1.** O efeito estufa linear, o carbono no `chemistry`, a ordem de
acoplamento antiga — nada disso existe no código. Se um dia se concluir que a
ciência do M1/M2 estava errada, a saída é corrigi-la para a frente, não voltar
uma chave.

Aceitamos isso por três razões:

1. **A flag nunca foi um modo equivalente.** O ADR 0010 registra que as duas
   trajetórias divergem por construção: o forçamento logarítmico satura e o
   linear não. "Rollback" aqui sempre significou "rodar ciência que sabemos ser
   pior", não "voltar a um estado conhecido bom.
2. **A reversibilidade que importa é outra.** O que a auditoria e o produto
   precisam é reproduzir o passado: dada uma semente e um checkpoint, recompor
   a mesma trajetória bit a bit. Isso é o **replay determinístico**, e ele não
   depende da flag — continua íntegro e está fixado por teste
   (`test_replay_is_the_reversibility_that_survived`).
3. **Duas rotas de tick custam caro em silêncio.** Cada Engine novo precisava
   ser pensado nas duas, cada teste corria o risco de exercitar a errada, e a
   rota morta ia envelhecendo sem que ninguém percebesse.

O que NÃO se perdeu: o histórico. O código do adaptador e dos subsistemas está no
git, e os ADRs 0008/0010/0011 descrevem o que ele fazia e por quê.

### 4. `build_planet_engine` mora em `engines/composition.py`, não em `engines/planet/`

O Planet Engine não conhece Engine algum — orquestra o que lhe entregam, e há um
contrato de import-linter que faz disso um erro de build. Pôr a fábrica dentro de
`engines/planet/` violaria justamente o contrato que ela deveria respeitar.

`engines/composition.py` é o oposto: conhece todos os oito, e é o único módulo
dentro de `engines/` que conhece. `engines/bridge.py` (tradução
`PlanetState` ↔ `WorldStateSnapshot`) o acompanha pelo mesmo motivo.

### 5. A ordem de acoplamento deixou de ser documentação e virou verificação

`SUBSYSTEM_ORDER` era uma constante que descrevia a ordem correta; nada impedia
que a fábrica montasse outra. `ENGINE_ORDER` é acompanhada de `validate_graph`,
que recusa no boot qualquer leitura para trás não declarada em `lagged_reads`.

A diferença prática: no modelo antigo, reordenar dois subsistemas produzia uma
simulação silenciosamente diferente. Agora produz um erro na subida.

### 6. A ciência por domínio saiu do YAML global

Os blocos `physics`/`chemistry`/`climate`/`geology`/`ocean`/`life` saíram de
`configs/simulation_params.yaml` (versão 3 → 4). Cada Engine carrega o próprio
`params.yaml` versionado, co-locado com o código que o consome (Spec §5.1).

Ficou no arquivo global o que NÃO pertence a Engine algum: condições iniciais,
faixas físicas, progressão de eras, orçamento da moldura e os parâmetros da
camada emergente — que não é um Engine e não teria onde morar.

O cabeçalho do YAML traz o mapa de para onde cada bloco foi, para que quem
procurar um parâmetro pelo nome antigo o encontre.

### 7. A remoção é verificada, não declarada

`tests/integration/test_legacy_removed.py` afirma que os módulos não importam,
que **nenhum arquivo do `src/` ainda os importa** (varredura de AST), que a flag
não existe em `Settings`, que o composition root tem uma rota só, e que toda
fatia tem dono.

Sem isso, "removido" é um estado que dura até o primeiro merge distraído. O teste
já se provou útil na própria implementação: pegou diretórios `__pycache__`
sobreviventes que tornavam `engines.legacy` importável como namespace package
vazio — um import que teria voltado a funcionar sem erro.

## Consequências

+ Uma rota de simulação, uma ordem de acoplamento, um lugar para cada parâmetro.
+ Todo Engine novo é pensado uma vez, não duas.
+ A ordem de acoplamento é verificada no boot em vez de documentada.
+ O composition root ficou trivial: monta os oito Engines e entrega.
− **Sem rollback para a ciência pré-M1.** Deliberado (§3). A rede é o replay.
− A suíte perdeu os testes de paridade legado × moldura e os dos subsistemas
  removidos. Eles testavam código que não existe; mantê-los seria manter o código.
− `WORLD_STATE_VERSION` sobe para 2 (ADR 0012): checkpoints da versão 1 não são
  legíveis, e não há caminho de migração — a `LegacySlice` que eles carregam não
  tem para onde ir sem inventar dados.
