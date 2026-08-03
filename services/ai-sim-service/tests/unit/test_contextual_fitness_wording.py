"""Q5 (validação Tássia): a aptidão é CONTEXTUAL, não inexistente.

Correção de VOCABULÁRIO, sem mudança de dinâmica — e não é preciosismo. Dizer
"não há aptidão neste modelo" troca uma imprecisão por outra: sugere que
sobreviver e perecer são indiferentes ao organismo, quando o que o modelo recusa
é a aptidão **ABSOLUTA** — o número único que ordenaria as espécies fora de
qualquer contexto.

A formulação correta é a que o Tutor vai herdar: a mesma coorte é apta a um
ambiente e inapta a outro, sem ter mudado em nada. É o que torna inteligível a
extinção catastrófica — uma espécie de aptidão contextual ALTA pode morrer.

Este arquivo guarda a formulação onde aptidão é discutida.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Onde a aptidão é discutida e a formulação precisa aparecer.
DISCUSSES_FITNESS = (
    Path("src/ecosfera_ai/engines/evolution/domain.py"),
    Path("src/ecosfera_ai/engines/evolution/events.py"),
)

CONTEXTUAL = ("contextual", "CONTEXTUAL")
ABSOLUTE_DENIAL = ("absoluta", "ABSOLUTA")


@pytest.mark.parametrize("path", DISCUSSES_FITNESS, ids=lambda p: p.name)
def test_the_contextual_wording_is_present(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert any(word in text for word in CONTEXTUAL), (
        f"{path.name} discute aptidão sem dizer que ela é CONTEXTUAL (Q5)"
    )


def test_the_domain_says_what_is_denied_is_absolute_fitness() -> None:
    """A negação precisa ser QUALIFICADA: nega-se a aptidão absoluta, não a aptidão."""
    text = Path("src/ecosfera_ai/engines/evolution/domain.py").read_text(encoding="utf-8")
    assert any(word in text for word in ABSOLUTE_DENIAL), (
        "o módulo nega a aptidão sem qualificar que o negado é a ABSOLUTA"
    )


def test_no_unqualified_denial_of_fitness_survives() -> None:
    """Nenhum lugar AFIRMA, sem qualificar, que aptidão não existe.

    É a formulação que o Tutor herdaria e repetiria ao aluno.

    Citar a formulação errada para REJEITÁ-LA é o oposto do defeito, e a
    documentação faz exatamente isso ("dizer 'não há aptidão' seria impreciso").
    Por isso a linha só conta como denúncia quando a frase aparece FORA de
    aspas — dentro delas, é menção, não uso.
    """
    forbidden = ("não há aptidão", "nao ha aptidao", "não existe aptidão")
    for path in Path("src/ecosfera_ai").rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            lowered = line.lower()
            unquoted = re.sub(r'"[^"]*"|«[^»]*»', "", lowered)
            for phrase in forbidden:
                assert phrase not in unquoted, (
                    f"{path}:{number} nega a aptidão sem qualificar — a aptidão é CONTEXTUAL (Q5)"
                )


def test_the_guard_would_catch_a_real_unqualified_denial() -> None:
    """Contraprova do próprio filtro: fora de aspas, a frase é pega."""
    quoted = 'dizer "não há aptidão" seria impreciso'
    plain = "aqui não há aptidão nenhuma"
    strip = lambda line: re.sub(r'"[^"]*"|«[^»]*»', "", line)  # noqa: E731

    assert "não há aptidão" not in strip(quoted), "a menção entre aspas seria acusada"
    assert "não há aptidão" in strip(plain), "o uso real escaparia do filtro"


def test_the_adrs_carry_the_wording_too() -> None:
    """A rastreabilidade: quem ler o ADR encontra a formulação corrigida."""
    adrs = list(Path("docs/adr").glob("*.md"))
    discussing = [p for p in adrs if "aptidão" in p.read_text(encoding="utf-8")]
    assert discussing, "nenhum ADR discute aptidão — a busca está errada"
    assert any("contextual" in p.read_text(encoding="utf-8").lower() for p in discussing), (
        "nenhum ADR que discute aptidão adota a formulação contextual (Q5)"
    )
