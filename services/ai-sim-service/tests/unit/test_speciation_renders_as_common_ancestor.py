"""Em PROSA, especiação é ancestral comum — e "A deu origem a B" é inexprimível.

O M6.0 travou a garantia no TIPO: `SpeciationFact` tem um ancestral e duas
linhagens irmãs e recusa qualquer outra forma. Este arquivo fecha o último trecho
do caminho, que é onde a garantia poderia se perder mesmo com o tipo correto —
alguém escreve um template que diz "a linhagem ancestral se tornou a linhagem
nova" e a estrutura, impecável, chega ao aluno traduzida errado.

A defesa aqui não é uma lista de frases proibidas (embora ela exista). É
ESTRUTURAL: o template de especiação não recebe linhagem alguma como slot. Não
há onde encaixar um sujeito e um objeto de ancestralidade, então a frase A→B não
tem como ser escrita nem por descuido — e os três identificadores continuam
disponíveis no `Grounding`, para quem audita.
"""

from __future__ import annotations

import yaml
from tests.support import speciation_event
from tests.support_explanation import TEMPLATES_PATH, context_of, explain, renderer, templates

from ecosfera_ai.domain.consumers.explanation import Register

# As formulações proibidas ao consumidor (BIO-001) — as mesmas que a Fase 0
# declarou para as regras causais. Repetidas aqui como ALVO do teste, não como
# um segundo vocabulário: a guarda que vale para os dois arquivos de prosa é
# `test_no_teleological_language`, estendida no M6.1.
FORBIDDEN_ANCESTRY = (
    "deu origem",
    "deram origem",
    "originou a espécie",
    "gerou a espécie",
    "descende da espécie",
    "virou uma nova espécie",
    "se tornou a linhagem",
    "a versão antiga",
)


def _speciation_fact() -> object:
    explanation = explain([speciation_event()], era=speciation_event().occurred_at.era)
    return explanation.facts[0]


def test_the_speciation_is_narrated_at_all() -> None:
    """Antes da Fase 0 a especiação era observável e INARRÁVEL — nada disparava."""
    fact = _speciation_fact()
    assert fact.template_id == "T-SPECIATION-COMMON-ANCESTOR"  # type: ignore[attr-defined]


def test_the_sentence_speaks_of_a_common_ancestor_and_two_lineages() -> None:
    text = _speciation_fact().text.lower()  # type: ignore[attr-defined]
    assert "ancestral comum" in text
    assert "duas linhagens" in text
    assert "dividiu" in text, "a especiação foi narrada sem a divisão que a define"


def test_the_sentence_denies_that_one_lineage_is_the_old_version_of_the_other() -> None:
    """A negação explícita é o que impede o aluno de reconstruir a escada sozinho."""
    text = _speciation_fact().text.lower()  # type: ignore[attr-defined]
    assert "irmãs" in text
    assert "nenhuma das duas é a versão antiga da outra" in text


def test_no_sentence_ever_says_one_species_produced_another() -> None:
    text = _speciation_fact().text.lower()  # type: ignore[attr-defined]
    for phrase in FORBIDDEN_ANCESTRY:
        if phrase == "a versão antiga":
            continue  # aparece na NEGAÇÃO, que é o oposto do defeito
        assert phrase not in text, f"a explicação afirma ancestralidade A→B: {phrase!r}"


def test_no_template_in_the_whole_file_asserts_a_to_b_ancestry() -> None:
    """A proibição vale para o arquivo inteiro, não só para a frase da especiação.

    Espelha `test_no_causal_rule_template_asserts_a_to_b_ancestry` da Fase 0,
    agora sobre o arquivo de prosa do M6.1.
    """
    raw = yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))
    prose = [str(entry["text"]) for entry in raw["templates"]]
    prose += [str(text) for text in (raw.get("mechanisms") or {}).values()]

    for text in prose:
        lowered = text.lower()
        for phrase in FORBIDDEN_ANCESTRY:
            if phrase == "a versão antiga" and "nenhuma das duas é a versão antiga" in lowered:
                continue
            assert phrase not in lowered, f"{text!r} afirma que uma espécie gerou outra"


# --- A garantia ESTRUTURAL, e não apenas a redação ---------------------------


def test_the_template_has_no_slot_for_a_lineage_at_all() -> None:
    """A defesa que não depende de quem escreve a frase.

    Sem slot de linhagem não existe "{a} deu origem a {b}" possível: a frase A→B
    precisaria de dois sujeitos nomeados, e o template não tem onde recebê-los.
    Uma lista de frases proibidas protege contra o que se lembrou de proibir;
    isto protege contra o que não se lembrou.
    """
    template = templates().get("T-SPECIATION-COMMON-ANCESTOR", Register.STANDARD)
    for forbidden_slot in ("{ancestor}", "{lineage_a}", "{lineage_b}", "{lineages}"):
        assert forbidden_slot not in template.text


def test_the_three_identities_still_reach_the_audit_trail() -> None:
    """Não nomeá-las na prosa não é perdê-las: o `Grounding` as guarda.

    Um UUID no meio da frase não ensina nada ao aluno; o lugar dele é a auditoria.
    """
    fact = _speciation_fact()
    assert "ancestor" in fact.grounding.fields  # type: ignore[attr-defined]
    assert "lineages" in fact.grounding.fields  # type: ignore[attr-defined]


def test_the_structural_guarantee_of_the_dossier_still_holds_underneath() -> None:
    """A prosa é o último elo; o fato por baixo continua com a forma da divisão."""
    context = context_of([speciation_event()], era=speciation_event().occurred_at.era)
    fact = context.speciations[0]
    assert len(fact.lineages) == 2
    assert fact.ancestor not in fact.lineages


def test_the_cause_of_the_split_reaches_the_sentence() -> None:
    """Uma especiação sem causa vira, na boca de quem narra, especiação por acaso."""
    text = _speciation_fact().text.lower()  # type: ignore[attr-defined]
    assert "porque" in text
    mechanisms = set(templates().mechanisms.values())
    assert any(mechanism.lower() in text for mechanism in mechanisms)


def test_adaptation_is_never_narrated_as_speciation() -> None:
    """PED-003: a distinção que impede reduzir evolução a adaptação.

    A frase de adaptação tem de NEGAR explicitamente que houve linhagem nova —
    sem isso o aluno lê "os traços mudaram" e conclui que nasceu uma espécie.
    """
    from ecosfera_ai.engines.evolution.events import TRAIT_SHIFT, EvolutionCauseCode
    from ecosfera_ai.shared_kernel.events import EventEmitter

    shift = EventEmitter(engine_id="evolution", seed=2027, tick=300, era=1).emit(
        TRAIT_SHIFT,
        EvolutionCauseCode.DIRECTIONAL_SELECTION,
        cause_detail={"before": 288.0, "after": 290.0},
    )
    text = explain([shift]).facts[0].text.lower()

    assert "adaptação" in text
    assert "frequência" in text
    assert "uma só" in text
    assert "não é o surgimento de uma linhagem nova" in text


def test_the_simple_register_keeps_the_common_ancestor() -> None:
    explanation = renderer().render(
        context_of([speciation_event()], era=speciation_event().occurred_at.era),
        Register.SIMPLE,
    )
    text = explanation.facts[0].text.lower()

    assert explanation.facts[0].register is Register.SIMPLE
    assert "ancestral comum" in text
    assert "nenhuma virou a outra" in text
    for phrase in FORBIDDEN_ANCESTRY:
        if phrase == "a versão antiga":
            continue
        assert phrase not in text
