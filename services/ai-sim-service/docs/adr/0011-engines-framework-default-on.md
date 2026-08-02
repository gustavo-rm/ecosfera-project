# ADR 0011 — A moldura de Engines vira o caminho principal

## Status
Aceito. Fecha o M1. Complementa o **ADR 0010** (fronteira do carbono) e
implementa **ADR-ARCH-0001**/**ADR-ARCH-0002**. Referências: Dossiê v3
§10.4/§10.5, RF-013/014, RF-023, RF-033.

## Contexto

O M0 entregou a moldura atrás de `ECOSFERA_ENGINES_FRAMEWORK`, desligada por
padrão, com o núcleo determinístico inteiro atravessando-a por um adaptador. O M1
entregou os três primeiros Engines científicos de verdade e o feedback físico
completo. A flag deixou de proteger algo em construção e passou a esconder o
caminho bom.

## Decisão

### 1. `ECOSFERA_ENGINES_FRAMEWORK` passa a `true` por padrão

O caminho de simulação de produção é a moldura. Desligar a flag **não é um modo
equivalente**: volta ao `TickOrchestrator` monolítico, com o efeito estufa linear
e o carbono no `chemistry`. É rollback de emergência, e o ADR 0010 explica por
que as duas trajetórias divergem.

### 2. `geology` e `climate` saem do LegacySubsystemAdapter

Viraram Engines. O adaptador fica com `physics`, o ciclo água/gelo do
`chemistry`, o `ocean` (menos o calor) e o `life` — e passa a **ler** as fatias
novas para montar o `PlanetState` que entrega aos subsistemas restantes. Ele lê o
mundo inteiro e escreve só a sua parte, que é o que a Spec §3 pede de qualquer
Engine.

`chemistry` e `ocean` continuam no adaptador até o M2, coexistindo com os Engines
novos sem quebra — verificado em teste.

### 3. O feedback causal do tutor passa a consumir o Event Store

`ExplainFromEventsUseCase` lê a trilha de eventos (Canal B) e a traduz em
observações para o motor de regras determinístico de sempre. Continua **sem
LLM** — isso é o M6.

`AdvanceEraUseCase` usa esse caminho em produção: os eventos do tick sobem pelo
`TickResult` (que o `FrameworkTickOrchestrator` preenche e o orquestrador legado
deixa vazio, porque não emite eventos) e a era é narrada a partir deles.

**Recuo deliberado.** Quando a era não produz ocorrência notável alguma — o caso
comum, já que o Canal B registra travessia de patamar e não o contínuo — a
narração recai sobre o delta agregado. Devolver explicação vazia seria regressão
pedagógica, e o delta agregado é estado PUBLICADO, não memória interna de Engine:
o recuo não viola a fronteira do ADR-ARCH-0001.

A resposta traz `narrated_from` (`events` | `state_delta`) como DADO. Sem ele,
saber qual caminho foi usado exigiria heurística sobre o conteúdo da explicação —
e auditabilidade por adivinhação não é auditabilidade.

Duas fronteiras deliberadas: o consumidor **não importa nenhum Engine** (conhece
o vocabulário dos eventos, que vem de `configs/event_observations.yaml`
versionado, e isso é verificado por teste), e **não escreve prosa científica** —
o evento traz `cause_code` estruturado, a frase sai das regras.

### 4. A proveniência causal vive no snapshot, não no Planet Engine

Encadear `causation_id` exige saber qual evento produziu o valor corrente de cada
fatia. Guardar isso num atributo do Planet Engine o tornaria estatal, e `tick()`
deixaria de ser função pura do snapshot — o que replay e `stepper` dependem.

A proveniência entrou no `WorldStateSnapshot`. Como é derivada de um fluxo de
eventos determinístico, o replay a reproduz idêntica; e como atravessa ticks, uma
erupção no tick 51 consegue explicar o forçamento que cruza o patamar no tick 63.
Sem isso, só encadeariam eventos coincidentes no mesmo tick, o que quase nunca
acontece numa cadeia com acumulação.

### 4b. Limitação conhecida: o estado persistido ainda é o `PlanetState` legado

A borda HTTP e a persistência guardam `PlanetState`, não `WorldStateSnapshot`.
Isso **trunca o snapshot a cada tick**: `greenhouse_forcing`, `pressure`,
`co2_flux` e a **proveniência causal** não têm campo onde caber e voltam a zero.

Consequências, medidas e delimitadas:

- **A física está intacta.** Forçamento, pressão e fluxo são funções puras de
  grandezas que sobrevivem (CO₂, vulcanismo), então são recalculadas idênticas.
- **A detecção de travessia de faixa precisou mudar.** Comparar contra um
  forçamento recém-zerado disparava `GreenhouseForcingChanged` em TODO tick — 65
  eventos em 80 ticks no smoke test. A faixa anterior passou a ser derivada do
  **estoque de CO₂**, que sobrevive. Caiu para 2 eventos, e a derivação é robusta
  nos dois caminhos.
- **O encadeamento causal entre ticks só vale no caminho puro.** Pelo HTTP,
  `causation_id` liga apenas eventos do MESMO tick. A cadeia
  erupção(t51)→forçamento(t63)→clima(t65) é reproduzível e testada com o Planet
  Engine direto, mas não sobrevive à persistência atual.

Fechar isso é trabalho do **M5** (Persistence + Event Store completo), quando o
`WorldStateSnapshot` inteiro passar a ser a unidade persistida. Até lá a
limitação está fixada por teste, para não virar regressão silenciosa.

### 5. `consequences` é projeção do Event Store, não saída do Engine

Um Engine não pode preencher `consequences` na emissão: no instante em que emite,
os efeitos ainda não aconteceram, e adivinhá-los exigiria saber o que os Engines
seguintes vão fazer. A ligação para a frente é obtida invertendo `causation_id`
(`causal_trace`), do lado do consumidor.

## Consequências

+ O feedback `vulcanismo → CO₂ → forçamento → temperatura` é observável em
  produção, nos eventos e no world-state, e reprodutível por semente.
+ O Tutor tem uma trilha limpa e auditável, sem inspecionar memória de Engine.
+ Os contratos HTTP não mudaram: as rotas de tick, era, timeline e replay
  continuam idênticas, agora servidas pela moldura.
+ Trocar o Event Store em memória por Postgres (M5) não toca em nenhum Engine.
− Duas rotas de tick a manter enquanto a flag existir. Ela deve ser removida
  quando o M2 esvaziar a `LegacySlice`; mantê-la além disso preservaria a ciência
  antiga em produção sem motivo.
− A proveniência entra na comparação bit-a-bit do snapshot. É determinística,
  então isso é correto — mas significa que mudar o esquema de identificadores de
  evento invalida checkpoints gravados, e exigirá subir `WORLD_STATE_VERSION`.
