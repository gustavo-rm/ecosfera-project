# Auditoria de conformidade — Evolution Engine

**Documento de referência:** Especificação Técnica Oficial do Evolution Engine (SSOT da parte biológica).
**Alvo auditado:** `services/ai-sim-service`, branch `claude/ecosfera-ai-next-increment-9la1q4` (PR #6, **aberto e não mesclado**).
**Base de comparação:** `feature/AI-simulation-service-development` — **sem nenhum código biológico**.
**Data:** 2026-07-29. **Etapa:** 2 de 4 (auditoria; nenhuma correção aplicada).

---

## 0. Resumo executivo

Três fatos governam todas as recomendações abaixo.

**Primeiro: toda a biologia existente está num PR ainda não mesclado.** Nada disso está em `main` nem na branch de integração. As violações identificadas são, portanto, **baratas de corrigir agora e caras depois** — a janela para decidir é esta.

**Segundo: as duas violações mais graves são estruturais, não de detalhe.** Existe uma função de aptidão escalar decidindo quem se extingue (DEC-01) e um agente lendo um agregado global como entrada da própria regra (DEC-16). A especificação classifica ambas como invalidantes: a §3.3 diz que "o problema não é a imprecisão da fórmula; é a existência dela", e a DEC-16 diz que sua violação "invalida cientificamente todos os resultados do motor".

**Terceiro: o modelo de dados existente e o especificado não são o mesmo sistema.** A biologia atual é **agregada por espécie, 0-D, em objetos Python**. A especificação exige **coortes de organismos, espacializadas em malha geodésica, em arrays colunares NumPy**. Isso não é distância de refatoração; é distância de arquitetura.

Contagem: **2 conformes, 2 parciais, 6 divergentes, 8 ausentes** de 18.

---

## 1. Tabela de conformidade DEC-01 … DEC-18

Legenda de esforço: **P** ≤ 1 sessão · **M** 2–3 sessões · **G** 4+ sessões · **—** não se aplica ainda.

| DEC | Decisão normativa | Situação | Evidência (arquivo:linha) | Esforço | Recomendação |
|---|---|---|---|---|---|
| **DEC-01** | Aptidão endógena; **não existe função de aptidão em nenhum ponto** | **DIVERGENTE** (estrutural) | `biology/fitness.py:1-101` define `environmental_fitness()→float`; usada para decidir extinção em `biology/evolution.py:326`, viabilidade de espécie nova em `:305` e seleção do melhor genoma em `:288` | **G** | **Não mesclar.** Ver §2.1 |
| **DEC-02** | Genoma paramétrico, modular, tipado | **PARCIAL** | `biology/genome.py:31-50` — paramétrico e tipado, mas **6 traços** contra os **57 loci** do Apêndice A, e sem organização em blocos funcionais (§10.3) | M | Próxima fatia |
| **DEC-03** | Genoma **diploide** com mapa de dominância | **AUSENTE** | `genome.py` é haploide: um valor por traço, sem par de alelos nem flag de dominância | M | Próxima fatia |
| **DEC-04** | Malha geodésica icosaédrica (nível 5 = 10 242 células) | **AUSENTE** | Nenhuma estrutura espacial no repositório: `grep -riE "grid\|mesh\|geodes\|cell\|neighbour"` em `src/` retorna vazio. O mundo é **0-D** | **G** | Fatia 1 |
| **DEC-05** | Coortes de super-indivíduos com teto adaptativo | **DIVERGENTE** | `biology/ecology.py:79-95`: o agente é uma **população de espécie inteira** sem genótipo individual nem fator de coorte. Destrói a hereditariedade particulada exigida por C4 (§3.1) | **G** | Fatia 1 |
| **DEC-06** | Passo síncrono com **gerações sobrepostas** | **DIVERGENTE** | `biology/evolution.py:247` — `population = offspring`: substituição em bloco, o modelo geracional que a DEC-06 rejeita explicitamente | M | Ver §2.3 |
| **DEC-07** | Modo reprodutivo como gene facultativo | **AUSENTE** | Só há reprodução assexuada implícita; nenhum gene `reproductive_mode` | M | Fatia futura |
| **DEC-08** | Espécie emergente, detectada **dentro de M7** | **DIVERGENTE** | `biology/evolution.py:296-318`: especiação decidida **dentro do motor evolutivo** por limiar de distância genética; sem critério de fluxo gênico nem persistência por N ticks; `SpeciesRecord` é entidade de negócio, não do observador | M | Fatia futura |
| **DEC-09** | Taxas de mutação auto-adaptativas com limites duros | **AUSENTE** | `evolution.py:59-60`: `mutation_rate`/`mutation_sigma` são constantes de configuração, não meta-genes herdáveis | M | Fatia futura |
| **DEC-10** | Necessidades em três níveis (recurso / necessidade / capacidade) | **AUSENTE** | Não há recursos nem necessidades fisiológicas; a única grandeza é `carrying_capacity`, um escalar | **G** | Fatia 1 (nível 1) |
| **DEC-11** | Matéria conservada, energia dissipativa | **AUSENTE** | Nenhum orçamento de matéria. Populações crescem/decrescem sem contrapartida em estoque; `ecology.py:122-124` cria biomassa do nada | **G** | Fatia 1 |
| **DEC-12** | Fluxos aleatórios **independentes por subsistema** (PCG64) | **PARCIAL** | Determinismo existe e é testado, mas: `evolution.py:28,84` usa o **`random` global** do Python (salvo/restaurado); `ecology.py:108` usa `model.random` do Mesa. São **dois fluxos acoplados**, não um por subsistema | M | Ver §2.4 |
| **DEC-13** | Arbitragem por utilidade com pesos genéticos | **AUSENTE** | Nenhum comportamento; agentes não escolhem ações | **G** | Fatia futura |
| **DEC-14** | Morfologia escalar com alometria | **AUSENTE** | `genome.py` tem `size`, mas nenhuma consequência alométrica derivada dele | M | Fatia futura |
| **DEC-15** | Distúrbios estocásticos periódicos obrigatórios | **AUSENTE** | Nenhum gerador de distúrbios na camada biológica | M | Fatia futura |
| **DEC-16** | **Regra de Ouro** — nada de M7 volta como entrada de M1–M6 | **DIVERGENTE** (estrutural) | `biology/ecology.py:121` — `occupied = self.model.total_producer_population()`, agregado global de **toda a população**, usado na regra de crescimento do próprio agente (`:122-124`). Também `:117` (`producer_capacity`) e `:129` (`prey_available`) | M | **Não mesclar.** Ver §2.2 |
| **DEC-17** | Estado serializável com retomada determinística, **incluindo o estado dos RNGs** | **PARCIAL** | Checkpoints + replay existem e são verificados (`application/simulation/replay_state.py:38-56`), mas o replay **recomputa** em vez de retomar, e **o estado interno dos geradores não é persistido** — exatamente o detalhe que a DEC-17 chama de "o que normalmente se esquece" | M | Próxima fatia |
| **DEC-18** | Banco de sementes com dormência | **AUSENTE** | Inexistente | M | Fatia futura |

### Invariantes conformes (o que já está certo)

| Invariante | Situação | Evidência |
|---|---|---|
| **Barreira germinativa** (§9.1) — nada adquirido em vida entra no genoma | **CONFORME** | `grep -rn "replace(.*genome"` não retorna nada; `codex.py:41` só altera população/aptidão, nunca o genoma. A herança é estritamente genética |
| **Determinismo sob semente fixa** (§24.2) | **CONFORME** (no escopo atual) | `tests/unit/test_evolution_determinism.py` — mesma semente reproduz a sequência; há teste de vazamento do `random` global |
| **Fronteira determinístico × IA** (ADR 0006 local) | **CONFORME e reaproveitável** | `tests/unit/test_deterministic_layer_unaffected.py` compara campo a campo com biologia ligada/desligada. É o embrião correto do teste da Regra de Ouro |

---

## 2. As quatro divergências que exigem decisão sua

### 2.1 DEC-01 — a função de aptidão (a mais cara)

**O que existe.** `fitness.py` calcula um escalar de qualidade por genoma, e esse escalar decide:

```python
# evolution.py:326 — quem se extingue
if record.fitness < self._p.extinction_fitness or record.population < ...:
    gone = record.extinguished(era)

# evolution.py:305 — quem chega a existir
if fitness < self._p.extinction_fitness:
    continue  # inviável ao nascer: não vira espécie

# evolution.py:288 — quem representa a espécie
best = max(candidates, key=lambda g: self._fitness_of(g, state, 0.0))
```

**Por que não é ajustável.** A §3.3 é categórica: *"nenhum módulo do motor pode conter uma função que retorne uma medida escalar de qualidade de um organismo e a use para decidir quem se reproduz"*. Renomear `fitness` para `adequação` ou movê-la de arquivo não muda nada — o que a especificação proíbe é o **mecanismo**: um critério a priori substituindo a termodinâmica local.

**O que a especificação quer no lugar.** Um organismo morre porque seu reservatório de energia chegou a zero, não porque um número ficou abaixo de um limiar. Isso exige o que hoje não existe: recursos finitos, ingestão, imposto metabólico e um estoque de energia por organismo.

**Contexto honesto:** escrevi esse código no Incremento 3 sob um enunciado que pedia explicitamente "Algoritmo Genético (DEAP)" com "função de aptidão". A especificação que você anexou **rejeita esse paradigma por decisão registrada**. Não há como conciliar os dois; um dos documentos tem de ceder, e a §23.2 diz que quem cede não é a especificação sem uma nova DEC.

**Recomendação: corrigir agora, não mesclando.** A correção não é editar `fitness.py` — é substituí-lo por metabolismo, que é a Fatia 1 do roteiro.

### 2.2 DEC-16 — Regra de Ouro violada

```python
# ecology.py:121-124
occupied = self.model.total_producer_population()   # agregado de TODA a população
self.population += params.growth_rate * self.population * (1.0 - occupied / capacity)
```

O agente decide seu próprio crescimento a partir de um censo global. A DEC-16 chama isso de onisciência concedida: *"todo padrão coletivo que ele produzir será consequência da onisciência concedida, não descoberta do sistema"*.

Detalhe agravante: as oscilações predador-presa que documentei como "emergentes" no PR #6 **dependem** desse agregado. Elas são, em rigor, um Lotka-Volterra implícito escrito com outra sintaxe — não emergência.

**Recomendação: corrigir agora.** A forma certa é o agente ler apenas a `LocalView` da sua célula (§21.2). Sem malha (DEC-04), porém, "local" não tem significado — o que amarra esta correção à Fatia 1.

### 2.3 DEC-06 — substituição em bloco

`evolution.py:247` (`population = offspring`) descarta a população inteira a cada geração. A DEC-06 rejeita isso por dois motivos: é irrealista e *"viola a exigência de gradualidade da seleção cumulativa (§3.2), porque descarta simultaneamente todo o acúmulo da população anterior"*.

**Recomendação: cai junto com DEC-01.** O laço geracional do DEAP some quando a reprodução passa a ser consequência de excedente energético.

### 2.4 DEC-12 — fluxos de aleatoriedade

O motor é reprodutível, mas por um mecanismo frágil: salvar/restaurar o `random` **global** do Python em volta da chamada do DEAP (`evolution.py:80-88`). Funciona, e há teste de vazamento — mas viola o espírito e a letra da DEC-12, que exige um fluxo PCG64 **independente por subsistema** justamente para que "acrescentar uma chamada aleatória no módulo de movimento" não desloque a sequência de mutações.

**Recomendação: corrigir na próxima fatia.** É barato (`np.random.Generator` por subsistema, derivado por `SeedSequence` — padrão que o `TickOrchestrator` **já usa** em `simulation_engine/orchestrator.py:59`) e não bloqueia a Fatia 1.

---

## 3. Onde nenhuma DEC foi violada — e por quê importa

A camada **determinística** (`physics`, `chemistry`, `climate`, `geology`, `ocean`) e a infraestrutura de **timeline/persistência/fila** foram construídas sob outras decisões (ADRs 0003–0007 locais) e **não conflitam** com a especificação. Elas são o substrato que a §5.12 pressupõe: *"o Evolution Engine é consumido pelo ai-sim-service, que o invoca dentro do orquestrador de tick"*.

Reaproveitável sem alteração:

- `TickOrchestrator` + `SeedSequence` — o padrão de RNG que a DEC-12 pede;
- timeline com checkpoints append-only + replay verificado — base da DEC-17;
- porta `JobQueue` + worker ARQ — a §22.6 vai precisar disso;
- migrations Alembic no schema `simulation`;
- o teste de fronteira determinístico × IA — molde do teste da Regra de Ouro (§24.2).

---

## 4. Recomendação sobre o PR #6

Reafirmo a opção **(c)** com o detalhamento que a auditoria permite:

| Componente | Ação | Motivo |
|---|---|---|
| `biology/fitness.py`, `evolution.py`, `ecology.py`, `engine.py` | **não mesclar** | Violam DEC-01, DEC-16, DEC-05, DEC-06 |
| `biology/genome.py`, `codex.py` | **não mesclar como estão** | Haploide (DEC-03) e 6 loci contra 57; viram insumo do Apêndice A |
| `infrastructure/jobs/*`, migration `0003`, `ports/job_queue.py` | **mesclar** | Conformes e necessários |
| Endpoints `/species`, `/ecology`, `/jobs` | **mesclar atrás de flag** | Contrato útil; hoje serviriam dados de um motor que será substituído |
| `ECOSFERA_BIOLOGY_ENABLED=false` como padrão | **mesclar** | Desliga a camada divergente sem removê-la |

Alternativa se houver compromisso de entrega do Inc 3: **mesclar tudo com `BIOLOGY_ENABLED=false` por padrão** e registrar esta auditoria como dívida vinculada. Preserva a entrega, não expõe o motor divergente, e evita reescrever o PR. O custo é conviver com ~980 LOC que serão descartados.

**O que eu não recomendo** é mesclar com a flag ligada: isso publica como "emergente" um comportamento que a especificação classifica como cientificamente inválido, e o tutor de IA passaria a explicar ao estudante uma dinâmica que não é o que o texto diz ser.

---

## 5. Nenhuma DEC nova é necessária

Avaliei se alguma decisão do documento é inviável na prática e **não encontrei nenhuma** que exija supersessão pela §23.2. As divergências são todas de implementação, não de especificação: o código foi escrito antes do documento existir, sob um enunciado que pedia o paradigma oposto.

Duas observações para vigiar adiante, sem propor mudança agora:

1. **Custo da malha × coortes.** 10 242 células (DEC-04) × coortes (DEC-05) com tick em dezenas de milissegundos (§22.6) é exigente para Python+NumPy. Se a Fatia 1 mostrar que o orçamento não fecha no nível 5, o caminho correto é uma DEC-19 ajustando o **nível de subdivisão padrão** — parâmetro que a própria DEC-04 já declara configurável —, não abandonar a malha.
2. **DEC-08 e a estabilidade de identidade na UI.** Espécie detectada em M7 com confirmação por N ticks significa que o códex do estudante pode ver uma linhagem "virar espécie" retroativamente. É consequência aceita da decisão, mas precisa de tratamento de produto na UI.

---

## 6. Próximo passo

Aguardo sua revisão desta auditoria e a decisão sobre o PR #6 antes de executar a **Etapa 3** (esqueleto de `packages/evolution-engine/`, contratos tipados, 57 loci e parâmetros como dados, testes de invariante em `xfail`).
