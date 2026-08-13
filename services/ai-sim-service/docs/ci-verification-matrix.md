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
| 12 | Fronteiras de import | 8 contratos `import-linter` | `pyproject.toml` | contrato BROKEN |
| 13 | O consumidor read-side **não** alcança Engine nem world-state | contrato `Consumidores read-side so alcancam o Event Store` + `test_consumer_reads_only_event_store` | `pyproject.toml` / contrato | contrato BROKEN; e a varredura por AST nomeia o arquivo e o import |
| 14 | O M6.0 **não** depende de LLM nem de RAG | contrato `A fundacao factual do M6.0 nao depende de LLM nem de RAG` | idem | contrato BROKEN ao primeiro import de `ollama`/embeddings/`rag` |
| 15 | O vocabulário duplicado do consumidor **não** divergiu dos Engines | `test_consumer_vocabulary_matches_engines` | contrato | igualdade termo a termo falha nomeando o termo que divergiu |
| 16 | O dossiê factual sobre o Event Store **real** é o mesmo que em memória | `test_factual_context_over_postgres` (6 testes) | integração | dossiês diferentes — pega perda parcial no `payload` JSONB, que um teste de "tem conteúdo" não veria |
| 17 | Toda afirmação da prosa vem de um campo do dossiê | `test_every_claim_is_grounded_in_context` | unidade | fato sem evento, campo que não resolve, número sem slot, ou resumo que diverge dos fatos — cada um com contraprova do próprio filtro |
| 18 | A extinção catastrófica nunca é narrada como falha de adaptação | `test_catastrophic_extinction_reads_as_chance` | unidade | lista de formulações que culpam a comunidade, mais a exigência de nomear o gatilho vindo do `causation_id` real |
| 19 | Especiação é inexprimível como "A deu origem a B" **em prosa** | `test_speciation_renders_as_common_ancestor` | unidade | o template ganha slot de linhagem (falha estrutural), ou a frase perde "ancestral comum"/"irmãs" |
| 20 | A guarda anti-teleológica da Fase 0 ALCANÇA a prosa nova | `test_non_teleological_wording_preserved` | contrato | o arquivo de templates sai da coleta de `_templates()` — cobertura afirmada, não suposta |
| 21 | Todo `cause_code` tem frase OU silêncio declarado | `test_every_cause_code_has_a_mechanism_phrase_or_is_declared_unnarrated` | contrato | código novo sem oração de mecanismo e fora de `not_narrated`, nomeando o código |
| 22 | Há UM narrador de eventos depois do M6.1 | `test_single_explainer_after_integration` | contrato | módulo novo importando o renderizador fora da lista, ou prosa de aluno hardcoded no código |
| 23 | A explicação não depende de LLM nem de RAG | `test_no_llm_dependency` + contrato `import-linter` | contrato | import direto (varredura AST) ou indireto (grafo do import-linter) em qualquer módulo do caminho evento → prosa |
| 24 | Toda entrada do corpus tem origem; externa tem licença | `test_corpus_manifest_has_required_provenance` + `CHECK` da migration 0006 | unidade + integração | entrada anônima ou referência sem licença — recusada pelo modelo E pelo banco |
| 25 | Nenhum código BNCC foi inventado | `test_corpus_contains_no_fabricated_curriculum` | unidade | código que não aparece no texto do Dossiê, ou "(conferir)" promovido a verificado |
| 26 | Passagem recuperada não pode ocupar o lugar de um fato | `test_retrieved_passage_is_not_a_fact_type` | unidade | campos disjuntos, sem parentesco, e o `mypy` EXECUTADO sobre a atribuição proibida |
| 27 | O RAG recupera e não gera | `test_no_generation_this_layer` + 2 contratos `import-linter` | contrato | import de LLM, alcance ao Event Store, ou composição de texto a partir de passagens |
| 28 | pgvector concorda com a implementação de referência | `test_pgvector_over_postgres` (13 testes) | integração | ordem ou score divergentes entre o `<=>` do banco e o cosseno em Python |
| 29 | Uma consulta nunca vê vetores de outro modelo | `test_a_query_never_sees_another_models_vectors` | integração | linha de outro modelo, gravada com vetor máximo, aparecendo no resultado |

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
5. **O corpus do M6.2 nunca foi indexado com o modelo SEMÂNTICO.** A política de
   rede deste ambiente nega `huggingface.co` e o CI não instala o extra `ai`, então
   `SentenceTransformerEmbedder` teve a lógica testada com carregador injetado, e
   não uma execução com pesos reais. Declarado no ADR 0027; é a primeira coisa a
   provar num ambiente com acesso.
6. **O dossiê factual do M6.0 não tem rota HTTP**, então nada o exercita pela
   borda. É consequência da lacuna 1, e não descuido: o Event Store do processo é
   uma lista única, não escopada por planeta, e servir uma rota a partir dele
   reintroduziria o vazamento do ADR 0023 na própria fundação anti-alucinação
   (ADR 0025). O que existe hoje é `scripts/smoke_m6_0.py`, que roda uma
   simulação real e inspeciona o JSON — verificação de fumaça, **não** de CI.

## Manutenção

Ao acrescentar um teste que exige infraestrutura, use
`pytestmark = requires_postgres()` — nunca um `skipif` próprio. O hook da linha 3
pega o `skipif` artesanal, mas pegá-lo é o plano B; o plano A é a marca, que
falha por teste e diz qual.

Ao acrescentar uma afirmação nova sobre o CI, acrescente uma linha aqui **com o
"como falha" preenchido**. Se não houver como falhar, não é verificação: é
suposição, e o lugar dela é a lista de lacunas.
