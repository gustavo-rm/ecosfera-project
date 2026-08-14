"""Nenhum conteúdo curricular foi inventado — cada objetivo rastreia a uma citação.

A tentação desta subetapa é preencher o corpus. Um corpus maior parece melhor, e
inventar um objetivo BNCC plausível é fácil: a estrutura é conhecida, o código
tem formato regular, e ninguém percebe até um professor conferir.

Seria o defeito do `solar_flux` do M2 transplantado para o conteúdo — algo que
parece verificado, não é, e por isso não se denuncia sozinho. Aqui a defesa é
dupla: todo objetivo cita a seção do Dossiê de onde saiu, e a ressalva
"(conferir)" do próprio Dossiê é preservada em `code_verified`.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.support_rag import manifest

from ecosfera_ai.domain.rag.corpus import CorpusCategory

MANIFEST = manifest()
OBJECTIVES = MANIFEST.of_category(CorpusCategory.CURRICULUM_OBJECTIVE)
DOSSIE = Path(__file__).resolve().parents[4] / "docs/dossie/ECOSFERA_Dossie_PDI_v3.md"
# Formato dos códigos BNCC 2018: EF<ano><área><nº> ou EM13<área><nº>.
BNCC_CODE = re.compile(r"^(EF\d{2}[A-Z]{2}\d{2}|EM13[A-Z]{3}\d{3})$")


def test_there_are_curriculum_objectives_to_check() -> None:
    assert OBJECTIVES


def test_every_objective_cites_the_dossier_section_it_came_from() -> None:
    for entry in OBJECTIVES:
        assert "ECOSFERA_Dossie_PDI_v3.md" in entry.source, (
            f"{entry.entry_id} não cita a seção do Dossiê de onde saiu"
        )
        assert "§" in entry.source, f"{entry.entry_id} cita o documento sem a seção"


def test_every_bncc_code_actually_appears_in_the_dossier() -> None:
    """A verificação que impede o código plausível-porém-inventado.

    Não basta o código ter o FORMATO certo: ele tem de estar escrito na matriz de
    alinhamento do Dossiê. Um `EF09CI99` bem formado passaria por qualquer regex e
    seria pura invenção.
    """
    text = DOSSIE.read_text(encoding="utf-8")
    for entry in OBJECTIVES:
        for code in entry.bncc_codes:
            assert code in text, (
                f"{entry.entry_id} cita {code}, que não aparece no Dossiê — "
                "código curricular não se inventa"
            )


def test_every_bncc_code_has_the_shape_of_a_real_one() -> None:
    for entry in OBJECTIVES:
        for code in entry.bncc_codes:
            assert BNCC_CODE.match(code), f"{entry.entry_id} traz {code!r}, fora do formato BNCC"


def test_every_objective_declares_whether_its_code_was_verified() -> None:
    """`code_verified` é obrigatório no currículo: a ressalva não pode ser omitida."""
    for entry in OBJECTIVES:
        assert entry.code_verified is not None, (
            f"{entry.entry_id} não diz se o código foi conferido"
        )


def _caveat_applies_to(source: str, code: str) -> bool:
    """A ressalva "(conferir)" vale para AQUELE código, e não para a entrada toda.

    A distinção importa e quase se perdeu aqui: a entrada do efeito estufa cita
    dois códigos — um confirmado no texto do Dossiê e outro marcado "(conferir)" —
    e indexa apenas o confirmado. Uma varredura ingênua por "conferir" na origem
    inteira acusaria a entrada certa. O que se procura é a ressalva COLADA ao
    código, que é como o Dossiê a escreve e como a origem a reproduz.
    """
    position = source.find(code)
    if position < 0:
        return False
    return "(conferir)" in source[position : position + 40]


def test_no_indexed_code_marked_conferir_is_claimed_as_verified() -> None:
    """O coração deste arquivo: promover um "(conferir)" a verificado fabrica precisão.

    O Dossiê marca alguns códigos como pendentes de validação do número exato.
    Uma entrada que INDEXE um desses tem de sair com `code_verified: false`.
    """
    for entry in OBJECTIVES:
        pending = [code for code in entry.bncc_codes if _caveat_applies_to(entry.source, code)]
        if pending:
            assert entry.code_verified is False, (
                f"{entry.entry_id} indexa {pending}, marcado '(conferir)' no Dossiê, "
                "e mesmo assim se declara verificado"
            )


def test_the_caveat_detector_is_not_vacuous() -> None:
    """Contraprova: o detector encontra a ressalva colada e ignora a distante."""
    assert _caveat_applies_to("§3.4 (EF09CI09 *(conferir)*)", "EF09CI09")
    assert not _caveat_applies_to(
        "§3.4 (EF07CI13 citado no texto; EF07CI12 marcado '(conferir)')", "EF07CI13"
    )


def test_the_unverified_objective_says_so_in_its_own_text() -> None:
    """Quem ler a passagem sabe da pendência — não só quem ler o metadado."""
    pending = [entry for entry in OBJECTIVES if entry.code_verified is False]
    assert pending, "nenhuma entrada preserva a ressalva do Dossiê — ela se perdeu"
    for entry in pending:
        assert "conferência" in entry.text or "conferir" in entry.text.lower()


def test_no_objective_invents_a_grade_band() -> None:
    allowed = ("Fundamental II", "Ensino Médio", "Técnica")
    for entry in OBJECTIVES:
        assert any(band in entry.grade_band for band in allowed), (
            f"{entry.entry_id} declara a faixa {entry.grade_band!r}, que não é trilha do projeto"
        )


def test_non_curriculum_entries_do_not_claim_bncc_codes() -> None:
    """Uma regra de vocabulário com código BNCC seria currículo disfarçado."""
    for entry in MANIFEST.entries:
        if entry.category is not CorpusCategory.CURRICULUM_OBJECTIVE:
            assert not entry.bncc_codes, f"{entry.entry_id} não é currículo e cita código BNCC"
