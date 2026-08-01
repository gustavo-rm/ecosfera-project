# ADR 0017 — Biologia opcional, imports preguiçosos, e a dívida dos dois caminhos

## Status
Aceito quanto às partes (1) e (2). A parte (3) é **dívida registrada, não
resolvida** — precisa de decisão explícita antes do M4. Fecha o M3 junto com o
**ADR 0016**. Referências: ADR 0006, ADR 0007 (import preguiçoso do ARQ),
ADR-ARCH-0001, RF-031.

## Contexto

O M3 substituiu o Biota provisório por Evolution + Ecology Engines, com seleção
local e sem função de aptidão global (ADR 0016). Ao verificar as guardas do M3,
três coisas apareceram que não estavam no plano.

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

### 3. DÍVIDA — existem DOIS caminhos de biologia, e um deles contradiz o ADR 0016

Este é o achado que precisa de decisão, e por isso está registrado em vez de
resolvido no impulso.

| | Caminho A (novo) | Caminho B (legado) |
| --- | --- | --- |
| onde | `engines/evolution` + `engines/ecology` | `simulation_engine/biology/` |
| cadência | por tick, dentro do `ENGINE_ORDER` | por era, via `EvolveBiologyUseCase` |
| ciência | seleção local, sem fitness | **AG com fitness global, `selTournament`** |
| produto | fatias + eventos do Canal B | **códex de espécies** (tabela `species`) |
| ligado | sempre | `ECOSFERA_BIOLOGY_ENABLED` |

**Os dois estão ativos agora**, e o caminho B está ligado **por padrão**
(`biology_enabled: bool = Field(default=True)`). Ele é alcançado por `deps.py` →
`get_biology_engine()` → `BiologyEngine(EvolutionEngine(...), ...)`, e é ele que
popula o códex de espécies e alimenta o resumo de era.

**Isto já havia sido auditado, e de forma independente.**
`docs/evolution-engine/00-auditoria-conformidade.md` (2026-07-29) examinou
exatamente esses arquivos contra a Especificação do Evolution Engine e concluiu:

> | `biology/fitness.py`, `evolution.py`, `ecology.py`, `engine.py` |
> | **não mesclar** | Violam DEC-01, DEC-16, DEC-05, DEC-06 |

e, sobre a flag:

> O que eu não recomendo é mesclar com a flag ligada: isso publica como
> "emergente" um comportamento que a especificação classifica como
> cientificamente inválido, e o tutor de IA passaria a explicar ao estudante uma
> dinâmica que não é o que o texto diz ser.

A DEC-01 ("não existe função de aptidão em nenhum ponto") é a mesma decisão que o
ADR 0016 aplicou ao Engine novo. O M3 chegou ao mesmo veredito por outro caminho
— o que confirma o diagnóstico e torna a pendência mais urgente, não menos.

Por que isto não é apenas desarrumação:

- **Contradiz a regra de ouro do M3 dentro do mesmo serviço.** Um estudante pode
  receber uma explicação derivada de um ótimo escolhido por torneio — exatamente
  a concepção teleológica que o ADR-ARCH-0001 superou.
- **Os dois podem discordar.** O Engine diz biomassa X com genoma médio G; o job
  diz que o códex tem espécies com genomas ranqueados por aptidão. Nada
  reconcilia os dois números, e nada detecta a divergência.
- **Trava a remoção do `deap`.** Enquanto o caminho B viver, o extra `sim`
  precisa do `deap`.

**Por que não resolvemos agora.** Apagar o caminho B removeria o **códex de
espécies** — a tabela `species`, os registros de especiação e extinção com nome,
o "quem está vivo neste planeta" que é a carga pedagógica do M4. Os eventos do
Canal B do Evolution Engine já carregam o genoma no `cause_detail`, então o códex
PODE ser reconstruído como projeção — mas essa projeção não existe, e apagar
antes de construí-la deixaria um buraco funcional.

As três saídas, com a recomendação:

1. **Reparentar o códex sobre os eventos do Evolution Engine** (recomendada). O
   caminho B para de fazer evolução e vira projeção de
   `SpeciationOccurred`/`SpeciesExtinct`/`MassMortality`. O fitness global e o
   `deap` saem; o códex sobrevive. É o desenho que o ADR 0016 já pressupõe ao
   dizer que "a composição por espécie é materializada no códex a partir dos
   eventos".
2. **Apagar o caminho B inteiro.** Mais simples e mais rápido, mas custa o códex
   até que o M4 o reconstrua.
3. **Manter os dois.** Rejeitada: deixa o fitness global vivo em produção,
   contradizendo o próprio milestone e a recomendação explícita da auditoria.

Há ainda uma **medida provisória**, ortogonal às três: virar o padrão de
`biology_enabled` para `False`. Ela não decide nada — só impede que o caminho
cientificamente inválido rode sem alguém tê-lo pedido, que é literalmente o que a
auditoria recomenda. O custo é que o códex de espécies e as rotas `/species`
passam a exigir a flag ligada, o que é mudança de comportamento visível ao
produto. Por isso **não foi aplicada** no M3: é decisão de produto, não de
implementação.

Até a decisão, o caminho B permanece **como está** — não foi ampliado nem
recebeu ciência nova no M3.

## Consequências

**Ganhamos.** O extra `sim` volta a ser opcional de fato, verificado e não
apenas declarado. A moldura inteira roda numa instalação mínima, o que é o que o
walking skeleton do Inc 0/1 prometia.

**Perdemos.** O import preguiçoso troca uma falha no boot por uma falha na
primeira execução do AG por era. É o mesmo compromisso já aceito no ADR 0007 para
o ARQ, e o teste que exige o `ImportError` mantém a exigência visível.

**Fica em aberto** a parte (3), acima. Enquanto ela não for decidida, o serviço
contém duas biologias com ciências incompatíveis, e essa é a dívida mais
importante que o M3 deixa para o M4.
