# ADR 0028 — Integração do LLM com ancoragem: o modelo reescreve, não decide

**Status:** aceito
**Marco:** M6.3
**Relacionados:** ADR-ARCH-0002 (três audiências = três projeções) · ADR 0025 (M6.0,
fundação factual) · ADR 0026 (M6.1, piso de qualidade) · ADR 0027 (M6.2, RAG
pedagógico, e o adendo do portão do embedder) · ADR 0019 (catastrófica ×
ecológica) · ADR 0023 (ancestral comum, BIO-005) · ADR 0024 (coortes)

## Contexto

Este é o marco que introduz o primeiro componente genuinamente não-determinístico
do serviço. Tudo o que o M6.0, o M6.1 e o M6.2 construíram existe para que o
trabalho dele seja estreito: **o LLM reescreve o piso do M6.1 no registro que o
M6.2 recupera.** Ele não decide o que aconteceu, não acrescenta fato e não
sobrepõe o Event Store.

O princípio que governa o M6 inteiro não muda aqui, e é o que define correção:

> A verdade sobre o planeta do aluno é o **Event Store**. Um consumidor está
> correto quando o que afirma é derivável do event log, e alucinando quando não
> está — por mais cientificamente verdadeira que a afirmação seja em geral.

## Decisão

### 1. A hierarquia de ancoragem, escrita no tipo e no prompt

```
Event Store → FactualContext (M6.0) → Explanation (M6.1) ─┐
                                      ^ o QUE aconteceu   ├→ prompt → LLM → verificação → aluno
corpus      → RetrievedPassage (M6.2) ────────────────────┘
              ^ COMO se diz
```

O prompt entrega as duas metades ROTULADAS (`<fatos>` e `<registro>`) e declara,
em texto, qual delas é verdade. Um modelo que receba dois blocos sem hierarquia
declarada trata os dois como igualmente autoritativos — e a passagem que diz
"extinções catastróficas são independentes de aptidão" vira "houve uma extinção
catastrófica neste planeta".

### 2. A verificação fica ENTRE a geração e o aluno

Não há caminho em que texto não verificado chegue ao aluno. O caso de uso só
devolve prosa do modelo se o veredito passou; em todos os outros casos devolve o
piso do M6.1 — íntegro, e não uma versão degradada dele.

O que se confere, e por quê:

* **Números.** Todo numeral da saída tem de aparecer no piso. Forte e sem falso
  positivo: uma reescrita fiel pode OMITIR um número, nunca acrescentar um. É o
  herdeiro direto da regra 3 do `test_every_claim_is_grounded_in_context`, e pega
  a alucinação mais comum de um modelo pequeno — a quantidade plausível.
* **Formulação proibida.** As listas canônicas do BIO-005 e da aptidão absoluta
  (Q5), as mesmas que guardam templates e código desde a Fase 0.
* **Acontecimento inventado.** Se a prosa fala de um meteoro e o dossiê daquele
  planeta não tem `MeteorImpact`, o modelo acrescentou um fato.

**O que NÃO se confere, dito em voz alta.** A cobertura de acontecimento
inventado é PARCIAL — só os tipos com termo concreto próprio. Não há análise
sintática, não há verificação de que a relação causal foi preservada, e não há
robustez adversarial. Isso é M6.4, e prometê-lo aqui daria falsa segurança.

### 3. Toda falha vira o piso, e nenhuma exceção sobe

A porta devolve `str | None`. Rede caída, tempo esgotado, HTTP não-2xx, JSON
malformado, corpo vazio: tudo vira `None` com o motivo registrado. O caso de uso
ainda captura exceção por cima disso — a promessa é do adaptador, e o M6.4 vai
injetar ali um harness que ninguém escreveu ainda.

O comportamento correto quando o modelo falha não é estourar: é entregar o piso,
que já é explicação correta. Uma exceção escapando transformaria indisponibilidade
de infraestrutura em erro para o aluno, existindo resposta boa o tempo todo.

`GroundingVerdict` tem **três** estados, e não dois: passou, reprovado, e **não
avaliado**. A distinção veio do roteiro de fumaça, que mostrava
`veredito: reprovado` com o modelo desligado — e não houve reprovação alguma, não
houve texto para verificar. Somar queda de rede à taxa de alucinação faria o M6.4
medir a infraestrutura achando que mede o modelo.

### 4. O modelo escolhido: `llama3.1:8b` em produção, `llama3.2:1b` no CI

**Produção — `llama3.1:8b`.** Multilíngue com português competente, roda em
hardware modesto (~5 GB quantizado) e é o que o `docker-compose` do projeto já
previa no perfil `ai`. A tarefa aqui é reescrever um texto dado, não raciocinar
sobre ciência: o piso já traz o conteúdo correto, e o que se pede é registro. Um
modelo maior custaria infraestrutura para melhorar uma tarefa que não é o gargalo.

**CI — `llama3.2:1b`.** ~1,3 GB, baixa em segundos. O que o job verifica é que a
ancoragem funciona ponta a ponta com um LLM de verdade, e isso não melhora com um
modelo que leve dez minutos para baixar em todo run.

A temperatura é **0,2**: a tarefa é reescrever, e criatividade nesta posição é
literalmente o modo de falha.

### 5. Arbitragem por categoria — fechando o achado do ADR 0027

O adendo do ADR 0027 mediu que a similaridade **não** distingue uma regra de
vocabulário da correção validada que diz o mesmo: as duas voltam para a mesma
consulta, e qual vem primeiro depende do embedder (o léxico preferiu VAL-Q8, o
semântico preferiu VOC-006). Aquele ADR recomendou resolver por filtro de
categoria; é o que este marco faz.

Entre irmãs, a **regra de vocabulário entra primeiro** — é a formulação curta e
citável, escrita para ser seguida; a correção validada é o registro de por que a
regra existe. Dentro da mesma categoria a similaridade continua mandando, e
`entry_id` fecha o desempate para que a ordem seja TOTAL.

O ganho não é qualidade de recuperação, é **reprodutibilidade**: sem isso, trocar
de embedder mudaria o prompt sem que nada de factual tivesse mudado — num marco
em que se está tentando medir um componente não-determinístico.

E a ambiguidade **não** é tratada como falha de fundamentação. A regra é mais
simples e mais forte que arbitrar: *a prosa é conferida contra o PISO e o DOSSIÊ,
nunca contra o corpus.* Um contrato de import impede que isso volte a ser
disciplina.

### 6. O vocabulário anti-teleológico foi CONSOLIDADO, não copiado

Pergunta do pre-flight: a lista era cópia da Fase 0 ou a fonte canônica?

**Era a fonte canônica.** A Fase 0 apontava para ela: o teste de contrato já a
importava do teste unitário e afirmava identidade de objeto e tamanho mínimo,
justamente para impedir que alguém a substituísse por outra. O ADR 0023 e o
`causal_rules.yaml` enunciam a diretriz em prosa; a enumeração verificável nasceu
no teste.

O que mudou no M6.3 é quem precisa dela. Até aqui só testes liam a lista, porque
só havia prosa determinística para conferir; agora existe um verificador em tempo
de execução, e código de produção não importa de `tests/`. A lista **migrou** para
`domain/consumers/wording.py`, e o teste passou a importá-la de lá.

**A consolidação encontrou uma divergência real.** A VOC-001 do corpus ensina ao
Tutor que "a espécie desenvolveu" é proibida, e a lista de imposição não a
alcançava — só completações mais específicas. Uma frase como *"a espécie
desenvolveu uma casca mais grossa"* passaria pelo verificador depois de o próprio
corpus tê-la declarado errada. O radical entrou na lista, conferido contra o
repositório para não gerar falso positivo, e um teste novo mantém as duas
alinhadas: tudo o que a VOC-001 lista como proibido tem de ser pego pelo guarda.

Aptidão absoluta ficou em lista **separada**: "era inferior" não atribui intenção
a ninguém — afirma uma ordenação que não existe. Fundi-las faria a mensagem de
erro citar a regra errada.

### 7. A porta do LLM substituiu a do MVP, em vez de conviver com ela

O MVP deixou `LLMClient` e `NullLLM` com **zero pontos de uso**. Mantê-los
deixaria duas abstrações de LLM no serviço ao mesmo tempo, e a antiga trazia a
superfície de string crua com `max_tokens` — o "peça qualquer coisa" que o
contrato de ancoragem existe para não ter.

Uma porta declarada que ninguém exercita é a família de defeito que este serviço
já pagou duas vezes (`atmosphere.oxygen` sem escritor, o filtro fantasma de
`planet_id`). Foi substituída: `NullLanguageModel` satisfaz a porta nova e devolve
`None`, o que faz "LLM desligado" percorrer exatamente o mesmo caminho que "LLM
caiu".

### 8. A mudança de método: de igualdade exata para invariante

**Esta é a mudança metodológica do marco, e ela vale para o M6.4 em diante.**

Todo marco anterior testou por igualdade: mesma entrada, mesma saída, byte a byte.
Era possível porque tudo era determinístico, e era a forma mais forte de afirmação
disponível — o M5 chega a comparar exports por hash.

Com um modelo generativo no caminho essa forma deixa de existir. Duas execuções
com a mesma entrada produzem textos diferentes, e **nenhum dos dois é o certo**.
O que resta é afirmar PROPRIEDADES que valem para toda saída:

* nenhuma afirmação sem origem no piso;
* nenhuma formulação teleológica, nenhuma aptidão absoluta;
* o que o piso chama de catastrófico não vira falha de adaptação;
* nenhum acontecimento fora do dossiê.

As N gerações dos testes unitários são **roteirizadas**, e isso é deliberado: um
modelo real produziria as violações raramente e de modo imprevisível, e um teste
que dependesse de ele errar seria intermitente. Roteirizar torna a afirmação
exaustiva em vez de sortuda.

## O que está VERIFICADO, e o que não está

**Verificado localmente:** o contrato de falha modo a modo; a verificação de
fundamentação nas duas direções (reprova invenção, aceita reescrita fiel); a
separação de tipos entre geração e fato, com o `mypy` EXECUTADO sobre a atribuição
proibida; a arbitragem por categoria, inclusive no caso em que a similaridade diz
o contrário; a consolidação do vocabulário, por identidade de objeto; e que
passagem enganosa não muda o que a saída afirma.

**Verificado no CI:** a geração contra um Ollama de verdade
(`test_generation_over_ollama.py`), com `ECOSFERA_REQUIRE_OLLAMA=1` transformando
ausência de daemon em FALHA, e não em pulo.

Esse job existe por causa da segunda lição do adendo do ADR 0027: **um falso pode
concordar com o adaptador enquanto a biblioteca real diverge.** Aqui o risco é
maior. Se o prompt for ambíguo, se o modelo ignorar a instrução ou se o
verificador for estrito demais, o sintoma é recuo em 100% das gerações — o aluno
lê o piso, nada quebra, e a camada inteira vira custo puro **indistinguível de
sucesso** em toda suíte roteirizada.
`test_at_least_one_real_generation_survives_the_gate` é o que impede isso.

**NÃO verificado:** taxa de aprovação com modelo real, qualidade pedagógica
comparada ao piso, e robustez a entrada adversarial. As três são M6.4, com
conjunto de avaliação de verdade. Este marco afirma que o caminho está de pé, não
que ele é bom.

## O que este marco NÃO faz

* **Nenhuma avaliação adversarial.** M6.4.
* **Nenhuma defesa contra injeção de prompt** além do próprio contrato de
  ancoragem. M6.4.
* **Nenhum ajuste fino de modelo**, nenhuma rota HTTP para o aluno, nenhuma camada
  de espécies com identidade.
* **Nada alterado** em `FactualContext`, nos templates do M6.1, no contrato do
  corpus do M6.2, no world-state ou nos Engines.

## Alternativas consideradas

* **Deixar o LLM ler o dossiê direto, sem o piso do M6.1.** Rejeitada: seria pedir
  ao modelo que decidisse o que é digno de nota e como encadear causas — as duas
  decisões que o M6.1 já toma de forma auditável. E apagaria o "antes" contra o
  qual se compara o que o modelo produz.
* **Verificar a fundamentação com um segundo LLM.** Rejeitada neste marco: trocaria
  um componente não-determinístico não verificado por dois, e o verificador
  passaria a ter os mesmos modos de falha do gerador. Uma heurística mecânica que
  se sabe parcial é mais honesta que uma verificação que parece completa.
* **Deixar a exceção do modelo subir.** Rejeitada: ver a decisão 3.
* **Arbitrar as irmãs por nota, escolhendo a de maior similaridade.** Rejeitada: é
  exatamente o que o ADR 0027 mediu que varia entre embedders.

## Consequências

O aluno passa a poder ler prosa escrita por um modelo — e só quando ela sobrevive
a uma conferência mecânica contra o event log dele. Quando não sobrevive, lê o
piso do M6.1, e a diferença fica registrada no objeto de saída em vez de sumir.

O M6.4 herda: a porta para injetar um harness adversarial sem tocar na ancoragem,
os motivos de reprovação em forma utilizável para montar conjunto de avaliação, a
distinção entre reprovação e indisponibilidade, e a lista de tipos de evento cuja
invenção esta rodada **não** detecta.
