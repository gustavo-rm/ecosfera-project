# Matriz de verificação de CI — o que é verificado, por quem, e o que aconteceria se falhasse

Este serviço já pagou duas vezes pela mesma classe de defeito: algo **declarado**
que ninguém **exercitava**. O campo `atmosphere.oxygen` existia sem escritor e
valia zero em toda corrida; o filtro `EventQuery.planet_id` era aceito e nunca
aplicado. Os dois passaram por marcos inteiros com a árvore verde.

Uma suposição tácita sobre o próprio CI é a versão mais perigosa disso, porque é
a que valida todas as outras. Esta matriz existe para que "os testes de
persistência rodam no CI" nunca mais seja algo que alguém **acredita**.

**Regra:** toda linha aqui tem um mecanismo que FALHA. Uma linha cujo "como
falha" for "ninguém percebe" não pertence a esta tabela — pertence à lista de
lacunas conhecidas, no fim.

## A matriz

| # | O que se afirma | Verificado por | Onde | Como falha |
|---|---|---|---|---|
| 1 | O ambiente de CI **pode** verificar persistência | passo `Verificar que a persistência é verificável aqui` | workflow, antes do lint | falha o job com `::error::` se `ECOSFERA_REQUIRE_POSTGRES != 1` ou `docker info` não responde |
| 2 | Sem Docker, persistência **falha** em vez de pular | marca `fail_without_docker` (`docker_guard.requires_postgres`) | `pytest_runtest_setup` | `AssertionError` em cada teste marcado |
| 3 | **Nenhum** teste de infraestrutura pulou | hook `pytest_sessionfinish` | `tests/conftest.py` | `exitstatus = 1` listando cada pulo — pega inclusive `skipif` artesanal que não usa a marca |
| 4 | Imagem do Postgres serve às migrations | `POSTGRES_IMAGE` em `docker_guard` | constante única | migration 0001 (`CREATE EXTENSION vector`) estoura no `alembic upgrade head` |
| 5 | As migrations aplicam limpas | `run_migrations` nas fixtures | cada módulo de persistência | erro do Alembic aborta a fixture |
| 6 | Colunas e índices do envelope §4 existem | `test_the_migration_adds_the_envelope_columns`, `test_the_query_indexes_exist` | `test_event_store_persist_and_query` | asserção contra `pg_indexes`/`information_schema` |
| 7 | `event_id` é único **por planeta** | `test_the_same_event_cannot_be_stored_twice` + `test_the_same_event_id_is_allowed_in_a_different_planet` | idem | `IntegrityError` esperado num sentido, ausente no outro |
| 8 | Um planeta não vaza no outro | `test_planet_isolation_no_cross_leak` (6 testes) | integração | marca `owner` em `cause_detail` denuncia o evento do planeta errado |
| 9 | In-memory e Postgres concordam | `test_query_contract_parity` (15 testes) | integração | conjuntos de `event_id` divergentes, ou envelope diferente no round-trip |
| 10 | O adaptador satisfaz a porta | `_port_conformance` | `postgres_event_store.py` | `mypy --strict` reprova a atribuição |
| 11 | Nenhum campo de query é decorativo | `test_no_phantom_filters` | unidade | campo que não exclui, ou que rejeita tudo |
| 12 | Fronteiras de import | 6 contratos `import-linter` | `pyproject.toml` | contrato BROKEN |

## Como cada mecanismo foi provado a morder

Um portão nunca exercitado é indistinguível de um portão quebrado. Cada um foi
verificado invertendo-o de propósito:

| Mecanismo | Como foi provado |
|---|---|
| Contratos de import-linter | import proibido inserido → `1 broken`, depois removido |
| `_port_conformance` | ordem dos parâmetros invertida → mypy reprovou, depois restaurada |
| Hook de zero-skip (#3) | arquivo com `skipif` artesanal → `exit=1` com a flag, `exit=0` sem ela |
| Guard `fail_without_docker` (#2) | `ECOSFERA_REQUIRE_POSTGRES=1` sem Docker → 5 erros, não 5 pulos |
| Gate de CI como um todo | o run #10 **reprovou** de verdade, pegando o índice que a 0005 invalidou |

## O histórico, para a afirmação não depender de memória

A pergunta "o CI roda mesmo os testes de Postgres?" tem resposta documentada,
não lembrada. Todo run que chegou ao passo de testes, desde o M4:

| Run | SHA | Marco | Resumo | Skips |
|---|---|---|---|---|
| #6 | `80c658e` | M4 | `581 passed, 1 xfailed` | **0** |
| #7 | `dfcece9` | M5 | reprovou no lint | testes não rodaram |
| #8 | `68b2037` | M5 | `676 passed, 5 errors` | **0** |
| #9 | `b7b7e3e` | M5 | `681 passed, 1 xfailed` | **0** |
| #10 | `e678053` | fix M5 | `718 passed, 1 failed` | **0** |
| #11 | `ece7f63` | fix M5 | `720 passed, 1 xfailed` | **0** |
| #12 | `590fdf9` | fix M5 | `721 passed, 1 xfailed` | **0** |

Dois desses runs são prova POSITIVA de execução real, não apenas ausência de
pulo — falharam com erros que só um Postgres vivo produz:

* #8 — `asyncpg.exceptions.FeatureNotSupportedError: extension "vector" is not
  available`, vinda do servidor;
* #10 — `AssertionError: índice event_log_event_id_key ausente`, com a lista real
  de `pg_indexes`.

**Conclusão sobre o M5:** a contagem "581 no CI contra 574 localmente" que o
workflow do M5 afirma foi **observada** no run #6, não calculada. Não houve
regressão nem ilusão — os testes rodaram desde o M4 e seguem rodando. O que
faltava não era execução: era **imposição**. Até agora "zero skips" era conferido
por um humano lendo a linha de resumo e somando à mão, e a linha 3 desta matriz é
o que substitui essa aritmética.

## Lacunas conhecidas — declaradas, não verificadas

Honestidade sobre o que esta matriz **não** cobre:

1. **O laço da simulação não alimenta o Event Store persistente.**
   `advance_era`/`evolve_biology` gravam o formato `EventLogEntry` do M2; o
   envelope §4 só é escrito por quem chamar `PostgresEventStore` diretamente.
   Follow-up declarado no ADR 0023.
2. **Testcontainers depende do daemon Docker do runner.** A linha 1 falha rápido
   e alto se ele sumir, mas a dependência é do ambiente, não declarada no
   workflow. Um `services:` de Postgres a tornaria explícita — ao custo de
   religar seis arquivos de teste e perder o isolamento por módulo (ver adiante).
3. **Traces (pilar 4)** seguem gancho no-op; nada verifica span algum
   (ADR 0022 §5).
4. **A instabilidade de carbono** continua `xfail` anotado (ADR 0020).

## Manutenção

Ao acrescentar um teste que exige infraestrutura, use
`pytestmark = requires_postgres()` — nunca um `skipif` próprio. O hook da linha 3
pega o `skipif` artesanal, mas pegá-lo é o plano B; o plano A é a marca, que
falha por teste e diz qual.

Ao acrescentar uma afirmação nova sobre o CI, acrescente uma linha aqui **com o
"como falha" preenchido**. Se não houver como falhar, não é verificação: é
suposição, e o lugar dela é a lista de lacunas.
