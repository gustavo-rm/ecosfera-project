# ADR 0005 — Persistência real em Postgres com SQLAlchemy async + Alembic

## Status
Aceito.

## Contexto
Até aqui o `PlanetRepository` só tinha adaptador em memória: o estado se perdia a
cada restart, inviabilizando a linha do tempo (ADR 0004) fora de um único
processo. O Postgres já existe no `docker-compose` do serviço (Inc 0/1) e o
platform-api já o usa — falta o serviço de IA passar a gravar de verdade.

## Decisão

**SQLAlchemy 2.0 assíncrono (driver asyncpg).** O serviço é FastAPI async de ponta
a ponta; um driver síncrono bloquearia o event loop a cada checkpoint. Usa-se
SQLAlchemy Core com SQL explícito (`text()`), não o ORM: as consultas são poucas e
simples, e o SQL à mão é mais legível e auditável — coerente com as migrations,
que também são escritas à mão neste repositório.

**Schema dedicado `simulation`, com três tabelas:**

| Tabela | Natureza | Papel |
| --- | --- | --- |
| `planets` | upsert | projeção do estado **corrente** (uma linha por planeta) |
| `era_checkpoints` | **append-only** | histórico de eras; `UNIQUE (planet_id, era)` |
| `event_log` | **append-only** | intervenções e marcos |

A distinção é intencional: as duas tabelas append-only nunca sofrem UPDATE/DELETE
em operação normal — é o que preserva a auditabilidade exigida pelo Dossiê §9. A
unicidade `(planet_id, era)` torna a gravação **idempotente**: reprocessar uma era
não a duplica nem reescreve o passado.

**Estado em JSONB, não em colunas.** O `PlanetState` ganha campos a cada
incremento (física, geologia, oceano neste; ecologia e evolução nos próximos) e um
schema colunar exigiria migration a cada mudança. A leitura ignora chaves
desconhecidas e usa os defaults da dataclass para as ausentes, de modo que
checkpoints antigos permanecem legíveis (compatibilidade nos dois sentidos). O
preço — não dá para filtrar/indexar por variável física com a mesma eficiência —
é aceitável: as consultas do serviço são por `planet_id`/`era`, não analíticas.

**Seleção por feature flag** (`ECOSFERA_PERSISTENCE_BACKEND=inmemory|postgres`,
default `inmemory`). O import do adaptador Postgres é **preguiçoso** (dentro do
composition root): o serviço sobe e a suíte determinística roda sem o extra
`infra` instalado. O adaptador in-memory é mantido de propósito — testes de
unidade não devem exigir banco nem container.

**Alembic:** o serviço já tinha `alembic.ini` e a migration `0001` (schema `rag`).
Mantivemos **uma única árvore** de migrations cobrindo todos os schemas Python do
serviço; a `0002` cria o schema `simulation`. O `env.py` foi estendido para:
- aceitar URL **síncrona e assíncrona** (a mesma `DATABASE_URL` do adaptador
  serve para migrar, sem exigir um segundo driver);
- **criar o schema da tabela de versão** se ausente, para que as migrations
  rodem num banco efêmero (Testcontainers), que não passa pelo `initdb` do compose.

## Consequências
+ A porta `PlanetRepository` não mudou: nenhuma camada acima sabe que existe SQL.
+ Trocar de backend é uma variável de ambiente; o rollback é imediato.
+ Testcontainers cobre o adaptador contra um Postgres real (imagem `pgvector`,
  necessária porque a migration `0001` cria a extensão `vector`).
− **Débito de nomenclatura:** a tabela de versão do Alembic vive no schema `rag`,
  herdado de quando esse era o único schema do serviço. O nome remete ao primeiro
  schema, não ao conteúdo. Movê-la exigiria migrar o estado de bancos já
  migrados; fica registrado para tratamento junto com a unificação de ADRs.
− Duas fontes de estado corrente (`planets` e o último `era_checkpoint`) podem
  divergir se o tick fino rodar sem fechar era — aceitável e esperado: a projeção
  é conveniência de leitura, a verdade auditável é a cadeia append-only.
