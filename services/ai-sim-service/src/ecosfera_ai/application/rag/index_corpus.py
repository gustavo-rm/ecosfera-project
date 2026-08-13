"""Pipeline de indexação: manifesto revisado por humano → vetores no índice.

Offline e idempotente. Roda fora do laço de simulação, não toca no world-state e
não conhece Engine algum — é a mesma fronteira de consumidor read-side dos
marcos anteriores, com a diferença de que aqui nem o Event Store é lido: o corpus
é material do PROJETO, não do planeta de ninguém.

## Idempotente por substituição, e por modelo

Indexar duas vezes o mesmo manifesto deixa o índice igual. A substituição é
por MODELO: reindexar com `ecosfera-deterministic-v1` não apaga o que um modelo
semântico gravou, e vice-versa. Sem isso, uma reindexação parcial deixaria
sobras de outro espaço vetorial convivendo com as novas — e a consulta
compararia espaços diferentes sem que nada acusasse.

## O manifesto manda no modelo

O nome do modelo vem do manifesto, não de quem chama. É o arquivo revisável que
declara com o que aquele corpus foi indexado, e é isso que torna uma troca de
modelo uma mudança VERSIONADA em vez de um efeito colateral de deploy.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.application.rag.corpus_index import CorpusIndex, IndexedEntry
from ecosfera_ai.domain.rag.corpus import CorpusEntry, CorpusManifest
from ecosfera_ai.domain.rag.embedding import EmbeddingModel


class EmbeddingModelMismatchError(ValueError):
    """O modelo injetado não é o que o manifesto declara.

    Falha alto em vez de indexar. Gravar vetores de um modelo sob o nome de outro
    produziria um índice em que a consulta compara espaços distintos — e o sintoma
    seria a passagem errada com um número plausível ao lado, não uma exceção.
    """


@dataclass(frozen=True, slots=True)
class IndexReport:
    """O que a indexação fez — para inspeção humana e para o log de auditoria."""

    model_name: str
    indexed: int
    by_category: dict[str, int]
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "indexed": self.indexed,
            "by_category": dict(self.by_category),
            "sources": list(self.sources),
        }


class IndexCorpusUseCase:
    """Lê o manifesto, gera os vetores e substitui a indexação daquele modelo."""

    def __init__(self, embedder: EmbeddingModel, index: CorpusIndex) -> None:
        self._embedder = embedder
        self._index = index

    async def execute(self, manifest: CorpusManifest) -> IndexReport:
        if manifest.embedding_model != self._embedder.name:
            raise EmbeddingModelMismatchError(
                f"o manifesto declara {manifest.embedding_model!r} e o indexador é "
                f"{self._embedder.name!r}; indexar assim gravaria vetores de um "
                "modelo sob o nome de outro"
            )

        texts = [_embeddable_text(entry) for entry in manifest.entries]
        vectors = self._embedder.embed(texts)
        indexed = [
            IndexedEntry(entry=entry, embedding=vector)
            for entry, vector in zip(manifest.entries, vectors, strict=True)
        ]
        await self._index.replace_all(self._embedder.name, indexed)

        by_category: dict[str, int] = {}
        for entry in manifest.entries:
            key = entry.category.value
            by_category[key] = by_category.get(key, 0) + 1

        return IndexReport(
            model_name=self._embedder.name,
            indexed=len(indexed),
            by_category=by_category,
            sources=tuple(sorted(manifest.sources)),
        )


def _embeddable_text(entry: CorpusEntry) -> str:
    """O texto que vai para o modelo: as CHAVES DE BUSCA mais a passagem.

    O tópico e os `cause_codes` entram na frente porque são as palavras pelas
    quais o consumidor de cima procura, e nem sempre elas aparecem no corpo da
    regra. Sem o tópico, uma regra sobre especiação que só diz "as duas linhagens
    compartilham um ancestral" ficaria invisível a uma consulta pelo termo.

    Os `cause_codes` foram acrescentados depois de o roteiro de fumaça mostrar o
    problema: o corpus é em português e os códigos de causa são um enum em inglês
    (`CATASTROPHIC_EVENT`), então uma consulta pelo código não casava com
    absolutamente nada e devolvia a primeira entrada por desempate. Incluí-los é
    honesto — o código É parte do que a entrada endereça, do mesmo jeito que o
    tópico —, e é o que faz `for_cause_code` funcionar também por texto livre.

    Repare no que NÃO acontece aqui: o código de causa entra como CHAVE, não como
    afirmação. Nenhuma entrada passa a dizer que o mecanismo ocorreu em planeta
    algum — quem afirma isso é o dossiê factual, e o tipo que sai do retriever
    continua incapaz de ocupar o lugar de um fato.
    """
    keys = " ".join(part for part in (entry.topic, *entry.cause_codes) if part)
    return f"{keys}. {entry.text}" if keys else entry.text


__all__ = ["EmbeddingModelMismatchError", "IndexCorpusUseCase", "IndexReport"]
