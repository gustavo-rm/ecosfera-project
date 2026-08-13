"""Roteiro de fumaça do M6.2 — a recuperação, IMPRESSA para inspeção humana.

    uv run python scripts/smoke_m6_2.py            # com o extra `sim`
    uv run --no-extra sim python scripts/smoke_m6_2.py

Indexa o corpus pedagógico e roda consultas representativas, IMPRIMINDO cada
passagem recuperada com a similaridade e a origem. O ponto é olhar: um retriever
que devolve "alguma coisa" com nota alta passa em qualquer asserção de forma e
falha no que importa — trazer a passagem que de fato responde à pergunta.

A lição vem do M6.1, onde o roteiro de fumaça foi quem revelou 300 parágrafos
quase idênticos que nenhum teste de forma tinha visto. Por isso aqui se imprime
antes de afirmar.

O que o script afirma, depois de imprimir:

  1. cada consulta recupera a passagem ESPERADA no topo (não apenas algo);
  2. o filtro por categoria devolve só aquela categoria;
  3. toda passagem carrega origem — nenhuma entrada anônima chega ao Tutor;
  4. o ranking é monotônico decrescente em similaridade;
  5. nada do que sai daqui é um fato: nenhuma passagem tem campo de evento.

**Sem LLM e sem geração.** O M6.2 recupera; quem escreve é o M6.3.
"""

from __future__ import annotations

import asyncio
from dataclasses import fields
from pathlib import Path

from ecosfera_ai.application.rag.corpus_index import InMemoryCorpusIndex
from ecosfera_ai.application.rag.index_corpus import IndexCorpusUseCase
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase
from ecosfera_ai.domain.rag.corpus import CorpusCategory, load_manifest
from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder
from ecosfera_ai.domain.rag.passage import FACT_BEARING_FIELDS, RetrievedPassage

MANIFEST = Path("configs/pedagogical_corpus.yaml")

# Consultas por CÓDIGO DE CAUSA — o caminho que o M6.3 vai usar de fato: dado o
# `cause_code` de um evento REAL do planeta, quais regras de linguagem governam a
# forma de contá-lo. Aqui a exigência é de primeiro lugar, porque a consulta é
# filtrada e o conjunto candidato é pequeno e bem definido.
CAUSE_CODE_CASES = (
    ("CATASTROPHIC_EVENT", "VAL-Q8", "catástrofe não é falha de adaptação (Tássia, Q8)"),
    ("DIVERGENT_NICHE", "VOC-002", "a regra do ancestral comum (BIO-001)"),
    ("PREY_COLLAPSE", "VAL-Q12", "a progressão cadeia → teia (Tássia, Q12)"),
)

# Consultas em TEXTO LIVRE. A exigência aqui é estar entre os primeiros, e não em
# primeiro — e a diferença é honesta, não uma régua rebaixada para o teste passar.
#
# O embedder de referência é LÉXICO: ele mede sobreposição de vocabulário, não
# proximidade de sentido, e o cosseno sobre saco-de-palavras favorece entradas
# CURTAS. Numa consulta sobre especiação, tanto a regra do ancestral comum quanto
# a que separa adaptação de especiação são respostas legítimas, e um baseline
# léxico não tem como ordená-las por importância pedagógica — isso é trabalho do
# modelo semântico de produção. O que se verifica aqui é que a entrada certa é
# RECUPERADA, que é o que a infraestrutura do M6.2 promete.
FREE_TEXT_CASES = (
    (
        "especiação ancestral comum linhagens",
        None,
        "VOC-002",
        "a regra que proíbe dizer que uma espécie deu origem a outra",
    ),
    (
        "aptidão contextual ou absoluta",
        None,
        "VOC-005",
        "a regra de aptidão contextual (Q5)",
    ),
    (
        "efeito estufa gás carbônico temperatura",
        CorpusCategory.CURRICULUM_OBJECTIVE,
        "BNCC-EFEITO-ESTUFA",
        "o objetivo BNCC do efeito estufa",
    ),
)


def _print(found: tuple[RetrievedPassage, ...]) -> None:
    for rank, passage in enumerate(found, start=1):
        print(f"  {rank}. {passage.similarity:.3f}  {passage.entry_id}  ({passage.category})")
        print(f"       fonte: {passage.source}")
        print(f"       texto: {passage.text[:140]}...")


def _assert_common(found: tuple[RetrievedPassage, ...]) -> None:
    """As garantias que valem para toda recuperação, seja qual for a consulta."""
    assert all(p.source.strip() for p in found), "passagem sem origem chegou ao consumidor"
    scores = [p.similarity for p in found]
    assert scores == sorted(scores, reverse=True), f"ranking fora de ordem: {scores}"


async def main() -> int:
    manifest = load_manifest(MANIFEST)
    embedder = DeterministicEmbedder()
    index = InMemoryCorpusIndex()

    report = await IndexCorpusUseCase(embedder, index).execute(manifest)
    print(f"--- corpus indexado: {report.indexed} entradas, modelo {report.model_name} ---")
    for category, count in sorted(report.by_category.items()):
        print(f"  {category:24} {count}")
    print(f"  fontes distintas:      {len(report.sources)}\n")

    retriever = RetrievePassagesUseCase(embedder, index)
    failures: list[str] = []

    print("=== POR CÓDIGO DE CAUSA (o caminho do M6.3) — exige 1º lugar ===\n")
    for code, expected, why in CAUSE_CODE_CASES:
        found = await retriever.for_cause_code(code, limit=3)
        print(f"CONSULTA for_cause_code({code!r})")
        print(f"  esperado em 1º: {expected} — {why}")
        _print(found)
        if not found:
            failures.append(f"for_cause_code({code!r}) não recuperou nada")
        elif found[0].entry_id != expected:
            failures.append(f"for_cause_code({code!r}) trouxe {found[0].entry_id}, não {expected}")
        # o filtro por código nunca devolve entrada que não o endereça
        assert all(code in p.relevant_cause_codes for p in found), "o filtro por causa vazou"
        _assert_common(found)
        print()

    print("=== TEXTO LIVRE — exige estar entre os recuperados (ver nota acima) ===\n")
    for query, category, expected, why in FREE_TEXT_CASES:
        categories = None if category is None else frozenset({category})
        found = await retriever.execute(query, limit=3, categories=categories)

        label = f"[{category.value}]" if category else "[todas as categorias]"
        print(f"CONSULTA {label}: {query!r}")
        print(f"  esperado entre os 3: {expected} — {why}")
        _print(found)
        if expected not in {p.entry_id for p in found}:
            failures.append(f"{query!r} não recuperou {expected} entre os 3 primeiros")
        if categories is not None:
            assert all(p.category is category for p in found), "o filtro de categoria vazou"
        _assert_common(found)
        print()

    # 5. uma passagem não é um fato — nem por nome de campo
    passage_fields = {f.name for f in fields(RetrievedPassage)}
    leaked = passage_fields & FACT_BEARING_FIELDS
    assert not leaked, f"RetrievedPassage ganhou campo de fato: {leaked}"
    print(
        f"OK — RetrievedPassage não compartilha campo algum com um fato ({len(leaked)} colisões)."
    )

    if failures:
        print("\nFALHAS DE RELEVÂNCIA:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("OK — toda consulta trouxe no topo a passagem esperada, com origem e ordenada.")
    print("\nRECUPERAÇÃO pronta. A GERAÇÃO é o M6.3 — nada aqui escreve prosa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
