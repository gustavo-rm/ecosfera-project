# ADR 0012 — Ciclos fechados: as fronteiras do carbono e da água

## Status
Aceito. Abre o M2. Estende o **ADR 0010** (fronteira do carbono no M1) e
implementa **ADR-ARCH-0001**/**ADR-ARCH-0002**. Complementado pelo **ADR 0013**
(`physics` → Astronomy, Biota provisório) e pelo **ADR 0014** (aposentadoria do
legado). Referências: Dossiê v3 §10.4/§10.5, Spec §3/§5.1, RF-014, RF-016.

## Contexto

O M1 deu dono ao carbono ATMOSFÉRICO e à temperatura, mas deixou dois ciclos
pela metade. O carbono tinha fonte (desgaseificação) e sumidouros
(intemperismo, absorção biótica) e **nenhum reservatório oceânico** — o maior
tampão de carbono de um planeta simplesmente não existia no modelo. A água
morava em duas variáveis desconexas (`water` e `ice_cover`), governadas por
subsistemas diferentes, sem nada que dissesse que a soma das duas era uma
grandeza física.

Enquanto isso a `LegacySlice` continuava sendo o depósito do que não tinha dono,
o que impedia a aposentadoria do adaptador.

## Decisão

### 1. O carbono ganha o reservatório oceânico — e uma convenção de sinal

O **Chemistry Engine** passa a deter o carbono dissolvido (`ocean_carbon`), o
soterrado (`soil_carbon`) e, sobretudo, o fluxo de troca `air_sea_flux`. A
Atmosphere continua dona do estoque atmosférico (ADR 0010).

A troca segue a **lei de Henry**, linearizada em torno da referência
pré-industrial:

```
F = solubilidade · (pCO₂_ar − pCO₂_oceano) · (1 − saturação)
```

> Sabine, C. L. et al. (2004). *The oceanic sink for anthropogenic CO₂.*
> Science 305(5682), 367–371.

**A convenção de sinal é a decisão, não a fórmula.** `F > 0` significa que o
oceano absorve. A química SOMA esse número ao próprio reservatório; a atmosfera
SUBTRAI exatamente o mesmo número do dela. Um fluxo, dois livros, sinais opostos.

A alternativa — cada Engine calcular a própria troca — parece simétrica e é
errada: os dois calculariam a partir de estados ligeiramente diferentes (a
composição é sequencial), e a diferença viraria carbono criado ou destruído a
cada tick, sem que nenhum dos dois Engines estivesse individualmente incorreto.

O termo de **saturação** existe para que um oceano cheio pare de absorver. Sem
ele o reservatório oceânico seria um sumidouro infinito e o carbono atmosférico
desapareceria — o oposto do que a física do sumidouro descreve.

### 2. A água vira quatro reservatórios com uma soma conservada

O **Hydrology Engine** substitui o subsystem `ocean` e absorve o ciclo
gelo↔água que estava embutido no `chemistry` legado. Quatro reservatórios
(`ocean`, `ice`, `vapour`, `freshwater`) e cinco fluxos entre eles.

Nenhum fluxo cria ou destrói água: cada um **move massa**. É isso que torna a
conservação uma invariante verificável, e não um comentário. Cada fluxo é
limitado pelo reservatório de ORIGEM, de modo que a não-negatividade vale antes
da invariante — a invariante fica sendo rede de segurança, não mecanismo.

**`ice_cover` sai da `ClimateSlice`.** A criosfera é um reservatório de água, e
tratá-la como variável climática era o que obrigava dois subsistemas a
escreverem a mesma grandeza. O Climate passa a LER a fração de gelo, que a
hidrologia publica.

### 3. A fração de gelo é publicada, não recalculada

O Climate precisa da fração de gelo para o albedo. Recalculá-la a partir dos
reservatórios exigiria importar o domínio da hidrologia — o que o contrato de
import-linter proíbe — ou reimplementar a mesma divisão, que é a definição de
ciência duplicada.

Ela entra na `HydrologySlice` como campo publicado. Canal A, um escritor, um
leitor.

### 4. Conservação da água é invariante de runtime; a do carbono, não

`ConservedTotal` verifica, a cada delta, que a soma dos quatro reservatórios não
se moveu além da tolerância declarada em `hydrology/params.yaml`.

**Ela não repara.** As demais invariantes recortam o valor e seguem, porque o
recorte é regra determinística conhecida. Aqui não existe reparo correto: saber
que a soma se moveu não diz de qual reservatório tirar a diferença, e escolher um
esconderia o defeito exatamente onde ele precisa ser visto. A violação vira
`DiagnosticEvent` e o número errado fica à vista.

O carbono **não** ganhou invariante equivalente, e isso é deliberado. Ele não é
uma soma constante: tem fonte (vulcanismo) e sumidouro (absorção biótica), ambos
legítimos. O que precisa valer é a identidade contábil da troca ar↔oceano, que
atravessa DUAS fatias com donos diferentes. Uma invariante que roda por delta,
sobre uma fatia, não a enxerga; e ensinar o Planet Engine a distinguir "fonte" de
"troca" seria colocar ciência nele, o que o ADR-ARCH-0001 proíbe.

A identidade é verificada em teste de integração (`test_carbon_is_not_double_counted`),
que é onde uma afirmação sobre a contabilidade ENTRE Engines pertence.

### 5. As defasagens declaradas que quebram os ciclos

Quatro acoplamentos são bidirecionais e seriam ciclos no grafo. Todos se
resolvem com defasagem de um tick, **declarada** em `lagged_reads` — não
declarar é erro de boot, via `validate_graph`:

| Ciclo | Lê no mesmo tick | Lê defasado |
| --- | --- | --- |
| química ⇄ atmosfera | Chemistry lê Geology | Chemistry lê `atmosphere.co2` |
| clima ⇄ água | Hydrology lê `climate.temperature` | Climate lê `hydrology.ice_fraction` |
| geologia ⇄ água | — | Geology lê a água para a erosão |
| recurso ⇄ biota | Biota lê `resource.carrying_capacity` | Resource lê `biota.biomass` |

### 6. O `PlanetState` cresceu para não comer a ciência nova

`FrameworkTickOrchestrator.tick()` faz o ciclo `snapshot → Engines → PlanetState`
a CADA tick, porque é o `PlanetState` que a borda HTTP e a persistência guardam.
Um estoque sem lugar nele voltaria a zero uma vez por tick — e a hidrologia, a
química, o recurso e a biota nunca realimentariam coisa alguma.

O `PlanetState` ganhou os ESTOQUES das fatias novas. É a evolução que a
persistência já previa: o estado é gravado como JSONB justamente para que ganhar
campos não exija migration, e a leitura tolera chaves desconhecidas e preenche
ausentes com o default da dataclass. Checkpoints anteriores ao M2 continuam
legíveis.

`water` e `ice_cover` seguem publicados como AGREGADOS derivados — o contrato
HTTP não mudou. Quem ganhou detalhe foi o modelo, não a interface.

Substituir o `PlanetState` inteiro pelo `WorldStateSnapshot` continua sendo
trabalho do **M5**. O que o M2 fez foi impedir que a truncagem comesse a ciência
nova enquanto isso não acontece.

### 7. Condições iniciais são física, não campos em branco

`ocean_carbon` parte de 300 (equilíbrio com a atmosfera de referência) e os
estoques de N/P/S partem dos valores em que o elemento é exatamente
não-limitante.

Isso foi medido, não estimado. Com o oceano em zero, o gradiente inicial era de
280 ppm inteiros e o planeta gastava a primeira era transferindo carbono do ar
para a água: o CO₂ atmosférico CAÍA de 280 para 234 em 60 ticks, e a leitura
pedagógica virava "o oceano resfria o planeta" — um artefato de condição inicial
apresentado como resultado. Com os nutrientes em zero, a capacidade de suporte
nascia em ~0 e a abiogênese atrasava ~50 ticks pelo mesmo motivo.

Com os valores de referência, a capacidade inicial reproduz a do subsistema
`life`, e os fatores novos (nutriente, energia) só passam a morder quando o
planeta de fato fica limitado por eles — que é para isso que existem.

## Consequências

+ Os dois ciclos físicos fecham: a água conserva dentro da tolerância declarada
  e o carbono tem contabilidade auditável entre ar, oceano e sedimento.
+ O oceano AMORTECE o carbono, que é o comportamento real do sistema: o
  aquecimento é mais lento do que a emissão bruta faria supor, e o aluno tem um
  fenômeno novo para explicar.
+ Toda fatia passa a ter dono — o pré-requisito para o ADR 0014.
+ `ConservedTotal` é reutilizável para qualquer grandeza conservada futura.
− A trajetória do M1 mudou. A cadeia erupção→forçamento→clima leva mais ticks
  para se fechar, e o teste que a verifica passou a declarar um cenário
  vulcânico em vez de esperar que uma trajetória aleatória a produzisse. Isso é
  correção de método: o que se verifica é o encadeamento por `causation_id`, e
  fazê-lo depender de sorteio já era frágil no M1.
− O `PlanetState` ficou grande e duplica o esquema do world-state. É dívida
  consciente, e o M5 a paga ao persistir o snapshot inteiro.
− `WORLD_STATE_VERSION` sobe para 2: checkpoints da versão 1 não são legíveis.
