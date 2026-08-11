"""O vocabulário do consumidor e o dos Engines dizem a MESMA coisa.

O consumidor não pode importar Engine algum (Spec §2), então ele repete as
constantes do envelope que sabe ler. Duplicação envelhece — e a alternativa,
importar do Engine, trocaria a duplicação por acoplamento, que é a troca errada:
o envelope §4 é CONTRATO entre a simulação e todos os consumidores, e um contrato
existe justamente para que os dois lados mudem sozinhos.

O que torna a duplicação segura é este arquivo. Ele é TESTE, e por isso pode
importar os dois lados; o código de produção não pode. Se um Engine renomear
`SpeciesExtinct`, aqui falha com o nome do termo que divergiu — em vez de o Tutor
emudecer em silêncio sobre extinções, que é como esta classe de defeito se
manifestaria em produção: sem exceção, sem log, só uma ausência.
"""

from __future__ import annotations

from ecosfera_ai.domain.consumers import vocabulary as consumer
from ecosfera_ai.engines.ecology import events as ecology
from ecosfera_ai.engines.event import events as extraordinary
from ecosfera_ai.engines.evolution import events as evolution


def test_the_biology_event_types_match() -> None:
    assert consumer.LIFE_EMERGED == evolution.LIFE_EMERGED
    assert consumer.SPECIATION_OCCURRED == evolution.SPECIATION_OCCURRED
    assert consumer.SPECIES_EXTINCT == evolution.SPECIES_EXTINCT
    assert consumer.MASS_MORTALITY == evolution.MASS_MORTALITY


def test_the_ecology_event_types_match() -> None:
    assert consumer.TROPHIC_COLLAPSE == ecology.TROPHIC_COLLAPSE
    assert consumer.POPULATION_DECLINED == ecology.POPULATION_DECLINED


def test_the_extraordinary_event_types_match() -> None:
    assert consumer.METEOR_IMPACT == extraordinary.METEOR_IMPACT
    assert consumer.SUPERVOLCANIC_ERUPTION == extraordinary.SUPERVOLCANIC_ERUPTION
    assert consumer.ICE_AGE_ONSET == extraordinary.ICE_AGE_ONSET


def test_the_speciation_participant_roles_match() -> None:
    """Se os papéis divergirem, a leitura de ancestral comum devolve vazio.

    E vazio, aqui, não é neutro: `SpeciationFact` recusaria o evento e o dossiê
    quebraria — ruidosamente, que é o comportamento certo, mas por um motivo que
    este teste nomeia antes.
    """
    assert consumer.ANCESTOR_ROLE == evolution.ANCESTOR_ROLE
    assert consumer.LINEAGE_ROLE == evolution.LINEAGE_ROLE


def test_the_catastrophic_cause_code_matches() -> None:
    """A fronteira do ADR 0019 depende deste literal e de mais nada."""
    assert (
        str(evolution.EvolutionCauseCode.CATASTROPHIC_EVENT.value)
        == consumer.CATASTROPHIC_CAUSE_CODE
    )


def test_every_notable_transition_is_a_type_some_engine_really_emits() -> None:
    """Nenhum marcador aponta para um tipo que ninguém produz.

    É a lição do `solar_flux` do M2 — um campo sem escritor que valeu zero em
    silêncio por um marco inteiro. Um marcador sem emissor anuncia ao Tutor uma
    âncora temporal que a simulação nunca vai lhe dar.
    """
    emitted = {
        value
        for module in (evolution, ecology, extraordinary)
        for name, value in vars(module).items()
        if name.isupper() and isinstance(value, str) and name != "__doc__"
    }
    assert emitted >= consumer.NOTABLE_TRANSITIONS, (
        f"marcadores sem emissor: {consumer.NOTABLE_TRANSITIONS - emitted}"
    )


# --- A prosa do M6.1 cobre todo cause_code declarado -------------------------


def test_every_cause_code_has_a_mechanism_phrase_or_is_declared_unnarrated() -> None:
    """Nenhum `cause_code` fica sem frase POR ESQUECIMENTO.

    É a lição do `solar_flux` do M2 aplicada à prosa. Um código sem oração de
    mecanismo não estoura nada: o narrador simplesmente pula o evento, e o aluno
    lê uma era em que aquele acontecimento não existiu. O sintoma é ausência, e
    ausência não se denuncia sozinha.

    Por isso a alternativa tem de ser EXPLÍCITA: ou o código tem frase, ou está
    em `not_narrated` com a razão registrada no YAML. Um código novo que não
    esteja em nenhum dos dois reprova aqui, ao lado do nome dele.
    """
    import importlib
    import pkgutil
    from pathlib import Path

    import ecosfera_ai.engines as engines_package
    from ecosfera_ai.domain.consumers.templates import load_templates
    from ecosfera_ai.shared_kernel.events import CauseCodeEnum

    for module in pkgutil.walk_packages(engines_package.__path__, "ecosfera_ai.engines."):
        if module.name.endswith(".events"):
            importlib.import_module(module.name)

    def walk(cls: type[CauseCodeEnum]):  # type: ignore[no-untyped-def]
        for sub in cls.__subclasses__():
            yield sub
            yield from walk(sub)

    declared = {str(member.value) for subclass in walk(CauseCodeEnum) for member in subclass}
    table = load_templates(Path("configs/explanation_templates.yaml"))
    covered = set(table.mechanisms) | set(table.not_narrated)

    assert declared <= covered, (
        "cause_code sem frase e sem declaração de silêncio — o Tutor pularia o "
        f"evento sem avisar ninguém: {sorted(declared - covered)}"
    )


def test_no_mechanism_phrase_is_declared_for_a_code_that_does_not_exist() -> None:
    """O inverso: uma frase para código que ninguém declara é prosa morta.

    Ela passaria a revisão pedagógica, ocuparia espaço no arquivo e nunca
    chegaria a aluno algum — e daria a impressão de cobertura que não existe.
    """
    import importlib
    import pkgutil
    from pathlib import Path

    import ecosfera_ai.engines as engines_package
    from ecosfera_ai.domain.consumers.templates import load_templates
    from ecosfera_ai.shared_kernel.events import CauseCodeEnum

    for module in pkgutil.walk_packages(engines_package.__path__, "ecosfera_ai.engines."):
        if module.name.endswith(".events"):
            importlib.import_module(module.name)

    def walk(cls: type[CauseCodeEnum]):  # type: ignore[no-untyped-def]
        for sub in cls.__subclasses__():
            yield sub
            yield from walk(sub)

    declared = {str(member.value) for subclass in walk(CauseCodeEnum) for member in subclass}
    table = load_templates(Path("configs/explanation_templates.yaml"))

    assert set(table.mechanisms) <= declared, (
        f"frases para códigos inexistentes: {sorted(set(table.mechanisms) - declared)}"
    )
