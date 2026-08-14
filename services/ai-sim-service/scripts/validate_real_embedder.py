"""Portão do M6.3: o embedder SEMÂNTICO de verdade, medido contra o de referência.

    uv run --extra ai python scripts/validate_real_embedder.py

O M6.2 entregou a infraestrutura de RAG com uma lacuna declarada em voz alta no
ADR 0027: `SentenceTransformerEmbedder` nunca rodou com pesos baixados. A
política de rede do ambiente de desenvolvimento nega `huggingface.co` (403 no
CONNECT), e o CI daquele marco sincronizava sem o extra `ai`. A lógica do
adaptador tinha teste; a passagem pelo modelo real, não.

Enquanto essa lacuna existir, o M6.3 estaria construindo geração ancorada sobre
uma recuperação cuja qualidade ninguém mediu. Por isso este roteiro é um PORTÃO,
e não um extra: ele roda no CI, com o extra `ai`, e REPROVA se o modelo real não
alcançar o piso que o embedder de referência já alcança.

## O que se compara, e por que o critério não é o mesmo para todos os casos

Consultas por CÓDIGO DE CAUSA são filtradas por categoria e por código: o
conjunto candidato é pequeno e bem definido, e o baseline léxico já acerta o 1º
lugar. O modelo semântico tem de EMPATAR nesse piso — não há desculpa para
regredir onde a busca é fácil.

Consultas em TEXTO LIVRE são o contrário: o embedder de referência mede
sobreposição de vocabulário e o M6.2 mediu o preço disso (viés de comprimento,
similaridade incomparável entre consultas). Ali o piso é RECUPERAR entre as
primeiras, e a posição — melhorou, empatou ou piorou — é impressa dos dois lados
antes de qualquer afirmação.

Em ambos os casos o alvo é um CONJUNTO de entradas aceitáveis, e não uma entrada
única; a nota longa sobre `CAUSE_CODE_CASES` explica por que, com os dois casos
medidos que obrigaram a distinção.

**Uma regressão aqui é achado, não ruído.** Se o modelo semântico piorar em algum
caso, o lugar disso é o ADR 0027, ao lado das duas limitações que o M6.2 já mediu.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import replace
from pathlib import Path

from ecosfera_ai.application.rag.corpus_index import InMemoryCorpusIndex
from ecosfera_ai.application.rag.index_corpus import IndexCorpusUseCase
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase
from ecosfera_ai.domain.rag.corpus import CorpusCategory, CorpusManifest, load_manifest
from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder, EmbeddingModel

MANIFEST_PATH = Path("configs/pedagogical_corpus.yaml")

# Os mesmos casos do roteiro de fumaça do M6.2 — de propósito. Comparar contra
# consultas novas mediria outra coisa; o que interessa é se o modelo real
# sustenta o que a infraestrutura já demonstrou com o de referência.
#
# ## Por que cada caso declara um CONJUNTO aceitável, e não uma entrada
#
# A primeira versão exigia UMA entrada específica em 1º e reprovou o modelo real
# em dois casos. Investigados um a um, nenhum dos dois era recuperação errada:
#
#   * `CATASTROPHIC_EVENT` — o modelo pôs VOC-006 à frente de VAL-Q8. As duas
#     declaram `cause_codes: [CATASTROPHIC_EVENT]`, as duas têm tópico "extinção"
#     e as duas dizem a MESMA regra (catastrófica é independente de aptidão; não
#     colapsar com a ecológica). Uma é a regra de vocabulário, a outra é a
#     correção validada que a originou.
#   * "aptidão contextual ou absoluta" — o modelo pôs VAL-Q5 à frente de VOC-005.
#     Mesma relação: as duas afirmam que a aptidão é relacional e não absoluta.
#
# O corpus do M6.2 tem essa forma DE PROPÓSITO: a prioridade declarada põe as
# regras de vocabulário e as correções validadas lado a lado, e conceitos de
# maior risco pedagógico aparecem nas duas categorias. Exigir uma delas em 1º
# testaria um desempate arbitrário entre dois textos que dizem a mesma coisa — e
# o M6.3 recebe as duas de qualquer modo, porque `for_cause_code` traz as duas
# categorias juntas.
#
# O critério passa a ser: em 1º tem de vir uma entrada que CARREGUE a regra que
# governa aquela consulta. O conjunto é fechado e justificado caso a caso, então
# a barra continua mordendo — um objetivo BNCC ou uma regra de outro tópico em 1º
# reprova, e foi exatamente o que quase aconteceu no caso da aptidão, onde
# BNCC-EVOLUCAO-ADAPTACAO ficou em 2º.
CAUSE_CODE_CASES = (
    (
        "CATASTROPHIC_EVENT",
        frozenset({"VAL-Q8", "VOC-006"}),
        "a distinção catastrófica × ecológica (Tássia Q8 e a regra BIO-006)",
    ),
    ("DIVERGENT_NICHE", frozenset({"VOC-002"}), "a regra do ancestral comum (BIO-001)"),
    ("PREY_COLLAPSE", frozenset({"VAL-Q12"}), "a progressão cadeia → teia (Tássia, Q12)"),
)

FREE_TEXT_CASES = (
    (
        "especiação ancestral comum linhagens",
        None,
        frozenset({"VOC-002"}),
        "a regra que proíbe dizer que uma espécie deu origem a outra",
    ),
    (
        "aptidão contextual ou absoluta",
        None,
        frozenset({"VOC-005", "VAL-Q5"}),
        "a aptidão como relação, e não como nota do organismo",
    ),
    (
        "efeito estufa gás carbônico temperatura",
        CorpusCategory.CURRICULUM_OBJECTIVE,
        frozenset({"BNCC-EFEITO-ESTUFA"}),
        "o objetivo BNCC do efeito estufa",
    ),
)

RANK_MISS = 999  # posição sentinela para "não recuperado"


async def _rank_of(
    retriever: RetrievePassagesUseCase,
    query: str,
    acceptable: frozenset[str],
    *,
    category: CorpusCategory | None,
    cause_code: str | None,
    limit: int,
) -> tuple[int, str, tuple[tuple[str, float], ...]]:
    """Melhor posição (1-based) entre as entradas aceitáveis, e qual delas veio.

    A pergunta é "a regra que governa esta consulta chegou ao topo?", e não "esta
    entrada específica chegou ao topo" — ver a nota sobre conjuntos acima.
    """
    categories = frozenset({category}) if category is not None else None
    if cause_code is not None:
        found = await retriever.for_cause_code(cause_code, limit=limit)
    else:
        found = await retriever.execute(query, limit=limit, categories=categories)

    top = tuple((passage.entry_id, passage.similarity) for passage in found)
    for position, passage in enumerate(found, start=1):
        if passage.entry_id in acceptable:
            return position, passage.entry_id, top
    return RANK_MISS, "", top


async def _retriever_for(
    embedder: EmbeddingModel, manifest: CorpusManifest
) -> RetrievePassagesUseCase:
    """Indexa as MESMAS entradas com o embedder pedido, num índice só dele.

    O manifesto declara `ecosfera-deterministic-v1`, e `IndexCorpusUseCase`
    RECUSA indexá-lo com outro modelo — foi a primeira coisa que este roteiro
    encontrou no CI, e a recusa está certa: gravar vetores de um modelo sob o
    nome de outro é exatamente o defeito que o M6.2 fechou pondo `model_name` na
    chave primária.

    Trocar o campo aqui não contorna a guarda, exerce a intenção dela. O que se
    compara são dois espaços vetoriais SEPARADOS, cada um indexado e consultado
    sob o seu próprio nome; o que os dois têm em comum são as entradas do corpus.
    Misturá-los num índice só é que seria o erro.
    """
    index = InMemoryCorpusIndex()
    for_this_model = replace(manifest, embedding_model=embedder.name)
    await IndexCorpusUseCase(embedder, index).execute(for_this_model)
    return RetrievePassagesUseCase(embedder, index)


def _verdict(reference_rank: int, real_rank: int) -> str:
    if real_rank == RANK_MISS:
        return "NÃO RECUPEROU"
    if real_rank < reference_rank:
        return f"MELHOROU ({reference_rank}º → {real_rank}º)"
    if real_rank == reference_rank:
        return f"empatou ({real_rank}º)"
    return f"PIOROU ({reference_rank}º → {real_rank}º)"


def _print_top(label: str, top: tuple[tuple[str, float], ...]) -> None:
    rendered = ", ".join(f"{entry_id} {score:.3f}" for entry_id, score in top[:3])
    print(f"      {label:<12} {rendered}")


async def main() -> int:
    from ecosfera_ai.infrastructure.embeddings.sentence_transformer import (
        DEFAULT_MODEL_NAME,
        SentenceTransformerEmbedder,
    )

    manifest = load_manifest(MANIFEST_PATH)
    print("=" * 78)
    print("PORTÃO M6.3 — validação do embedder semântico real")
    print("=" * 78)
    print(f"corpus  : {len(manifest.entries)} entradas ({MANIFEST_PATH})")
    print(f"modelo  : {DEFAULT_MODEL_NAME}")
    print("baixando os pesos (primeira execução leva alguns minutos)...\n")

    real = SentenceTransformerEmbedder()
    print(f"modelo carregado: {real.name}, {real.dimensions} dimensões\n")

    reference_retriever = await _retriever_for(DeterministicEmbedder(), manifest)
    real_retriever = await _retriever_for(real, manifest)

    failures: list[str] = []

    print("-" * 78)
    print("CONSULTAS POR CÓDIGO DE CAUSA — piso: 1º lugar, igual ao de referência")
    print("-" * 78)
    for cause_code, acceptable, description in CAUSE_CODE_CASES:
        reference_rank, reference_hit, reference_top = await _rank_of(
            reference_retriever,
            cause_code,
            acceptable,
            category=None,
            cause_code=cause_code,
            limit=10,
        )
        real_rank, real_hit, real_top = await _rank_of(
            real_retriever,
            cause_code,
            acceptable,
            category=None,
            cause_code=cause_code,
            limit=10,
        )
        print(f"\n  {cause_code} → espera {description}")
        print(f"      aceitáveis:  {', '.join(sorted(acceptable))}")
        _print_top("referência:", reference_top)
        _print_top("real:", real_top)
        print(f"      veredito     {_verdict(reference_rank, real_rank)}")
        if real_hit and reference_hit and real_hit != reference_hit:
            print(
                f"      nota:        o modelo real preferiu {real_hit}; o léxico, {reference_hit}"
            )

        if real_rank != 1:
            first = real_top[0][0] if real_top else "nada"
            failures.append(
                f"{cause_code}: em 1º veio {first}, que não carrega a regra da consulta "
                f"({description}); o piso da consulta filtrada é o 1º lugar"
            )

    print()
    print("-" * 78)
    print("CONSULTAS EM TEXTO LIVRE — piso: recuperar; a promessa é subir de posição")
    print("-" * 78)
    for query, category, acceptable, description in FREE_TEXT_CASES:
        reference_rank, reference_hit, reference_top = await _rank_of(
            reference_retriever,
            query,
            acceptable,
            category=category,
            cause_code=None,
            limit=5,
        )
        real_rank, real_hit, real_top = await _rank_of(
            real_retriever,
            query,
            acceptable,
            category=category,
            cause_code=None,
            limit=5,
        )
        print(f"\n  {query!r} → espera {description}")
        print(f"      aceitáveis:  {', '.join(sorted(acceptable))}")
        _print_top("referência:", reference_top)
        _print_top("real:", real_top)
        print(f"      veredito     {_verdict(reference_rank, real_rank)}")
        if real_hit and reference_hit and real_hit != reference_hit:
            print(
                f"      nota:        o modelo real preferiu {real_hit}; o léxico, {reference_hit}"
            )

        if real_rank == RANK_MISS:
            failures.append(
                f"{query!r}: nenhuma das entradas que carregam a regra ({description}) "
                f"apareceu entre as 5 primeiras com o modelo real; o de referência traz "
                f"{reference_hit or 'uma delas'} em {reference_rank}º"
            )

    print()
    print("=" * 78)
    if failures:
        print("PORTÃO REPROVADO — o modelo real não sustenta o piso do de referência:")
        for failure in failures:
            print(f"  · {failure}")
        print("=" * 78)
        return 1

    print("PORTÃO APROVADO — o modelo semântico real sustenta o piso do de referência.")
    print("A lacuna declarada no ADR 0027 está fechada; registre o resultado lá.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
