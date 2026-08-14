"""O corpus pedagógico — o material de REGISTRO do Tutor, com proveniência.

Este corpus existe para o Tutor **soar** como um professor alinhado ao currículo,
não para ele **saber** mais ciência. A distinção decide a arquitetura inteira do
M6:

* o FATO sobre o planeta do aluno vem do Event Store (`FactualContext`, M6.0) e é
  narrado pelo piso de template (M6.1) — é inviolável;
* este corpus informa REGISTRO e LINGUAGEM: como dizer, com que palavras, em que
  ordem didática, com que vocabulário proibido.

Se o corpus disser "extinções catastróficas ocorrem" e a trilha daquele planeta
não tiver nenhuma, o Tutor não pode narrar uma. A garantia contra isso é de TIPO
e vive em `passage.py`.

## Proveniência é invariante, não convenção

Toda entrada declara de qual documento do projeto ela saiu. Não existe entrada
anônima: o modelo recusa uma, e o banco recusa outra (migration 0006, NOT NULL +
CHECK). A razão é operacional — quando alguém perguntar "por que o Tutor falou
assim com meu filho?", a resposta precisa ser um documento, não uma lembrança.

## Nada de conteúdo curricular inventado

`code_verified` reproduz a ressalva do próprio Dossiê: alguns códigos BNCC da
matriz de alinhamento estão marcados "(conferir)" — o objeto de conhecimento foi
confirmado, o número da habilidade não. Promover um "(conferir)" a verificado
fabricaria precisão que o projeto não tem, que é o defeito do `solar_flux` do M2
transplantado para a camada de conteúdo.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class CorpusCategory(StrEnum):
    """As quatro famílias de material, em ordem de prioridade (ADR 0027).

    A ordem não é decorativa: ela é a decisão de produto sobre de onde o Tutor
    tira a própria voz. Livros-texto gerais foram considerados e rejeitados como
    corpus primário — empurram o registro para a voz de um manual universitário,
    errada para a faixa etária.
    """

    VOCABULARY_RULE = "vocabulary_rule"
    VALIDATED_CORRECTION = "validated_correction"
    CURRICULUM_OBJECTIVE = "curriculum_objective"
    EXTERNAL_REFERENCE = "external_reference"


class MissingProvenanceError(ValueError):
    """Uma entrada sem origem declarada, ou sem licença quando precisa.

    Falha alto. Uma entrada anônima é pior que uma entrada ausente: ela chega ao
    aluno como as outras e ninguém consegue dizer de onde veio quando perguntarem.
    """


@dataclass(frozen=True, slots=True)
class CorpusEntry:
    """Uma passagem do corpus, antes de ser indexada.

    `cause_codes` e `topic` são CHAVES DE ROTEAMENTO — dizem "esta regra é
    relevante quando se narra tal mecanismo". Não afirmam que o mecanismo
    ocorreu no planeta de ninguém. Confundir as duas coisas é o risco central
    desta subetapa, e é por isso que o tipo que sai do retriever não é um fato.
    """

    entry_id: str
    category: CorpusCategory
    source: str
    text: str
    topic: str = ""
    cause_codes: tuple[str, ...] = ()
    bncc_codes: tuple[str, ...] = ()
    grade_band: str = ""
    # Só para `curriculum_objective`: o número da habilidade BNCC foi conferido?
    # `False` preserva o "(conferir)" do Dossiê — o objeto de conhecimento está
    # certo, o código ainda não foi validado.
    code_verified: bool | None = None
    license: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise MissingProvenanceError(
                f"a entrada {self.entry_id!r} não declara origem — o corpus do "
                "Tutor não admite material anônimo"
            )
        if not self.text.strip():
            raise MissingProvenanceError(f"a entrada {self.entry_id!r} está vazia")
        if self.category is CorpusCategory.EXTERNAL_REFERENCE and not self.license.strip():
            raise MissingProvenanceError(
                f"a entrada externa {self.entry_id!r} não declara licença; na dúvida "
                "sobre a procedência de um material, ele fica de fora (ADR 0027)"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "category": self.category.value,
            "source": self.source,
            "text": self.text,
            "topic": self.topic,
            "cause_codes": list(self.cause_codes),
            "bncc_codes": list(self.bncc_codes),
            "grade_band": self.grade_band,
            "code_verified": self.code_verified,
            "license": self.license,
        }


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    """O manifesto inteiro, com o modelo de embedding que o indexou.

    O modelo fica aqui, e não só no banco, porque trocá-lo muda o significado de
    toda similaridade já gravada. Uma troca silenciosa faria o Tutor recuperar
    outra coisa sem que nada acusasse.
    """

    version: int
    embedding_model: str
    entries: tuple[CorpusEntry, ...] = ()

    def of_category(self, category: CorpusCategory) -> tuple[CorpusEntry, ...]:
        return tuple(entry for entry in self.entries if entry.category is category)

    @property
    def sources(self) -> frozenset[str]:
        return frozenset(entry.source for entry in self.entries)


def _tuple_of(raw: Mapping[str, Any], key: str) -> tuple[str, ...]:
    return tuple(str(item) for item in (raw.get(key) or ()))


def load_manifest(path: Path) -> CorpusManifest:
    """Lê o manifesto versionado. Uma entrada malformada derruba a carga inteira.

    Deliberado: um corpus parcialmente carregado é pior que nenhum, porque o
    Tutor passaria a recuperar de um conjunto que ninguém revisou — e a revisão
    humana é exatamente o que este arquivo existe para permitir.
    """
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries: list[CorpusEntry] = []
    seen: set[str] = set()
    for item in raw.get("entries", []):
        entry_id = str(item["id"])
        if entry_id in seen:
            raise MissingProvenanceError(f"a entrada {entry_id!r} aparece duas vezes no manifesto")
        seen.add(entry_id)
        entries.append(
            CorpusEntry(
                entry_id=entry_id,
                category=CorpusCategory(str(item["category"])),
                source=str(item.get("source", "")),
                text=" ".join(str(item.get("text", "")).split()),
                topic=str(item.get("topic", "")),
                cause_codes=_tuple_of(item, "cause_codes"),
                bncc_codes=_tuple_of(item, "bncc_codes"),
                grade_band=str(item.get("grade_band", "")),
                code_verified=item.get("code_verified"),
                license=str(item.get("license", "")),
            )
        )
    return CorpusManifest(
        version=int(raw.get("version", 1)),
        embedding_model=str(raw["embedding_model"]),
        entries=tuple(entries),
    )


__all__ = [
    "CorpusCategory",
    "CorpusEntry",
    "CorpusManifest",
    "MissingProvenanceError",
    "load_manifest",
]
