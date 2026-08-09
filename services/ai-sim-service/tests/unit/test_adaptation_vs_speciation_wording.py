"""PED-003 — ADAPTAÇÃO não é ESPECIAÇÃO, e o sistema distingue as duas.

O risco pedagógico é reduzir evolução a adaptação: o aluno passa a achar que
evoluir é "ficar melhor no que já se é", e a especiação vira mágica ou vira
sinônimo de adaptação. As duas definições que o vocabulário precisa sustentar:

  ADAPTAÇÃO  — mudança na FREQUÊNCIA dos traços numa POPULAÇÃO ao longo do
               tempo. Continua havendo UMA linhagem.
  ESPECIAÇÃO — surgimento de uma NOVA LINHAGEM a partir de um ancestral comum.
               Onde havia uma, passam a existir duas.

Adaptação acumulada pode LEVAR à especiação; não É especiação.

Este arquivo guarda a distinção onde ela precisa estar: nas regras causais (o
que o aluno ouve hoje) e na documentação dos `cause_code` (o que o Tutor do M6
vai herdar).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

RULES = Path("configs/causal_rules.yaml")
EVENTS = Path("src/ecosfera_ai/engines/evolution/events.py")
DOMAIN = Path("src/ecosfera_ai/engines/evolution/domain.py")


def _rules() -> list[dict[str, Any]]:
    raw: dict[str, Any] = yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    return [dict(rule) for rule in raw.get("rules", [])]


def _rule(rule_id: str) -> dict[str, Any]:
    found = [rule for rule in _rules() if rule["id"] == rule_id]
    assert found, f"a regra {rule_id} sumiu do arquivo versionado"
    return found[0]


# --- A distinção nas regras causais (o que o aluno ouve) ----------------------


def test_adaptation_is_narrated_as_a_change_of_trait_frequency() -> None:
    template = str(_rule("R-TRAIT-ADAPTATION")["template"]).lower()
    assert "adaptação" in template
    assert "frequência" in template, (
        "a adaptação é narrada sem dizer que o que muda é a FREQUÊNCIA dos "
        "traços — sem isso ela vira 'o indivíduo se ajustou'"
    )
    assert "uma só" in template or "uma linhagem" in template, (
        "a narração da adaptação não diz que a linhagem continua sendo uma"
    )


def test_the_adaptation_rule_says_it_is_not_a_new_lineage() -> None:
    """A negação explícita é o que separa os dois fenômenos para o aluno."""
    template = str(_rule("R-TRAIT-ADAPTATION")["template"]).lower()
    assert "não é o surgimento de uma linhagem nova" in template


def test_speciation_is_narrated_as_a_split_from_a_common_ancestor() -> None:
    template = str(_rule("R-SPECIATION-COMMON-ANCESTOR")["template"]).lower()
    assert "ancestral comum" in template
    assert "duas linhagens" in template
    assert "dividiu" in template, "a especiação é narrada sem a divisão que a define"


def test_the_two_rules_are_reachable_from_the_events_that_produce_them() -> None:
    """Uma regra que nenhuma observação alcança é prosa que ninguém ouve.

    A especiação vira observação de `species_richness`; a mudança de traço vira
    observação de `mean_temp_optimum`. As regras têm de partir DESSAS variáveis.
    """
    observations = yaml.safe_load(
        Path("configs/event_observations.yaml").read_text(encoding="utf-8")
    )
    variables = {str(entry["variable"]) for entry in observations["mappings"]}

    assert _rule("R-SPECIATION-COMMON-ANCESTOR")["cause"] in variables
    assert _rule("R-TRAIT-ADAPTATION")["cause"] in variables


def test_no_rule_calls_adaptation_a_new_species() -> None:
    """A confusão que o requisito nomeia, na direção em que ela costuma ocorrer."""
    for rule in _rules():
        template = str(rule["template"]).lower()
        if "adaptação" in template:
            assert "espécie nova" not in template, (
                f"{rule['id']} descreve adaptação como surgimento de espécie"
            )


# --- A distinção onde o Tutor vai buscá-la ------------------------------------


def test_the_cause_code_vocabulary_defines_both_terms() -> None:
    """`TraitShift` é adaptação; `SpeciationOccurred` é especiação."""
    text = EVENTS.read_text(encoding="utf-8")
    assert "ADAPTAÇÃO" in text and "ESPECIAÇÃO" in text
    assert "frequência" in text.lower(), (
        "a documentação dos cause_code define adaptação sem falar em frequência"
    )
    assert "TraitShift" in text and "SpeciationOccurred" in text, (
        "a distinção é declarada sem ser ancorada nos eventos que a materializam"
    )


def test_the_domain_module_carries_the_distinction_too() -> None:
    """Onde a mutação e o limiar vivem é onde alguém confundiria os dois."""
    text = DOMAIN.read_text(encoding="utf-8")
    assert "ADAPTAÇÃO" in text and "ESPECIAÇÃO" in text
    assert "PED-003" in text


def test_adaptation_is_not_presented_as_a_step_toward_speciation_by_necessity() -> None:
    """Acumular adaptação PODE levar à especiação; não leva por obrigação."""
    text = EVENTS.read_text(encoding="utf-8")
    assert "pode LEVAR à especiação" in text
