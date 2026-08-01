# ADR 0017 — Biologia opcional, e a retirada do fitness global em quatro tempos

## Status
Partes (1) e (2): **aceitas e implementadas**.
Parte (3): sequência de quatro tempos **aprovada**; o tempo 1 está implementado,
o tempo 2 está **bloqueado** por um achado de modelagem (ver "O BLOQUEIO"), e os
tempos 3 e 4 dependem dele.

Fecha o M3 junto com o **ADR 0016**. Referências: ADR 0006, ADR 0007 (import
preguiçoso do ARQ), ADR-ARCH-0001, ADR-ARCH-0002, RF-031, DEC-01/DEC-04/DEC-16 da
Especificação do Evolution Engine, e a auditoria de conformidade de 2026-07-29.

## Contexto

O M3 substituiu o Biota provisório por Evolution + Ecology Engines, com seleção
local e sem função de aptidão global (ADR 0016). Ao verificar as guardas do M3,
três coisas apareceram que não estavam no plano — e a terceira é a mais séria de
todo o marco.

## Decisão

### 1. O extra `sim` volta a ser realmente opcional

`pyproject.toml` declara `sim` (`mesa`, `deap`, `scipy`, `networkx`) como extra
**opcional**, e o walking skeleton depende disso: sem ele, o serviço roda com
adaptadores in-memory. Não era verdade.

A cadeia era esta:

```
engines/composition.py
  → simulation_engine/params.py        (para montar SimulationParams)
    → biology/evolution.py             (para EvolutionParams)
      → from deap import base, creator, tools     ← no TOPO do módulo
```

Ou seja: **o `deap` era requisito de importação de toda a física.** O serviço não
subia sem um pacote declarado opcional, e nada apontava isso porque nenhum teste
rodava sem o extra instalado.

A fábrica `_deap()` (`@lru_cache(maxsize=1)`, mesma técnica do `_mesa_classes()`)
move o import e o registro das classes do `creator` para dentro da execução. O
`deap` continua obrigatório para o AG por era — o que muda é **quando** ele é
exigido.

`tests/unit/test_app_boots_without_sim.py` fixa isso, em **subprocesso**: os nove
Engines importam e rodam 120 ticks com `mesa`, `deap`, `scipy` e `networkx`
bloqueados. O subprocesso não é preciosismo — bloquear o import no processo do
pytest exigiria expurgar `ecosfera_ai` do `sys.modules`, o que reexecuta o
registro de métricas do Prometheus e falha com `Duplicated timeseries`. O defeito
seria do teste.

O mesmo arquivo afirma o contraponto: `_deap()` **continua** levantando
`ImportError` sem o extra. Sem isso, alguém concluiria que o extra virou
supérfluo.

### 2. O Ecology Engine não envolve o ABM — ele PORTA a ciência

A intenção original era envolver `simulation_engine/biology/ecology.py` atrás de
uma fábrica preguiçosa. O Engine entregue não faz isso, e a docstring dizia que
fazia. A docstring estava errada, não o código.

O motivo de o porte ser o desenho certo: o ABM opera sobre **populações por
espécie**; o Engine opera sobre **três agregados tróficos**, que é o que cabe no
Canal A (aditivo, de floats). Envolvê-lo exigiria materializar a lista de
espécies a cada tick só para agregá-la de volta — custo e complexidade para
produzir o mesmo número.

Consequência prática: o Ecology Engine não importa `mesa` de forma alguma, e é
por isso que os nove Engines rodam sem o extra. O ABM com `mesa` segue vivo no
caminho de biologia por era.

### 3. Retirada do fitness global em QUATRO TEMPOS

Existem hoje **dois caminhos de biologia com ciência incompatível no mesmo
binário**, e o inválido estava ligado por padrão.

| | Caminho A (Engine) | Caminho B (legado, por era) |
| --- | --- | --- |
| onde | `engines/evolution` + `engines/ecology` | `simulation_engine/biology/` |
| cadência | por tick, dentro do `ENGINE_ORDER` | por era, via `EvolveBiologyUseCase` |
| ciência | seleção local, sem fitness | **AG do DEAP, `selTournament` sobre aptidão escalar** |
| produto | fatias + eventos do Canal B | **códex de espécies** (tabela `species`) |
| gate | nenhum (roda sempre) | `ECOSFERA_BIOLOGY_ENABLED` |

**Isto já havia sido auditado, de forma independente.**
`docs/evolution-engine/00-auditoria-conformidade.md` (2026-07-29) examinou esses
arquivos contra a Especificação do Evolution Engine e concluiu **"não mesclar"**
para `fitness.py`, `evolution.py`, `ecology.py` e `engine.py` (violam DEC-01,
DEC-16, DEC-05, DEC-06), e desaconselhou explicitamente subir com a flag ligada:

> O que eu não recomendo é mesclar com a flag ligada: isso publica como
> "emergente" um comportamento que a especificação classifica como
> cientificamente inválido, e o tutor de IA passaria a explicar ao estudante uma
> dinâmica que não é o que o texto diz ser.

A DEC-01 ("não existe função de aptidão em nenhum ponto") é a mesma decisão que o
ADR 0016 aplicou ao Engine novo. O M3 chegou ao mesmo veredito por outro caminho.

#### A decisão NÃO é escolher entre três opções

As saídas consideradas não estão no mesmo nível — tratá-las como alternativas
mutuamente exclusivas seria um falso trilema. **Desligar a flag é contenção**
(para o sangramento); **decidir o destino do caminho B é arquitetura**; **remover
o DEAP é consequência**. A decisão é uma SEQUÊNCIA:

**Tempo 1 — `biology_enabled=False` por padrão. FEITO.**
Contenção imediata, commit isolado. Não decide nada sobre o caminho B: apenas
impede que ciência sabidamente inválida rode sem alguém a ter pedido. O custo
aceito é que `/species` passa a exigir a flag — o estado honesto é "o catálogo
antigo está desativado porque sua ciência é inválida; o novo está sendo ligado".
A biologia emergente **não depende desta flag** e segue rodando no tick.

**Tempo 2 — reparentar o códex sobre os eventos do Evolution Engine. BLOQUEADO.**
Ver "O bloqueio encontrado", abaixo.

**Tempo 3 — remover `simulation_engine/biology/`**, quando nada mais o consumir.
Fecha a cadeia de migração: `RF-031 (AG global) → ADR-ARCH-0001 (emergente) →
M3 (sem DEAP no Engine) → aqui (o último DEAP do serviço morre)`. O caminho B é o
último reduto do fitness global; removê-lo torna a proibição da DEC-01 verdadeira
**no código**, e não só nos Engines.

**Tempo 4 — religar `biology_enabled=True`**, quando o único caminho existente
for o emergente. A flag volta a ligar biologia, e só há a biologia certa para
ligar.

Entre o tempo 1 e o tempo 4 a única biologia que roda por padrão é **nenhuma**
(flag desligada) ou **a emergente** (após o reparenting). O caminho DEAP não
executa por padrão a partir do tempo 1.

#### Por que rejeitamos deletar o caminho B agora

Deletar direto (sem reparentar) parecia mais simples e é mais caro de viver:

- **Custo do códex.** O `/species` ficaria vazio por um marco inteiro.
- **Eventos órfãos — o pior dos dois.** Pior que a funcionalidade sumida é a
  RAZÃO de ela sumir: o Evolution Engine continuaria emitindo
  `SpeciationOccurred`/`SpeciesExtinct` que **ninguém projeta em lista nenhuma**.
  Ficaríamos com a trilha (o "por quê") sem o catálogo (o "o quê"), e o Tutor
  explicaria "a espécie X foi extinta" sem conseguir listar quais espécies
  existem. É a mesma família dos furos silenciosos desta rodada — o `solar_flux`,
  a `biomass` — agora do lado read-side: nada estoura, e uma pergunta básica do
  usuário deixa de ter resposta.
- **Irreversibilidade.** Reparentar é incremental e reversível; deletar é
  arqueologia se o M4 precisar de algo que vivia lá. Entre duas opções que chegam
  ao mesmo lugar (caminho B morto), ganha a que preserva funcionalidade e é
  reversível.

#### O BLOQUEIO encontrado no tempo 2

A verificação pedida antes de reparentar — *"o envelope de evento do Evolution
carrega tudo que o códex precisa?"* — respondeu **não**, e por um motivo
diferente do previsto.

O genoma **está** lá: `LifeEmerged` e `SpeciationOccurred` carregam os seis
traços em `cause_detail` como `gene_*`. O que falta é mais fundo:

| `SpeciesOut` precisa | O evento carrega? |
| --- | --- |
| `genome` (6 traços) | **sim** (`gene_*` no `cause_detail`) |
| `emerged_era` | sim (`occurred_at.era`) |
| `trophic_class` | sim (derivável do genoma) |
| `species_id` | **NÃO** |
| `population` (por espécie) | **NÃO** (só a biomassa da comunidade) |
| `ancestor_id` (linhagem) | **NÃO** |
| `fitness` | não — e **não deve** existir (DEC-01) |

A causa não é o envelope estar magro. É que **o Evolution Engine não tem
espécies.** Ele modela a comunidade como **um genoma médio** (ADR 0016, §2), e
todo evento seu nomeia `species:community` ou `species:founder`.
`species_richness` é um `float` escalar na fatia — uma contagem, não um conjunto
de identidades. `SpeciationOccurred` significa *"o genoma médio da comunidade
divergiu além do limiar"*, e **não** *"a espécie X nasceu da espécie Y"*.

Uma projeção só pode projetar o que existe a montante. Não há como derivar um
catálogo de espécies coexistentes, com população e linhagem, de uma série de
eventos sobre uma média.

**A saída prevista não resolve, e teria criado um problema pior.** A hipótese era
"o Engine escreve no repositório do códex ao emitir o evento". Isso quebraria a
pureza do Engine: `tick()` é função pura do snapshot — é disso que o replay
bit-a-bit depende —, e Engines não têm portas de I/O por desenho
(ADR-ARCH-0001). O sink de observabilidade só é chamado **depois** que o tick
fecha, e pelo Planet Engine, justamente para manter a medição fora do caminho
determinístico. Um Engine gravando num repositório no meio do tick é exatamente o
canal lateral que a moldura proíbe.

As saídas reais, para decisão:

1. **Redefinir o códex como LINHAGEM da comunidade** (mais barata, honesta).
   Cada `LifeEmerged`/`SpeciationOccurred` abre uma entrada com o genoma médio
   daquele momento; `SpeciesExtinct` fecha. `ancestor_id` é a entrada anterior;
   `population` é a biomassa da comunidade. O `/species` passa a mostrar uma
   **cadeia filogenética no tempo**, não um censo de espécies coexistentes — e o
   schema muda de significado (`fitness` sai). Numa corrida de 320 ticks isso dá
   poucas entradas, o que é pouco material pedagógico.
2. **Dar coortes por espécie ao Evolution Engine** (a que a auditoria pede: DEC-04,
   coortes em arrays colunares, malha geodésica). Aí a especiação produz
   identidades de verdade e o códex volta a ser um censo. É a reescrita de escala
   M4 que a própria auditoria chama de "distância de arquitetura, não de
   refatoração".
3. **Emitir eventos por espécie.** Rejeitada: não há espécies a nomear no modelo
   de média, e contraria a granularidade agregada padrão (ADR-ARCH-0002, Corr. 2).

Os tempos 3 e 4 dependem do tempo 2 e seguem bloqueados: não se remove o caminho
B enquanto ele for a única fonte do códex, nem se religa a flag antes de existir
biologia válida para ligar.

## Consequências

**Ganhamos.** O extra `sim` volta a ser opcional de fato, verificado e não apenas
declarado. A ciência inválida deixou de rodar por padrão — o que era o risco
concreto, e está fechado desde o tempo 1.

**Perdemos.** O import preguiçoso troca uma falha no boot por uma falha na
primeira execução do AG por era — mesmo compromisso já aceito no ADR 0007 para o
ARQ, com teste que mantém a exigência visível. E o `/species` passa a exigir a
flag até o tempo 2 concluir.

**Fica em aberto** a escolha entre "códex como linhagem" e "coortes por espécie".
Ela não é de implementação: decide o que o `/species` SIGNIFICA para o estudante,
e por isso volta para o dono do produto.
