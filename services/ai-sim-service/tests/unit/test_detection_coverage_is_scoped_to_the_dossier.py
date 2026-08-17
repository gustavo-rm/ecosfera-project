"""A cobertura fala do DOSSIÊ sob teste, e não do universo de tipos conhecidos.

## O defeito que este arquivo fecha

A primeira versão de `DetectionCoverage` comparava contra TODOS os tipos que o
sistema conhece. Como sempre há algum sem checagem, `is_complete` **nunca podia
ser verdadeiro** — e o relatório de avaliação imprimia, em toda execução:

    das aprovadas, com verificação COMPLETA: 0,0%

Um número que parecia achado e era artefato. Ele descrevia o SISTEMA (existem
tipos sem checagem), e não a TENTATIVA (esta geração foi verificada?), e por isso
não distinguia caso nenhum de caso nenhum. Uma métrica que só sabe dizer uma
coisa não é uma métrica pessimista — é uma constante com aparência de medida.

O recorte agora é o dossiê: os eventos que aquele planeta de fato tem.

## O que a métrica continua NÃO dizendo

Ela responde "os eventos deste planeta são verificáveis?". Não responde "poderia
ter passado uma invenção de um tipo que este planeta não tem?" — e essa segunda
pergunta segue com resposta ruim. O risco residual é do sistema, e o teste de
pontos cegos abaixo é onde ele é cobrado.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import cascade_context, spec

from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.generation.grounding import (
    checkable_event_types,
    unchecked_event_types,
    verify_grounding,
)
from ecosfera_ai.engines.ecology.events import TROPHIC_COLLAPSE, EcologyCauseCode
from ecosfera_ai.shared_kernel.events import EventEmitter

FLOOR = explain(list(branching_cascade()))
CASCADE = cascade_context()
FAITHFUL = "No ciclo 100, a queda de um meteoro atingiu o planeta."

VOCABULARY = set(
    yaml.safe_load(Path("configs/explanation_templates.yaml").read_text("utf-8"))["nouns"]
)


def _with_an_unchecked_event() -> FactualContext:
    """Um dossiê que contém um tipo que ninguém confere quanto a invenção."""
    collapse = EventEmitter(engine_id="ecology", seed=2027, tick=10, era=1).emit(
        TROPHIC_COLLAPSE, EcologyCauseCode.PREY_COLLAPSE
    )
    return FactualContext.of("planet-gap", ContextSlice.of_era(1), (collapse,))


# --- A métrica pode, de fato, chegar a 1.0 ------------------------------------


def test_a_dossier_of_fully_checkable_events_reports_complete_coverage() -> None:
    """O teste que prova que a métrica não é insatisfazível por construção.

    A cascata tem meteoro, mudança de temperatura e extinção — os três
    verificáveis depois do M6.4. Se este teste falhar, a métrica voltou a
    descrever o sistema em vez da tentativa.
    """
    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CASCADE, spec=spec())

    assert verdict.passed
    assert verdict.coverage.is_complete, (
        f"cobertura incompleta num dossiê inteiramente verificável: "
        f"{sorted(verdict.coverage.unchecked)}"
    )
    assert verdict.coverage.unchecked == frozenset()
    assert verdict.summary == "passou", "sem ressalva, porque não há o que ressalvar"


def test_a_dossier_holding_an_unchecked_type_reports_partial_coverage() -> None:
    """Contraprova: a ressalva continua aparecendo onde ela é verdadeira.

    Sem este caso, "a cobertura chega a 1.0" poderia significar "a cobertura é
    sempre 1.0", e a métrica teria trocado um valor constante por outro.
    """
    context = _with_an_unchecked_event()
    floor = explain(list(context.events))
    verdict = verify_grounding(
        "Naquele ciclo, algo mudou.", floor=floor, context=context, spec=spec()
    )

    assert verdict.passed
    assert not verdict.coverage.is_complete
    assert "TrophicCollapse" in verdict.coverage.unchecked
    assert "cobertura parcial" in verdict.summary


def test_the_coverage_names_only_types_the_dossier_actually_has() -> None:
    """O recorte é o dossiê: nada do universo de tipos entra na conta."""
    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CASCADE, spec=spec())
    present = {event.event_type for event in CASCADE.events}

    assert verdict.coverage.checked <= present
    assert verdict.coverage.unchecked <= present
    assert verdict.coverage.checked | verdict.coverage.unchecked == present


# --- E os pontos cegos declarados acompanham a realidade ----------------------


def test_the_declared_blind_spots_match_the_vocabulary() -> None:
    """A lista de pontos cegos é DERIVADA, e este teste impede que ela minta.

    A versão anterior era literal e estava errada: declarava cinco tipos quando o
    vocabulário tinha seis sem checagem. O que faltava era `SpeciesExtinct` — nem
    conferido, nem admitido como não conferido, que é a pior das duas metades.

    Uma lista literal que descreve outra lista envelhece sozinha. É a família do
    `atmosphere.oxygen` sem escritor e do filtro fantasma de `planet_id`, e a
    resposta é a mesma: derivar, e cobrar a derivação.
    """
    blind_spots = unchecked_event_types(spec(), VOCABULARY)

    assert blind_spots == VOCABULARY - checkable_event_types(spec())
    assert "SpeciesExtinct" not in blind_spots, "fechado no encerramento do M6.4"
    assert "TrophicCollapse" in blind_spots, "segue sem checagem, e declarado"


def test_every_blind_spot_is_a_real_event_type() -> None:
    """Contraprova da própria lista: um ponto cego inventado não guarda nada."""
    for event_type in unchecked_event_types(spec(), VOCABULARY):
        assert event_type in VOCABULARY


def test_the_checkable_set_covers_the_three_types_task_0_closed() -> None:
    """O que o Task 0 fechou continua fechado, e o encerramento acrescentou um."""
    checkable = checkable_event_types(spec())

    for closed_by_task_0 in ("SpeciationOccurred", "TemperatureShift", "PopulationDeclined"):
        assert closed_by_task_0 in checkable
    assert "SpeciesExtinct" in checkable, "fechado no encerramento"
    assert "MeteorImpact" in checkable, "termo concreto, desde o M6.3"
