# ADR 0021 — Event Store persistente e simulação portável

## Status
Aceito. Abre o M5 (Plataforma). Estende o schema do **M2**; paga a dívida de
rehidratação registrada no **ADR 0015**; instrumenta — sem tocar — a dívida do
**ADR 0020**. Referências: Spec §1/§4/§7/§8, ADR-ARCH-0001 (Emenda 3),
ADR-ARCH-0002, RF-016, RF-023, RNF-009.

## Contexto

O M5 transforma a camada de Plataforma de versão mínima em produto sério. Não
adiciona ciência nem Engine: consolida persistência e observabilidade.

## Decisão

### 1. O Event Store ESTENDE o schema do M2 — não há segundo mecanismo

O M2 criou `simulation.event_log` com o mínimo: `planet_id, tick, event_type,
payload`. Servia à linha do tempo e **não serve ao Event Store** — o envelope §4
(`cause_code`, `correlation_id`, `causation_id`, `era`, `engine_id`,
`granularity`) ficava inteiro dentro do JSONB, e consultar por correlação ou por
causa exigiria varrer a tabela.

A migration `0004` promove o envelope a **colunas** e cria os índices que
sustentam o contrato de query. As colunas são NULLABLE de propósito: as linhas
que o M2 gravou continuam válidas, sem backfill — elas não têm envelope, e essa é
a verdade sobre elas.

**`event_id` ganha índice único.** O identificador é determinístico (uuid5 sobre
seed/engine/tick/sequência), então reprocessar a mesma corrida não pode duplicar
a trilha. Com o índice, a idempotência é propriedade do BANCO e não da disciplina
de quem escreve — o que a torna confiável sob replay e reimport.

### 2. A serialização do estado sobe da infraestrutura para o domínio

`PlanetState.to_dict/from_dict` moram agora no domínio. Export portável, Event
Store e persistência precisam da MESMA forma canônica; mantê-la no adaptador
Postgres obrigava a camada de aplicação a importar infraestrutura para exportar —
a inversão que a hexagonal proíbe (ADR 0001). O adaptador delega.

A tolerância a chaves desconhecidas — o que permitiu ao M3 acrescentar fatias sem
migration — fica documentada com o preço dela: cobre ACRÉSCIMO, não troca de
esquema. Um campo removido é descartado em silêncio, e é por isso que o artefato
portável carrega `world_state_version` e recusa versões diferentes.

### 3. A simulação vira ARTEFATO portável (critério da Spec §8)

O export carrega seed, versão dos params, versão do world-state, checkpoints por
era e o Canal B com o envelope íntegro. Serializa **deterministicamente** (chaves
ordenadas), de modo que dois exports da mesma simulação dão o mesmo arquivo byte
a byte — o que permite comparar artefatos por hash sem reimportar.

**Importar errado FALHA alto.** Versão de formato ou de world-state diferente é
recusa, não degradação. Um import silenciosamente degradado produziria um planeta
PARECIDO com o original, e a diferença só apareceria como divergência de replay
muito depois, quando ninguém mais associa a causa. Pelo mesmo motivo, um
`cause_code` que este binário não conhece levanta erro em vez de virar `None`:
uma causa não interpretável viraria explicação errada ao aluno.

A verificação faz parte do import: o replay a partir do artefato reproduz o
original bit-a-bit, e isso é teste, não promessa.

### 4. O que o artefato NÃO carrega — retenção e LGPD

Nenhum dado de aluno. O artefato é da SIMULAÇÃO: planeta, física, biologia,
trilha de eventos do motor. A telemetria pedagógica (RF-071) vive em outra trilha,
com consentimento e retenção próprios (RNF-009), e misturá-las aqui faria de todo
export de pesquisa um export de dado pessoal.

O M5 **não introduz coleta nova**. A política que ele fixa é de fronteira: o
export de simulação é publicável e compartilhável porque, por construção, não
contém pessoa alguma. Qualquer junção futura entre trilha de simulação e
identidade de aluno exige decisão própria e não pode ser feita neste artefato.

### 5. Verificação de persistência é gate de CI, não caixa marcada

Os testes de Event Store persistente exigem Postgres real (Testcontainers). Numa
máquina de desenvolvimento sem Docker eles pulam, o que é honesto. No CI,
`ECOSFERA_REQUIRE_POSTGRES=1` transforma a ausência em **falha**.

Isso fecha um risco concreto: o CI já rodava esses testes — 581 no CI contra 574
localmente, exatamente os 7 que pulam sem Docker —, mas **por acaso**, porque o
runner `ubuntu-latest` traz um daemon Docker. Um runner futuro sem ele silenciaria
a suíte inteira de persistência e deixaria a árvore verde, atestando uma
verificação que não aconteceu. O pulo continua disponível onde é honesto e deixou
de estar disponível onde seria esconderijo.

## Consequências

**Ganhamos.** Uma simulação atravessa máquinas: o pesquisador leva a corrida, o
professor recebe o planeta da turma, e um bug de campo vira artefato anexado ao
relato. E o envelope é indexável, o que torna o contrato de query do M6 viável
sem varredura.

**Perdemos.** O artefato é acoplado à versão do esquema. É deliberado — a
alternativa (migrar artefatos antigos silenciosamente) troca uma falha visível por
uma divergência invisível.
