# Plano de Evolução do ECOSFERA

> Documento-base para orientar futuras alterações no código. Não contém código, pseudocódigo nem tarefas. Cada decisão é rastreável às fontes.
> **Convenção de origem:** `[Doc]` = afirmado nos documentos · `[Inf]` = inferência/recomendação deste plano · `[Compl]` = conhecimento científico complementar · `[Ctx]` = contexto conhecido do projeto usado só para tornar a decisão acionável.

---

## 1. Objetivo

Consolidar as validações e correções levantadas nos dois questionários (fase 1 e fase 2) em um conjunto de decisões e requisitos que aumentem o rigor científico, a qualidade pedagógica e a coerência da simulação do ECOSFERA — sem inflar a complexidade do sistema. A prioridade é a qualidade das decisões, não a cobertura exaustiva dos documentos.

## 2. Fontes analisadas

- **Documento A — Questionamentos fase 1:** validação científica dos mecanismos já existentes (evolução, ecologia, ciclos físicos). Blocos 0–3. Contém resposta do **Especialista (Tássia, Biologia)** e análise complementar de um **LLM**.
- **Documento B — Questionamentos fase 2:** decisão central sobre representação da vida (comunidade × espécies), o Tutor, e questões de carbono, oxigênio, sequência e lacunas. Blocos 1–5. Mesmas duas vozes.

Regra aplicada: em questões de rigor biológico/ecológico/evolutivo, o **Especialista é a referência principal**; o LLM é usado para design instrucional e para checar coerência. Divergências foram analisadas caso a caso (Seção 4), não resolvidas por escolha automática.

## 3. Síntese das decisões

Três eixos concentram o valor:

1. **Correções conceituais no modelo de vida** — a mais importante e a mais barata: a ancestralidade **não** é "espécie A deu origem à espécie B", e sim "duas espécies compartilham um ancestral comum que sofreu especiação". A especiação deve ser **gradual e causada** (barreira geográfica, isolamento, nicho), não um limiar instantâneo. `[Doc]`
2. **Relações ecológicas são a maior lacuna** — o Especialista aponta explicitamente que cadeias lineares empobrecem a ecologia; a maioria das espécies é **generalista**. Faltam **teias alimentares, competição, mutualismo, parasitismo e decomposição**. Este é o gargalo que destrava mais aprendizagem e é pré-requisito dos impactos antrópicos. `[Doc]`
3. **Comunidade + espécies, não uma escolha** — o modelo de **comunidade/população** continua sendo o mecanismo evolutivo; **espécies com identidade** entram como camada de investigação opcional (catálogo, filogenia simplificada), enriquecendo sem substituir. `[Doc]`

Prioridade máxima declarada pelo Especialista (Bloco 5): **impactos antrópicos** — a vida (humana) transformando o planeta. `[Doc]` Este plano o posiciona **depois** das relações ecológicas, das quais depende (Seção 9). `[Inf]`

**Fronteira em relação ao M6 (Tutor):** um subconjunto pequeno destas decisões é **pré-requisito do M6**, porque o Tutor narra a ciência da simulação — se a ciência de base estiver errada, o Tutor ensina o erro com autoridade. O restante é melhoria da ciência narrada e pode vir depois. A fronteira está marcada nas Seções 8 e 9.

## 4. Comparação entre as duas análises

Comparação por questão, extraindo só convergência, divergência e a conclusão. Onde as vozes concordam, registra-se apenas a decisão.

### Onde ambas convergem (validado — Preservar)
- **Evolução não-teleológica** (Q4): erro conceitual mais comum e mais grave; vale evitar. Especialista reforça que "evoluir porque precisa" é Lamarckismo; o aceito é o Neodarwinismo (seleção natural + mecanismos genéticos de mudança na frequência de alelos). `[Doc]`
- **Aptidão contextual, não absoluta** (Q5): sobreviver conforme condições locais representa bem a seleção natural. Especialista acrescenta que é preciso deixar claro que é processo **natural e aleatório** dentro de uma população (genótipos diferentes). `[Doc]`
- **Mutação como variação não-direcionada** (Q6): correto, desde que a linguagem deixe explícito que nenhum organismo foi "escolhido". `[Doc]`
- **Oscilações predador-presa** (Q9): cientificamente reconhecíveis e valiosas; ambas recomendam **destacá-las**. `[Doc]`
- **Pirâmide de energia** (Q10): fluxo unidirecional, energia decresce por nível trófico. Correto. `[Doc]`
- **Capacidade de suporte** (Q11): o ambiente limita a vida. Correto — e o Especialista amplia: vale para **toda** espécie, não só produtores. `[Doc]`
- **Cadeia vulcanismo→CO₂→estufa→temperatura→degelo** (Q13): direção correta. `[Doc]`
- **Vida como sumidouro de carbono** (Q14): cientificamente honesto; ambas veem como diferencial do jogo (o LLM associa à hipótese de Gaia, sem teleologia). `[Doc]`
- **Defasagem temporal de um tick** (Q16): senso comum; eventos dependem de outros. Não é problema. `[Doc]`

### Divergência 1 — Carbono (fase 2, item 11): **complementar, não contraditória**
- Especialista: "não acho importante mostrar isso" (o intemperismo/termostato). `[Doc]`
- LLM: concorda que não precisa ser mecânica de ensino, mas discorda de deixar como "gambiarra interna"; defende um **ciclo geológico do carbono internamente coerente** ainda que invisível. `[Doc]`
- **Avaliação:** não há contradição — o Especialista fala de **visibilidade ao aluno**; o LLM fala de **coerência do motor**. As duas afirmações coexistem. A distinção "não ensinar ≠ não modelar" é a chave. `[Inf]`
- **Decisão:** modelar o ciclo do carbono de forma coerente internamente (fechar a instabilidade de longo prazo), **sem** apresentá-lo como conceito ao aluno. Categoria **B**. → `GEO-001`.

### Divergência 2 — Oxigênio / Grande Oxigenação (fase 2, item 12): **aparente, dissolve-se**
- Especialista (pergunta do oxigênio): "se o jogo mostrar o planeta surgindo, é preciso mostrar o oxigênio, por causa da vida". `[Doc]`
- LLM: correção — o O₂ **não** foi pré-condição da primeira vida; a Terra teve vida **antes** da Grande Oxidação, e organismos fotossintetizantes produziram o O₂ que se acumulou depois. `[Doc]`
- **Avaliação:** a contradição é só aparente. Na **própria resposta de sequência** (fase 2, Bloco 4) o Especialista dá a ordem correta: primeiro ser vivo heterótrofo → fermentação → CO₂ → fotossintetizantes → O₂ → seres complexos. Ou seja, o Especialista **também** coloca a vida antes do O₂; a fala isolada do oxigênio foi imprecisa, mas a visão dele é consistente com a correção do LLM. `[Doc]` + `[Inf]`
- **Decisão:** adotar a sequência vida→fotossíntese→acúmulo de O₂→Grande Oxidação→diversificação aeróbia. Prioridade **condicional** ao escopo de início do jogo (ver `GEO-002`).

### Divergência 3 — Predador come só o nível imediatamente abaixo (Q12): **de ênfase**
- Especialista: as relações ficam **empobrecidas**; a maioria das espécies é generalista. `[Doc]`
- LLM: aceitável como primeira aproximação; introduzir **teias** nas eras avançadas. `[Doc]`
- **Avaliação:** não contradiz — o Especialista (autoridade em ecologia) confirma que é uma lacuna **real**; o LLM oferece a **estratégia de introdução** (progressão por era). Complementares. `[Inf]`
- **Decisão:** tratar como lacuna real (prioridade alta), implementada por progressão cadeias→teias. → `ECO-001`.

### Divergência 4 — Extinção como "falha de adaptação" (Q8): **correção científica do Especialista**
- Formulação original assumia extinção = falha de adaptação. `[Doc]`
- Especialista: **equívoco** — em desastres/extinções em massa as mortes são **aleatórias** ("má sorte"), não seleção dos mais aptos. `[Doc]`
- **Avaliação:** correção importante e correta. `[Ctx]` O sistema já distingue extinção **catastrófica** (independente de aptidão) de **ecológica** — esta validação confirma que essa distinção deve ser **preservada** e explicitada ao aluno. → `BIO-006` (Preservar).

### Divergência 5 — Especiação por limiar único (Q7): **simplificação a corrigir**
- Formulação: nova espécie = divergência genética acima de um limiar. `[Doc]`
- Especialista: aborda **um único mecanismo**; existem outros (convergência, anagênese, cladogênese); e é preciso mostrar **o que causa** a divergência (barreira geográfica, isolamento reprodutivo, nichos, pressões). `[Doc]`
- LLM: a abstração por limiar é aceitável (livros também simplificam), desde que se explique o isolamento reprodutivo ao longo de gerações. `[Doc]`
- **Avaliação:** o limiar isolado é aceitável como mecânica, mas **cientificamente incompleto** se apresentado como a única forma e sem causa. O Especialista é mais exigente e tem razão no conteúdo. `[Inf]`
- **Decisão:** manter a mecânica, mas torná-la **gradual e causada**, e evitar sugerir que é o único mecanismo. → `BIO-002`.

## 5. Decisões científicas consolidadas

### 5.1 Vida e evolução
- **Ancestralidade** representada como **ancestral comum → especiação → duas espécies**, nunca "A deu origem a B". `[Doc]` (`BIO-001`)
- **Especiação gradual e causada**, dirigida por barreiras/isolamento/nichos/pressões; não instantânea; não apresentada como mecanismo único. `[Doc]` (`BIO-002`)
- **Evolução é de população**, não do indivíduo; distinguir **adaptação × evolução × especiação** para não reduzir evolução a adaptação. `[Doc]` (`PED-003`)
- **Aptidão contextual e aleatória** dentro da população — preservar. `[Doc]`
- **Extinção**: ecológica (perda de adequação) **e** catastrófica (aleatória, independente de aptidão) — preservar a distinção. `[Doc]` (`BIO-006`)

### 5.2 Ecologia
- **Teias alimentares e generalistas** substituindo (progressivamente) a cadeia linear estrita — maior lacuna apontada. `[Doc]` (`ECO-001`)
- **Relações ecológicas** além da predação: competição, mutualismo, parasitismo, herbivoria. `[Doc]` (`ECO-002`)
- **Decomposição e ciclo de nutrientes** (decompositores). `[Doc]` + `[Compl]` (`ECO-003`)
- **Capacidade de suporte em todos os níveis tróficos** — preservar. `[Doc]` (`ECO-004`)
- **Oscilações predador-presa** destacadas como fenômeno de equilíbrio. `[Doc]` (`ECO-005`)

### 5.3 Planeta e vida
- **Ciclo do carbono internamente coerente** (fecha a instabilidade de longo prazo), modelado mas **não ensinado** em detalhe. `[Doc]` (`GEO-001`)
- **Grande ciclo da água** — incluir a participação da vida (transpiração), não só o pequeno ciclo físico. `[Doc]` (`GEO-003`)
- **Vulcanismo não é hoje a maior fonte de CO₂** — contextualizar no Tutor; liga aos impactos antrópicos. `[Doc]` (`GEO-004`)

### 5.4 Evolução planetária
- **Sequência da oxigenação**: vida (heterótrofo/fermentação→CO₂) → fotossintetizantes → O₂ → saturação de sumidouros → acúmulo → **Grande Oxidação** → diversificação aeróbia. `[Doc]` (`GEO-002`)
- Tratar **origem da vida e Grande Oxidação** como reconstruções científicas, evitando apresentá-las como fato fechado onde os documentos as tratam como sequência-modelo. `[Inf]`

### 5.5 Impactos antrópicos
- **Impactos antrópicos como consequência dos mecanismos ecológicos** (desmatamento → fragmentação de habitat → perda de relações ecológicas → alteração da comunidade → alteração dos ciclos), não como camada roteirizada à parte. Prioridade máxima do Especialista, mas **dependente** das relações ecológicas existirem primeiro. `[Doc]` + `[Inf]` (`ANT-001`)

## 6. Decisões pedagógicas

- **Comunidade + espécies**: população/comunidade obrigatória como mecanismo; **catálogo de espécies** como investigação **opcional** e **poucas** espécies. `[Doc]` (`BIO-003`)
- **Progressão de complexidade**: populações durante quase todo o jogo, com **eventos ocasionais** de especiação/extinção; cadeias→teias por era; física→vida→ecossistemas. `[Doc]` (`PED-001`)
- **Aprendizagem por investigação**: hipótese, observação, evidência — reduzir respostas prontas. `[Doc]` (`PED-002`)
- **Exemplos concretos e reais** aproximam o aluno (ex.: ancestral comum de chimpanzé e ser humano). `[Doc]`
- **Baixa carga cognitiva**: evitar excesso de espécies/indicadores simultâneos. `[Doc]`

## 7. Decisões para o Tutor/IA

- **Explicações causais ancoradas no estado observável** da simulação. `[Doc]` (`TUT-001`)
- **Contraste entre espécies** ao explicar extinção ("a Alpha dependia de água fria e desapareceu; a Beta tolerava o calor e sobreviveu"). `[Doc]` (`TUT-002`)
- **Linguagem anti-teleológica**: "surgiu uma mutação aleatória" e "a característica aumentou a sobrevivência porque…"; nunca "a espécie desenvolveu resistência". `[Doc]` (`BIO-005`)
- **Adaptação ao nível cognitivo** do estudante. `[Doc]` (`TUT-004`)
- **Filogenia simplificada** como recurso do Tutor: árvore de ancestral comum, não complexa, apropriada à idade. `[Doc]` (`BIO-004`)

## 8. Requisitos consolidados

Formato: **ID · Nome · Problema · Decisão · Comportamento esperado · Escopo · Prioridade**. A coluna **Momento** indica a relação com o M6: **pré-M6** (bloqueia/condiciona o Tutor), **M6** (é o próprio Tutor), **pós-M6** (melhoria posterior).

**BIO-001 · Ancestralidade por ancestral comum** · **Momento: pré-M6**
Problema: o modelo/eventos tratam especiação como "A originou B", cientificamente incorreto. `[Doc]`
Decisão: **Modificar** — representar como ancestral comum que se divide.
Comportamento: um evento de especiação registra um ancestral e **duas** linhagens resultantes; o Tutor jamais afirma que uma espécie atual gerou outra espécie atual.
Escopo: Domínio · Simulação · Tutor/IA. Prioridade: **P0**. Justif. científica: base da ancestralidade comum.

**BIO-002 · Especiação gradual e causada** · **Momento: causa no evento pré-M6; mecânica gradual pós-M6**
Problema: especiação por limiar instantâneo, sem causa e como mecanismo único. `[Doc]`
Decisão: **Modificar/Adicionar** — divergência ao longo do tempo, disparada por causa explícita (barreira geográfica, isolamento reprodutivo, nicho, pressão ambiental).
Comportamento: a separação de populações ocorre por um gatilho observável e ao longo de gerações; o sistema não sugere que divergência-por-limiar é a única forma de especiação.
Escopo: Simulação · Domínio · Tutor. Prioridade: **P1**.

**BIO-003 · Espécies dentro da comunidade (catálogo opcional)** · **Momento: decisão pré-M6, implementação pós-M6**
Problema: hoje a vida é comunidade/genoma médio; falta a camada de espécies com identidade para investigação e biodiversidade. `[Doc]` `[Ctx]`
Decisão: **Adicionar** — camada de espécies **sobre** o mecanismo de comunidade; catálogo como atividade opcional; poucas espécies.
Comportamento: o aluno pode nomear/catalogar espécies e ver quantas existem, sem que isso substitua a dinâmica populacional; a comunidade continua sendo o motor evolutivo.
Escopo: Domínio · Simulação · Frontend · Instrumentação pedagógica. Prioridade: **P1**.
Nota: a **decisão** (comunidade+espécies) precisa estar fechada antes do M6 porque define se o Tutor fala de "comunidade" ou de "espécie X" (afeta `TUT-002`); a **implementação** da camada é pós-M6.

**BIO-004 · Filogenia simplificada** · **Momento: pós-M6**
Problema: sem representação visual de ancestralidade comum. `[Doc]`
Decisão: **Adicionar** — árvore simples de ancestral comum, apropriada à idade.
Comportamento: o aluno visualiza que duas espécies partilham um ancestral; a árvore não expõe todas as gerações.
Escopo: Frontend · Tutor/IA. Prioridade: **P2**.

**BIO-005 · Linguagem anti-teleológica** · **Momento: pré-M6**
Problema: risco de o aluno concluir "a espécie evoluiu para…". `[Doc]`
Decisão: **Modificar** (linguagem do Tutor/eventos).
Comportamento: mutações descritas como aleatórias; seleção descrita por vantagem no ambiente; nunca intenção.
Escopo: Tutor/IA. Prioridade: **P1**. Nota: diretriz de vocabulário que o Tutor do M6 herda.

**BIO-006 · Extinção catastrófica × ecológica** · **Momento: pré-M6 (validação/explicitação)**
Problema: risco de tratar toda extinção como falha de adaptação. `[Doc]`
Decisão: **Preservar** (já distinguido no sistema) e explicitar ao aluno que extinções em massa são amplamente aleatórias.
Comportamento: uma espécie bem adaptada pode ser extinta por evento catastrófico; o Tutor explica isso como acaso, não como fracasso.
Escopo: Simulação · Tutor. Prioridade: **P1**.

**ECO-001 · Teias alimentares e generalistas** · **Momento: pós-M6**
Problema: cadeia linear estrita empobrece a ecologia; espécies reais são generalistas. `[Doc]`
Decisão: **Modificar/Adicionar** — consumidores exploram mais de um nível/recurso; teias por progressão.
Comportamento: uma perturbação em um recurso propaga-se por múltiplos caminhos; nas eras avançadas a estrutura é teia, não linha.
Escopo: Simulação · Científico · Motor. Prioridade: **P1**.

**ECO-002 · Relações ecológicas além da predação** · **Momento: pós-M6**
Problema: só predação está modelada; faltam competição, mutualismo, parasitismo, herbivoria. `[Doc]`
Decisão: **Adicionar**. Comportamento: mudanças ambientais alteram essas relações e, por elas, a comunidade.
Escopo: Simulação · Motor. Prioridade: **P1**.

**ECO-003 · Decomposição e ciclo de nutrientes** · **Momento: pós-M6**
Problema: sem decompositores, o ciclo de nutrientes fica incompleto. `[Doc]` `[Compl]`
Decisão: **Adicionar**. Comportamento: matéria orgânica morta retorna nutrientes ao ambiente.
Escopo: Simulação · Motor. Prioridade: **P2**.

**ECO-004 · Capacidade de suporte em todos os níveis** · **Momento: preservar** — Escopo: Simulação. Prioridade: **P2** (validado). `[Doc]`

**ECO-005 · Destaque das oscilações predador-presa** · **Momento: pós-M6** — Escopo: Frontend · Tutor. Prioridade: **P2**. `[Doc]`

**GEO-001 · Ciclo do carbono internamente coerente** · **Momento: pós-M6**
Problema: o CO₂ não estabiliza em horizontes longos; risco de estabilização artificial ("gambiarra"). `[Doc]` `[Ctx]`
Decisão: **Modificar** — fechar o ciclo geológico do carbono de forma coerente, **sem** ensinar o detalhe.
Comportamento: o planeta permanece coerente por horizontes longos; o aluno vê no máximo uma versão simplificada.
Escopo: Motor · Científico. Prioridade: **P1**. Categoria **B**. (Corresponde à dívida de carbono já registrada; cercada pelo horizonte ~600 ticks até ser paga.)

**GEO-002 · Oxigênio e Grande Oxidação** · **Momento: pós-M6 (condicional ao escopo)**
Problema: o oxigênio atmosférico e a Grande Oxidação não são modelados. `[Doc]`
Decisão: **Adicionar** (condicional). Comportamento: se o jogo parte da Terra primitiva, a vida antecede o O₂; fotossíntese acumula O₂; a Grande Oxidação abre novas possibilidades ecológicas.
Escopo: Motor · Simulação. Prioridade: **P1 se começa na Terra primitiva; P3 se começa com vida estabelecida**.

**GEO-003 · Grande ciclo da água (participação da vida)** · **Momento: pós-M6**
Problema: o ciclo pode representar só o pequeno ciclo físico, sem transpiração. `[Doc]`
Decisão: **Adicionar/Modificar**. Comportamento: a presença de vida altera o ciclo da água.
Escopo: Simulação. Prioridade: **P2**.

**GEO-004 · Contexto do CO₂ antrópico** · **Momento: M6 (conteúdo do Tutor)**
Problema: o vulcanismo pode passar por maior fonte de CO₂ hoje. `[Doc]`
Decisão: **Modificar** (contextualização do Tutor). Comportamento: o Tutor esclarece que ações humanas superam o vulcanismo hoje.
Escopo: Tutor/IA. Prioridade: **P2**. (ponte para `ANT-001`)

**PED-001 · Progressão de complexidade** · **Momento: pós-M6** — Escopo: Instrumentação · Simulação. Prioridade: **P1**. `[Doc]`

**PED-002 · Aprendizagem por investigação** · **Momento: M6/pós-M6** — Escopo: Instrumentação · Tutor. Prioridade: **P2**. `[Doc]`

**PED-003 · Distinção adaptação × evolução × especiação** · **Momento: pré-M6** — **Modificar** enquadramento/linguagem. Escopo: Tutor · Instrumentação. Prioridade: **P0/P1**. `[Doc]`

**TUT-001 · Explicações causais ancoradas no estado observável** · **Momento: M6 (reforçar já no pré-M6)** — **Preservar/Reforçar**. Escopo: Tutor/IA. Prioridade: **P0**. `[Doc]` `[Ctx]`

**TUT-002 · Contraste entre espécies na extinção** · **Momento: M6 (depende de `BIO-003`)** — **Adicionar**. Escopo: Tutor/IA. Prioridade: **P1**. `[Doc]`

**TUT-003 · Exemplos concretos e reais** · **Momento: M6** — **Adicionar/Reforçar**. Escopo: Tutor/IA. Prioridade: **P1**. `[Doc]`

**TUT-004 · Adaptação ao nível cognitivo** · **Momento: M6** — **Adicionar**. Escopo: Tutor/IA. Prioridade: **P2**. `[Doc]`

**ANT-001 · Impactos antrópicos emergentes** · **Momento: pós-M6**
Problema: ausência do eixo prioritário do Especialista; risco de ser roteirizado em vez de emergente. `[Doc]`
Decisão: **Adicionar** — impactos humanos como **consequência** dos mecanismos ecológicos existentes.
Comportamento: desmatamento/fragmentação/poluição alteram relações ecológicas e propagam efeitos até os ciclos; nada é "hard-coded" isolado.
Escopo: Simulação · Motor · Instrumentação. Prioridade: **P1 (dependente de `ECO-001/002`)**.

## 9. Ordem de implementação

Ordenada por **dependência**, não pela ordem das perguntas. Insight central: a prioridade nº 1 do Especialista (impactos antrópicos) é **downstream** da lacuna que ele mesmo aponta (relações ecológicas) — logo as relações vêm primeiro. `[Inf]`

**Regra de fronteira com o M6:** uma mudança é **pré-M6** se, sem ela, o Tutor narraria algo **cientificamente errado** (não apenas "menos rico"). Ancestralidade errada é pré-M6; teias alimentares ausentes é pós-M6.

**Fase 0 — Correções conceituais [PRÉ-M6] — único pré-requisito do Tutor**
Objetivo: garantir que a ciência que o Tutor vai narrar esteja correta. Requisitos: `BIO-001` (ancestral comum), `BIO-005` (linguagem anti-teleológica), `BIO-006` (explicitar extinção catastrófica), `PED-003` (adaptação × evolução), e a **causa** da especiação exposta no evento (parte de `BIO-002`). Decisão a formalizar junto: `BIO-003` (comunidade+espécies — escopo do que o Tutor assume). Dependências: nenhuma. Conclusão: o modelo de especiação registra ancestral comum + duas linhagens com causa; nenhuma linguagem teleológica; a decisão de coortes está registrada.

**Fase M6 — Tutor (LLM+RAG)**
O marco do Tutor, sobre um modelo com ancestralidade correta e escopo de espécies decidido. Incorpora `TUT-001/002/003/004`, `GEO-004`, `PED-002`.

**Fase 1 — Relações ecológicas (a fundação) [PÓS-M6]**
Requisitos: `ECO-001`, `ECO-002`, `ECO-003`, `ECO-005`. Conclusão: uma perturbação ambiental propaga-se por múltiplas relações (teia).

**Fase 2 — Espécies e especiação completas [PÓS-M6]**
Requisitos: `BIO-002` (mecânica gradual), `BIO-003` (implementação da camada), `BIO-004`. Dependências: Fase 0 e o modelo de comunidade.

**Fase 3 — Coerência dos ciclos planetários [PÓS-M6]**
Requisitos: `GEO-001` (paga a dívida de carbono), `GEO-003`, `GEO-002` (se aplicável).

**Fase 4 — Impactos antrópicos [PÓS-M6]**
Requisitos: `ANT-001`. Dependências: Fase 1 (há relações para impactar).

## 10. Fora do escopo

- **Ensinar ao aluno** o detalhe do intemperismo/carbonatos/sedimentação e escalas de milhões de anos (modelar internamente — `GEO-001` — mas não apresentar). `[Doc]`
- **Árvores filogenéticas completas** com todas as gerações (usar filogenia simplificada). `[Doc]`
- **Muitas espécies simultâneas** e excesso de indicadores na tela. `[Doc]`
- **Aula sobre múltiplos mecanismos de especiação** (convergência/anagênese/cladogênese) como conteúdo formal — no máximo menção conceitual pelo Tutor; a mecânica modela divergência causada. `[Inf]`
- **Tornar o termostato de carbono uma mecânica visível.** `[Doc]`
- **Oxigênio/Grande Oxidação** se o jogo começar com um planeta já habitado (**Adiar**). `[Doc]`
- Qualquer indicador/tela/número que **não** melhore a compreensão causal. `[Doc]`

## 11. Riscos de representação científica

- **Teleologia da evolução** — aluno pensa que espécies evoluem "para" algo; erro conceitual central perpetuado. Solução: `BIO-005` + `PED-003`.
- **Indivíduo × população** — crer que o indivíduo evolui. Solução: enquadrar evolução como fenômeno populacional (Fase 0).
- **Adaptação × especiação** — reduzir evolução a adaptação. Solução: `PED-003`.
- **Ancestralidade incorreta ("A→B")** — solução: `BIO-001`. **Risco pré-M6:** se não corrigido, o Tutor ensina ancestralidade errada com autoridade.
- **Extinção só como falha** — mass extinction é aleatória. Solução: `BIO-006`.
- **Relações ecológicas lineares** — ecologia empobrecida/irreal. Solução: `ECO-001/002`.
- **Ciclos biogeoquímicos artificialmente estabilizados** — "gambiarra" que fere a coerência. Solução: `GEO-001`.
- **Hipóteses como fatos** — origem da vida / Grande Oxidação / Gaia como certezas. Solução: enquadrar como reconstrução/sequência-modelo. `[Inf]`

## 12. Riscos pedagógicos

- **Excesso de espécies/indicadores simultâneos** → poucas espécies, poucos indicadores. `[Doc]`
- **Sobrecarga cognitiva** → progressão por eras (`PED-001`).
- **Explicações abstratas** → exemplos concretos (`TUT-003`).
- **Excesso de respostas prontas do Tutor** → investigação (`PED-002`).
- **Confusão correlação × causalidade** → o Tutor explica sempre por causa observável (`TUT-001`).
- **Reduzir evolução a adaptação** → `PED-003`.

## 13. Critérios de validação

Critérios de aceitação de alto nível (para virar testes depois):

- **Científico:** o sistema nunca representa evolução como transformação intencional do indivíduo; a ancestralidade aparece como ancestral comum; uma espécie bem adaptada pode ser extinta por evento catastrófico.
- **Pedagógico:** o aluno consegue identificar uma relação causal entre mudança ambiental e alteração populacional; e distinguir adaptação de especiação.
- **Simulação:** uma alteração ambiental produz efeitos **propagados pelas relações ecológicas** (teia), não por uma cadeia linear única.
- **Ciclos:** o planeta permanece cientificamente coerente em horizonte longo sem estabilização artificial visível.
- **Tutor:** explica eventos usando causas observáveis no estado da simulação e, quando há espécies, contrasta por que uma sobreviveu e outra não.

## 14. Decisões arquiteturais que precisam ser preservadas

Confirmadas pela validação e que **não** devem ser desfeitas: `[Doc]` valida, `[Ctx]` identifica no projeto.

- **Evolução emergente sem aptidão global** — o Especialista confirma que sobrevivência por condições locais representa bem a seleção natural (Q4/Q5). Preservar.
- **Extinção catastrófica independente de aptidão** — validada (Q8). Preservar.
- **Capacidade de suporte em todos os níveis tróficos** — validada e ampliada (Q11). Preservar.
- **Tutor ancorado no estado observável da simulação** (causas verificáveis) — coerente com "explicações causais". Preservar.
- **Coerência interna acima de complexidade visível** — princípio "não ensinar ≠ não modelar" (carbono). Preservar como diretriz geral.
- **Acoplamentos com defasagem de um tick** — aceitáveis (Q16). Preservar.
- **Comunidade/população como mecanismo evolutivo**, com espécies como camada por cima — não substituir o mecanismo pela representação de espécies.

## 15. Resumo executivo

A validação confirma que o núcleo científico do ECOSFERA está **correto** (evolução não-teleológica, aptidão contextual, pirâmide de energia, capacidade de suporte, sumidouro biótico, extinção catastrófica) — e esses pontos devem ser **preservados**. O valor das mudanças concentra-se em três frentes: **(1)** corrigir conceitos baratos e de alto impacto — ancestralidade por ancestral comum e especiação gradual e causada; **(2)** preencher a maior lacuna científica — **relações ecológicas** (teias, competição, mutualismo, decomposição), pré-requisito de tudo o mais; **(3)** representar a vida como transformadora do planeta — **impactos antrópicos** (prioridade do Especialista) e, conforme o escopo, a **Grande Oxidação**. A representação da vida resolve-se por **comunidade + espécies** (não uma escolha). Duas divergências são **complementares, não contraditórias**: o carbono deve ser **modelado sem ser ensinado**; a sequência do oxigênio (vida antes do O₂) é **consistente** entre as duas vozes. Quanto ao sequenciamento com o M6: apenas a **Fase 0 (correções conceituais)** é pré-requisito do Tutor — sem ela, o Tutor narraria ciência errada; todo o restante do plano é melhoria da ciência narrada e vem depois do M6. O princípio transversal é **não adicionar complexidade sem ganho causal**.
