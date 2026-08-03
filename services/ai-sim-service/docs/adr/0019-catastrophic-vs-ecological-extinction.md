# ADR 0019 — Extinção catastrófica × ecológica, e a aptidão CONTEXTUAL

## Status
Aceito. Fecha o M4 junto com o **ADR 0018**. Aplica as validações da especialista
em Biologia (Tássia): **Q5** (vocabulário), **Q8** (taxonomia de extinção) e
**Q11** (capacidade em todos os níveis tróficos). Referências: ADR-ARCH-0001,
ADR-ARCH-0002, ADR 0016, Dossiê v3 §10.5, Elton (1927), Verhulst (1838).

## Contexto

A concepção equivocada que a plataforma existe para desfazer é *"quem se extingue
era inferior"*. Até o M3, TODA extinção do simulador tinha causa ecológica — não
tolerou o calor, não achou recurso, foi predado. Cada peça estava correta, e o
conjunto **ensinava a concepção errada**: se toda morte é explicada por um traço,
morrer vira prova de inferioridade.

## Decisão

### 1. Duas famílias de causa, e elas não se misturam

| Família | `cause_code` | Natureza |
| --- | --- | --- |
| ECOLÓGICA | `THERMAL_INTOLERANCE`, `RESOURCE_SCARCITY`, `PREDATION_PRESSURE` | gradual, mediada por adaptação |
| CATASTRÓFICA | `CATASTROPHIC_EVENT` | abrupta, **independente de aptidão** |

Colapsá-las numa só faria o Tutor narrar toda extinção como falha de adaptação.

### 2. A mortalidade catastrófica NÃO olha para o genoma

A fração removida não passa por `local_suitability`, não é atenuada por adaptação
e não poupa quem está no próprio ótimo. Uma comunidade exemplarmente adaptada —
no ótimo térmico, tolerância larga, metabolismo barato, recurso de sobra, sem
predador — pode ser eliminada por um meteoro.

Isso é afirmado quantitativamente, e não só por presença de um código novo:
`test_catastrophic_extinction_is_fitness_independent` exige que a **fração
removida seja idêntica** para uma coorte bem adaptada e uma mal adaptada no mesmo
mundo, e varre o genoma traço a traço confirmando que nenhum deles compra
proteção. Se a catástrofe poupasse os aptos, seria seleção com outro nome.

### 3. A catástrofe é aplicada pela EVOLUTION, dona do total

**Desvio consciente do desenho inicial, confirmado pelo arquiteto.** A intenção
era aplicá-la na Ecology, junto da dinâmica trófica. Foi tentado e medido: a soma
dos níveis descolou de `biota.biomass` (13,57 contra 14,09), e a Ecology virou um
segundo **sumidouro** de biomassa — o espelho da "segunda fonte" que a mesma
invariante do M3 proíbe.

A Evolution é dona do total, então é ela que aplica a catástrofe; a renormalização
da Ecology propaga o efeito aos três níveis sozinha. Comportamento idêntico,
invariante de conservação preservada.

### 4. A cadeia causal aponta para o EVENTO, não para o clima

Uma extinção catastrófica encadeia por `causation_id` ao evento gatilho
(`MeteorImpact`), não ao `TemperatureShift` que por acaso ocorreu no mesmo tick.

**Isto foi um defeito real, encontrado pelo teste de cadeia e corrigido.** A
condicional existia mas fora aplicada ao bloco errado: `SpeciesExtinct` chegou a
emitir `cause_code=CATASTROPHIC_EVENT` com `causation_id` apontando para o clima.
O código de causa dizia "catástrofe" e a trilha dizia "não tolerou a
temperatura" — a trilha reintroduzia pela porta dos fundos exatamente o que o
código de causa fora criado para excluir. Um Tutor percorrendo aquela cadeia
diria ao aluno que a espécie morreu de calor.

### 5. Q5 — a aptidão é CONTEXTUAL, não inexistente

Dizer "não há aptidão neste modelo" troca uma imprecisão por outra. A aptidão
EXISTE; o que não existe é aptidão **ABSOLUTA** — o número único que ordenaria as
espécies fora de qualquer contexto.

A mesma coorte é apta a um ambiente e inapta a outro **sem ter mudado em nada**:
o genoma que prospera a 20 °C perece a 60 °C. A aptidão é propriedade da RELAÇÃO
entre organismo e ambiente, não um atributo que o organismo carrega.

É essa formulação que torna inteligível a extinção catastrófica: uma espécie de
aptidão contextual ALTA pode morrer. `test_contextual_fitness_wording` guarda a
formulação no domínio, nos `cause_code` e nestes ADRs — e distingue o USO da
MENÇÃO, porque citar a formulação errada para rejeitá-la é o oposto do defeito.

### 6. Q11 — capacidade de suporte em TODOS os níveis tróficos

**Princípio validado pela Tássia; FORMA decidida na engenharia.**

O princípio: o teto ambiental vale para consumidores, não só para produtores.
Antes, herbívoro e predador cresciam apenas pelo que conseguiam converter, sem
limite algum — um ambiente pobre sustentava uma pirâmide inteira desde que a
predação corresse bem.

A forma: a primeira leitura — fração fixa da capacidade ambiental para cada
consumidor — foi implementada e MEDIDA: travou os herbívoros em um terço da
população e levou os **predadores à extinção por fome**, achatando a cadeia em
dois níveis. Passava em toda asserção de unidade e só aparecia numa corrida
longa.

A forma adotada ancora o teto de cada nível no nível **ABAIXO** dele — a forma
eltoniana do mesmo limite. Preserva os três níveis e produz uma pirâmide melhor
formada que a do M3, onde produtores e herbívoros empatavam (56 × 56), base quase
plana que Elton (1927) não admite. Hoje: 125 ▸ 32 ▸ 8,4.

O Resource continua dono da `carrying_capacity` ambiental; a Ecology apenas a LÊ
por mais níveis. Não há segunda capacidade nem dupla contagem.

**Rastreabilidade:** princípio *validado*; forma eltoniana *a confirmar com a
especialista quando ambientada* (`docs/decisions/tassia-validation.md`).

### 7. O pino de CO₂ NÃO foi re-fixado — e a razão importa

Autorizou-se re-fixar `test_baseline_planet_is_quasi_stationary` no novo
equilíbrio (~264 ppm) **desde que confirmado estável**. O procedimento foi
executado e **reprovou**:

| | bio em t=2999 | ticks sem vida (t>1000) | deriva do CO₂ na cauda |
| --- | --- | --- | --- |
| M3 (sem teto) semente 2027 | 0,00 | 875 | +41,8 |
| M3 semente 99 | 0,00 | 1770 | +22,8 |
| M4 Q11 semente 2027 | 0,00 | 1536 | +53,7 |
| M4 Q11 semente 99 | **21,84** | **0** | +16,4 |

O CO₂ **não converge**: passa de 870 ppm e continua subindo em t=3000. O valor de
264 ppm era um TRANSIENTE, medido em t=600 no fundo de uma excursão grande.

E a causa **não é a Q11**: o M3 é igualmente instável, em duas sementes de duas,
e pior — a Q11 melhora estritamente a semente 99, onde a vida sobrevive em vez de
morrer. O colapso de longo prazo **precede o M4** e nunca fora observado porque
nenhum teste passava de ~600 ticks.

Re-fixar o pino no transiente registraria como "equilíbrio" um ponto de passagem.
O teste afirma DUAS coisas — que existe equilíbrio e onde ele está —, e a primeira
deixou de ser verdadeira. Fica em aberto, para o arquiteto, e é dívida
**anterior** ao M4.

## Consequências

**Ganhamos.** O aluno pode perder uma espécie bem adaptada para um meteoro e ouvir
do Tutor que foi um evento extremo — não uma falha dela. É a lição central do
marco.

**Perdemos.** A taxonomia depende de a `EventSlice` estar correta no tick da
morte: se a catástrofe fosse zerada cedo demais, uma morte catastrófica viraria
ecológica em silêncio. A precedência (catástrofe primeiro) e o teste de
contraprova cobrem isso.

**Aberto.** A instabilidade de longo prazo da linha de base, herdada do M3.
