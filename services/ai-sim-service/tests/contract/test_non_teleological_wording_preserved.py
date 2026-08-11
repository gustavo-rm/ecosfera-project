"""A prosa do M6.1 obedece ao vocabulário da Fase 0 — pela guarda dela, não por uma nova.

O requisito não é "o M6.1 também é anti-teleológico". É que exista **um só**
vocabulário. Se o M6.1 trouxesse a própria lista negra, as duas cópias
divergiriam — e a que envelhecesse seria justamente aquela que alguém
consultaria ao escrever a frase seguinte, porque estaria ao lado do template que
está editando.

Por isso este arquivo não redefine nada. Ele IMPORTA `test_no_teleological_language`
e afirma duas coisas:

  1. a guarda da Fase 0 realmente ALCANÇA o arquivo de prosa novo (senão a
     cobertura seria uma suposição — a mesma família do `planet_id` fantasma);
  2. as três regras de linguagem (BIO-005, PED-003, BIO-001) aparecem na prosa
     que o M6.1 acrescentou, e não apenas nas regras causais herdadas.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from tests.unit.test_no_teleological_language import (
    EXPLANATIONS,
    TELEOLOGICAL,
    _templates,
    _without_quoted,
)

RULES = Path("configs/causal_rules.yaml")


def _explanation_prose() -> list[str]:
    raw = yaml.safe_load(EXPLANATIONS.read_text(encoding="utf-8")) or {}
    prose = [str(entry["text"]) for entry in raw.get("templates", [])]
    prose += [str(text) for text in (raw.get("mechanisms") or {}).values()]
    prose += [str(text) for text in (raw.get("nouns") or {}).values()]
    return prose


# --- 1. A guarda da Fase 0 alcança a prosa nova ------------------------------


def test_the_phase_zero_guard_actually_reads_the_new_prose_file() -> None:
    """Cobertura AFIRMADA, não suposta: a lista de templates inclui os do M6.1."""
    collected = set(_templates())
    for text in _explanation_prose():
        assert text in collected, (
            f"a guarda anti-teleológica não vê {text!r} — o arquivo de prosa do "
            "M6.1 ficou fora dela, e a proteção seria só aparente"
        )


def test_the_guard_still_reads_the_original_rules_file() -> None:
    """E não trocou um arquivo pelo outro ao ganhar o segundo."""
    raw = yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    collected = set(_templates())
    for rule in raw["rules"]:
        assert str(rule["template"]) in collected


def test_there_is_exactly_one_blacklist_in_the_codebase() -> None:
    """Uma lista negra duplicada é uma lista negra que vai divergir."""
    from tests.unit import test_no_teleological_language as guard

    assert guard.TELEOLOGICAL is TELEOLOGICAL
    assert len(TELEOLOGICAL) >= 20, "a lista encolheu — alguém a substituiu por outra"


# --- 2. As três regras aparecem na prosa NOVA --------------------------------


def test_no_new_template_attributes_intention_to_evolution() -> None:
    """BIO-005 aplicado ao que o M6.1 acrescentou, frase a frase."""
    for text in _explanation_prose():
        lowered = _without_quoted(text.lower())
        for phrase in TELEOLOGICAL:
            assert phrase not in lowered, (
                f"a prosa do M6.1 atribui intenção à evolução: {text!r} contém {phrase!r}"
            )


def test_the_new_prose_distinguishes_adaptation_from_speciation() -> None:
    """PED-003 na prosa do M6.1, e não só nas regras causais herdadas."""
    prose = " ".join(_explanation_prose()).lower()

    assert "frequência dos traços" in prose, (
        "a adaptação é narrada sem dizer que o que muda é a FREQUÊNCIA dos traços"
    )
    assert "não é o surgimento de uma linhagem nova" in prose, (
        "a narração da adaptação não NEGA que ela seja especiação"
    )
    assert "se dividiu em duas linhagens" in prose, (
        "a especiação é narrada sem a divisão que a define"
    )


def test_the_new_prose_speaks_of_a_common_ancestor() -> None:
    """BIO-001 — e a negação explícita da escada de progresso."""
    prose = " ".join(_explanation_prose()).lower()

    assert "ancestral comum" in prose
    assert "irmãs" in prose
    assert "nenhuma das duas é a versão antiga da outra" in prose


def test_the_new_prose_keeps_fitness_contextual() -> None:
    """Q5: nega-se a aptidão ABSOLUTA, não a aptidão.

    A frase da extinção ecológica tem de dizer que a MESMA comunidade poderia ter
    seguido adiante em outro ambiente, sem mudar nada nela. Sem isso a aptidão
    volta a parecer propriedade do organismo, e não da relação com o ambiente.
    """
    prose = " ".join(_explanation_prose()).lower()

    assert "em outro ambiente" in prose
    assert "sem mudar nada nela" in prose
    for absolute in ("era inferior", "mais evoluída", "menos evoluída", "não servia"):
        assert absolute not in prose


def test_the_catastrophic_prose_does_not_blame_adaptation() -> None:
    """ADR 0019 na prosa: a catástrofe não seleciona, e a frase diz isso."""
    prose = " ".join(_explanation_prose()).lower()

    assert "por mais bem adaptada" in prose
    assert "não escolhe quem sobrevive" in prose


# --- Contraprova do próprio filtro -------------------------------------------


def test_the_shared_guard_would_catch_a_teleological_template() -> None:
    """Sem contraprova, "nenhuma frase é teleológica" poderia significar nada."""
    offender = "a comunidade evoluiu para tolerar o calor"
    assert any(phrase in _without_quoted(offender) for phrase in TELEOLOGICAL)
