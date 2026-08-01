# ADR 0015 — A dívida de rehidratação do world-state, vigiada até o M5

## Status
Aceito como **dívida explícita**, não como solução. Registra formalmente o que o
ADR 0012 §6 decidiu e o ADR 0011 §4b já antecipava. Vence no **M5** (Persistence
+ Event Store completo). Referências: Spec §3/§7, RF-016, RF-023.

Este ADR é curto de propósito: ele não decide nada novo. Existe para que a dívida
tenha rastro, dono e data de vencimento — e, sobretudo, um **guardião executável**.

## Contexto

A borda HTTP e a persistência guardam `PlanetState`, não `WorldStateSnapshot`.
`FrameworkTickOrchestrator.tick()` faz o ciclo completo a CADA tick:

```
PlanetState → snapshot_of → [8 Engines] → planet_state_of → PlanetState
```

Consequência: **um campo sem lugar no `PlanetState` volta a zero uma vez por
tick.** O Engine que o escreveu continua correto, o teste de unidade dele
continua verde, e a grandeza simplesmente nunca realimenta nada.

O M2 fechou o buraco ampliando o `PlanetState` com os estoques das fatias novas
(ADR 0012 §6). A solução é correta e barata — o estado é gravado como JSONB
justamente para que ganhar campos não exija migration — mas é **paliativa**: ela
duplica o esquema do world-state num segundo lugar que precisa ser mantido em dia
à mão.

## O risco que sobra

O perigo não é o que o M2 corrigiu. É o **próximo** Engine.

O M4 traz o Event Engine, que acrescenta estado. Se a fatia dele não for mapeada
na ponte, o defeito volta — e volta em silêncio, que é o que o torna caro. É
exatamente o padrão da falha do `solar_flux` (ADR 0013 §2): o sintoma é
*ausência*, e ausência não se denuncia sozinha. Nada estoura; um número apenas
fica parado, plausível, errado.

Três atributos tornam essa classe de defeito especialmente cara:

1. **Não quebra teste de Engine.** O Engine escreve seu delta corretamente; a
   perda acontece depois, na costura.
2. **Não quebra invariante.** Zero é um valor válido para quase toda grandeza.
3. **Produz números plausíveis.** Uma temperatura sem forçamento continua sendo
   uma temperatura. Num produto cujo resultado é *ensinar ciência correta*, isso
   significa um aluno aprendendo uma relação que o modelo não está de fato
   calculando.

## Decisão

### 1. A dívida fica registrada, com vencimento no M5

Substituir o `PlanetState` pelo `WorldStateSnapshot` como unidade persistida é
trabalho do M5. Até lá, a duplicação de esquema é aceita conscientemente.

### 2. E fica **vigiada** por um teste que falha por omissão

`tests/integration/test_snapshot_roundtrip.py` inverte o padrão: **toda fatia,
todo campo, DEVE sobreviver ao round-trip**. As exceções são declaradas uma a uma
em `DERIVED_FIELDS`, com o motivo pelo qual o valor é recuperável.

O teste é parametrizado por `SliceRef`, não por uma lista escrita à mão. Um
Engine novo entra sob a regra **sozinho**, no dia em que sua fatia entrar no
enum — quem o escrever não precisa lembrar deste arquivo. A mensagem de falha diz
o que fazer:

> a ponte perdeu campos de `chemistry`: ['methane']. Ou o campo entra no
> `PlanetState` (engines/bridge.py), ou é declarado em DERIVED_FIELDS com o
> motivo pelo qual é recuperável.

Uma lista de campos a CONFERIR faria o oposto: protegeria só o que alguém lembrou
de listar, que é precisamente o esquecimento que se quer pegar.

O guardião foi verificado contra o defeito que ele existe para pegar — um campo
novo numa fatia, sem mapeamento na ponte — e falha com a mensagem acima.

### 3. As exceções precisam se provar exceções

`DERIVED_FIELDS` hoje tem três campos: `geology.co2_flux`,
`atmosphere.greenhouse_forcing` e `atmosphere.pressure`. Todos são funções puras
de estoques que sobrevivem, então o primeiro tick os recalcula idênticos.

Isso não fica na palavra de quem escreveu: `test_the_declared_losses_really_are_recoverable`
roda um tick pelos dois caminhos (direto e pela ponte) e exige que os valores
coincidam. Declarar um campo como derivado sem que ele se recupere quebra o
teste — a exceção tem de ser verdade, não conveniência.

### 4. A dívida é bidirecional

`test_the_planet_state_carries_no_field_the_bridge_ignores` verifica o sentido
inverso: um campo escrito no `PlanetState` e nunca reconstruído no snapshot é a
mesma armadilha vista do outro lado.

## Consequências

+ A dívida deixou de depender de memória humana: um Engine novo que a reabra
  quebra o build, com mensagem que aponta o arquivo a editar.
+ As exceções são auditáveis e auto-verificadas.
+ O M5 tem um critério de pronto concreto: quando o `WorldStateSnapshot` for a
  unidade persistida, este ADR e o arquivo de teste podem ser removidos juntos.
− O `PlanetState` duplica o esquema do world-state até lá, e as duas listas
  precisam ser mantidas coerentes — o teste garante a coerência, mas não elimina
  o trabalho.
− `DERIVED_FIELDS` é um ponto de pressão: é fácil "resolver" uma falha
  acrescentando o campo à lista de exceções em vez de persistindo-o. O teste do
  §3 é a defesa contra isso, e a revisão precisa saber que ela existe.
