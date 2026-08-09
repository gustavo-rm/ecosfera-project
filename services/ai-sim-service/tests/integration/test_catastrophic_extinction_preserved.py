"""BIO-006 — a distinção catastrófica × ecológica sobreviveu à Fase 0.

Este arquivo NÃO reimplementa a distinção: ela é do M4 e está afirmada em
`test_extinction_cause_taxonomy`, `test_catastrophic_extinction_is_fitness_independent`
e `test_tutor_explains_catastrophic_vs_ecological`. O que ele faz é guardar a
distinção contra o que a Fase 0 mexeu — o vocabulário de `cause_code` e as regras
causais versionadas.

Os dois modos de a Fase 0 ter quebrado o M4 sem nada estourar:

  * um `cause_code` novo de especiação sendo diagnosticado numa extinção,
    devolvendo à morte uma causa que não é de morte;
  * a subida de versão de `causal_rules.yaml` derrubando as regras da catástrofe,
    fazendo o aluno voltar a ouvir "não se adaptou" depois de um meteoro.

Nos dois casos a suíte do M4 continuaria verde por caminhos diferentes. Aqui é
onde eles falham.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from tests.support import TRAITS, community_genome
from tests.support import test_params as _production_params

from ecosfera_ai.application.feedback.explain_from_events import load_translation
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.events import (
    SPECIATION_CAUSES,
    EvolutionCauseCode,
)
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    BiotaSlice,
    ClimateSlice,
    EcologySlice,
    EventSlice,
    ResourceSlice,
    SliceRef,
    WorldStateSnapshot,
)

EVOLUTION = evolution_params()
PARAMS = _production_params()
TRANSLATION = load_translation(Path("configs/event_observations.yaml"))
RULES = build_engine(Path("configs/causal_rules.yaml"))

ECOLOGICAL = frozenset(
    {
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        EvolutionCauseCode.RESOURCE_SCARCITY,
        EvolutionCauseCode.PREDATION_PRESSURE,
    }
)


def _dying_world(*, catastrophe: float, temperature: float = 20.0) -> WorldStateSnapshot:
    """Comunidade no piso, num ambiente ECOLOGICAMENTE letal (orçamento zero).

    O ambiente hostil é o que torna o par de testes honesto: os dois mundos são
    o MESMO, e a única diferença entre eles é o meteoro. Num mundo benigno a
    comunidade sobreviveria sem a catástrofe, e o teste da causa ecológica não
    teria extinção alguma para classificar — mediria a ausência do evento em vez
    da atribuição dele.
    """
    genome = community_genome()
    return WorldStateSnapshot(
        planet_id="bio-006",
        seed=2027,
        tick=11,
        era=0,
        climate=ClimateSlice(temperature=temperature),
        resource=ResourceSlice(
            water_available=0.9,
            nutrients_available=1.0,
            energy_available=0.2,
            carrying_capacity=0.0,
        ),
        biota=BiotaSlice(
            biomass=EVOLUTION.extinction_population * 1.05,
            species_richness=1.0,
            **{f"mean_{n}": float(getattr(genome, n)) for n in TRAITS},
        ),
        ecology=EcologySlice(),
        event=EventSlice(catastrophic_mortality=catastrophe),
    )


def _extinction(*, catastrophe: float, temperature: float = 20.0) -> DomainEvent:
    snapshot = _dying_world(catastrophe=catastrophe, temperature=temperature)
    engine = EvolutionEngine()
    result = engine.tick(
        TickContext(
            snapshot=snapshot,
            rng=rng_for(snapshot.seed, engine.engine_id, snapshot.tick),
            tick=snapshot.tick,
            era=snapshot.era,
            budget=PARAMS.engine_budget,
            caused_by={
                SliceRef.EVENT: ("evt-meteor",),
                SliceRef.CLIMATE: ("evt-temperature",),
            },
        )
    )
    extinct = [e for e in result.events if e.event_type == "SpeciesExtinct"]
    assert extinct, "a comunidade no piso não se extinguiu — o cenário deixou de valer"
    return extinct[0]


def _rule_ids() -> set[str]:
    raw: dict[str, Any] = yaml.safe_load(
        Path("configs/causal_rules.yaml").read_text(encoding="utf-8")
    )
    return {str(rule["id"]) for rule in raw["rules"]}


# --- As duas famílias continuam existindo e continuam separadas ---------------


def test_the_catastrophic_code_survived_the_envelope_change() -> None:
    assert EvolutionCauseCode.CATASTROPHIC_EVENT not in ECOLOGICAL
    assert set(EvolutionCauseCode) >= ECOLOGICAL


def test_the_new_speciation_causes_are_not_causes_of_death() -> None:
    """Especiação e extinção são fenômenos distintos; os vocabulários não se cruzam."""
    assert not (SPECIATION_CAUSES & ECOLOGICAL)
    assert EvolutionCauseCode.CATASTROPHIC_EVENT not in SPECIATION_CAUSES

    for catastrophe in (0.0, 0.9):
        cause = _extinction(catastrophe=catastrophe).cause_code
        assert cause not in SPECIATION_CAUSES, (
            f"a extinção foi atribuída a {cause}, que é causa de ESPECIAÇÃO"
        )


# --- A atribuição no motor continua correta ----------------------------------


def test_a_catastrophe_is_still_attributed_to_the_catastrophe() -> None:
    assert _extinction(catastrophe=0.9).cause_code is EvolutionCauseCode.CATASTROPHIC_EVENT


def test_without_a_catastrophe_the_same_world_still_gives_an_ecological_cause() -> None:
    """A contraprova: sem meteoro, a mesma comunidade morre de causa ecológica.

    E, com ele, a catástrofe GANHA da pressão ecológica que corria junto — a
    precedência do ADR 0019, que impede culpar o traço por uma morte de fora.
    """
    assert _extinction(catastrophe=0.0).cause_code in ECOLOGICAL
    assert _extinction(catastrophe=0.9).cause_code not in ECOLOGICAL


def test_the_catastrophic_chain_still_points_at_the_event_not_at_the_climate() -> None:
    """Encadear ao clima faria o Tutor narrar a morte como intolerância térmica."""
    assert _extinction(catastrophe=0.9).causation_id == "evt-meteor"
    assert _extinction(catastrophe=0.0).causation_id == "evt-temperature"


# --- A explicação continua tratando a catástrofe como ACASO -------------------


def test_the_catastrophe_rules_survived_the_version_bump() -> None:
    """A subida 4 → 5 acrescentou regras; derrubar as do M4 seria regressão muda."""
    assert {"R-CATASTROPHE-EXTINCTION", "R-CATASTROPHE-BIOMASS"} <= _rule_ids()


def test_the_student_still_hears_chance_and_not_failure() -> None:
    event = _extinction(catastrophe=0.9)
    observations = TRANSLATION.observations([event])
    assert observations, "a extinção catastrófica deixou de virar observação"
    assert observations[0].variable == "catastrophic_loss"

    text = " ".join(
        step.explanation for step in RULES.explain("bio-006", observations).chain
    ).lower()
    assert "evento extremo" in text, f"a explicação não nomeia o acaso: {text!r}"
    assert "por mais bem adaptada" in text, (
        "a explicação omite que a adaptação não teria salvado a espécie"
    )
    assert "não por falha dela" in text


def test_an_ecological_extinction_is_still_narrated_ecologically() -> None:
    """Uniformizar as duas em QUALQUER direção é o defeito."""
    observations = TRANSLATION.observations([_extinction(catastrophe=0.0)])
    assert observations[0].variable != "catastrophic_loss"
    text = " ".join(
        step.explanation for step in RULES.explain("bio-006", observations).chain
    ).lower()
    assert "evento extremo" not in text
