"""BIO-002 (parte pré-M6) — toda especiação diz o que a DISPAROU.

A mecânica não muda nesta fase: a especiação continua sendo divergência acima de
um limiar, num único passo. O que se acrescenta é a causa, porque o limiar é a
RÉGUA e não o motivo — e uma especiação narrada sem motivo vira, na boca de quem
narra, "a espécie precisava de uma nova", que é a teleologia do BIO-005.

A mecânica GRADUAL (divergência mantida ao longo de gerações) é dívida declarada
pós-M6: Fase 2 do Plano de Evolução, registrada no ADR 0023.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import community_genome, speciation_event, speciation_snapshot

from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.domain import LocalConditions
from ecosfera_ai.engines.evolution.events import (
    CAUSES_WITHOUT_EMITTER,
    SPECIATION_CAUSES,
    EvolutionCauseCode,
)
from ecosfera_ai.engines.evolution.service import _speciation_cause

EVOLUTION = evolution_params()


def _conditions(
    *, temperature: float = 20.0, capacity: float = 500.0, occupied: float = 40.0
) -> LocalConditions:
    return LocalConditions(
        temperature=temperature,
        water_available=0.9,
        energy_available=0.2,
        carrying_capacity=capacity,
        occupied=occupied,
        predation_pressure=0.0,
    )


# --- O evento carrega uma causa, e ela é do vocabulário de especiação ----------


def test_every_speciation_event_carries_a_cause_code() -> None:
    event = speciation_event()
    assert isinstance(event.cause_code, EvolutionCauseCode)
    assert event.cause_code in SPECIATION_CAUSES, (
        f"a especiação saiu com {event.cause_code!r}, que não é causa de especiação"
    )


def test_the_superseded_code_is_no_longer_emitted() -> None:
    """`GENETIC_DIVERGENCE` nomeava o critério, não a causa (BIO-002)."""
    assert speciation_event().cause_code is not EvolutionCauseCode.GENETIC_DIVERGENCE
    assert EvolutionCauseCode.GENETIC_DIVERGENCE not in SPECIATION_CAUSES


def test_the_superseded_code_survives_for_old_trails() -> None:
    """Removê-la tornaria ilegível toda trilha gravada antes da Fase 0.

    `event_from_dict` recusa um `cause_code` fora de todo vocabulário — é a
    recusa correta, e é por isso que o membro fica.
    """
    from ecosfera_ai.shared_kernel.events import event_from_dict, event_to_dict

    old = dict(event_to_dict(speciation_event()))
    old["cause_code"] = EvolutionCauseCode.GENETIC_DIVERGENCE.value
    assert event_from_dict(old).cause_code is EvolutionCauseCode.GENETIC_DIVERGENCE


# --- A causa é DIAGNOSTICADA, não constante -----------------------------------


def test_a_change_of_trophic_class_is_a_divergent_niche() -> None:
    """A linhagem passou a explorar outro recurso: a divisão é de nicho."""
    ancestor = community_genome(trophic_level=1.0)
    divergent = community_genome(trophic_level=2.0)
    assert (
        _speciation_cause(ancestor, divergent, _conditions(), EVOLUTION)
        is EvolutionCauseCode.DIVERGENT_NICHE
    )


def test_an_environment_outside_the_ancestral_window_is_environmental_pressure() -> None:
    ancestor = community_genome(temp_optimum=20.0, temp_tolerance=3.0)
    divergent = community_genome(temp_optimum=21.0, temp_tolerance=3.0)
    assert (
        _speciation_cause(ancestor, divergent, _conditions(temperature=60.0), EVOLUTION)
        is EvolutionCauseCode.ENVIRONMENTAL_PRESSURE
    )


def test_a_full_environmental_budget_is_environmental_pressure_too() -> None:
    """O orçamento ambiental estourado é pressão direcional como o calor é."""
    ancestor = community_genome()
    divergent = community_genome(size=1.2)
    conditions = _conditions(capacity=10.0, occupied=500.0)
    assert (
        _speciation_cause(ancestor, divergent, conditions, EVOLUTION)
        is EvolutionCauseCode.ENVIRONMENTAL_PRESSURE
    )


def test_accumulated_difference_without_a_trigger_is_reproductive_isolation() -> None:
    """Sem nicho novo e sem pressão, o que resta é o nome próprio do fenômeno."""
    ancestor = community_genome()
    divergent = community_genome(size=1.1)
    assert (
        _speciation_cause(ancestor, divergent, _conditions(), EVOLUTION)
        is EvolutionCauseCode.REPRODUCTIVE_ISOLATION
    )


def test_the_same_lineages_in_different_worlds_get_different_causes() -> None:
    """Contraprova de que a causa não é constante: só o ambiente mudou."""
    ancestor = community_genome(temp_tolerance=3.0)
    divergent = community_genome(temp_tolerance=3.0, size=1.1)
    calm = _speciation_cause(ancestor, divergent, _conditions(), EVOLUTION)
    hot = _speciation_cause(ancestor, divergent, _conditions(temperature=60.0), EVOLUTION)
    assert calm is not hot


@pytest.mark.parametrize("temperature", [18.0, 30.0, 34.0])
def test_a_real_event_carries_the_diagnosed_cause_in_any_of_these_worlds(
    temperature: float,
) -> None:
    """Ponta a ponta: o que o diagnóstico devolve é o que sai no envelope.

    Nenhum destes mundos está no ótimo do residente (26 °C): com o ambiente
    exatamente no ótimo não há gradiente, a seleção rejeita toda variante e não
    existe especiação a observar — o que é ciência correta, e não limitação do
    cenário.
    """
    world = speciation_snapshot(community_genome(temp_optimum=26.0), temperature=temperature)
    assert speciation_event(world).cause_code in SPECIATION_CAUSES


# --- Nenhum código de causa fica anunciado e sem emissor -----------------------


def test_every_declared_cause_either_has_an_emitter_or_is_registered_as_missing() -> None:
    """Um código sem emissor é a família de furo silencioso do `solar_flux`.

    O vocabulário anuncia uma explicação que a simulação nunca produz, e nada
    estoura. O registro `CAUSES_WITHOUT_EMITTER` torna o buraco ruidoso: quem
    acrescentar um código sem emitir precisa dizê-lo por escrito.
    """
    emitted = Path("src/ecosfera_ai/engines/evolution/service.py").read_text(encoding="utf-8")
    for code in EvolutionCauseCode:
        has_emitter = f"EvolutionCauseCode.{code.name}" in emitted
        assert has_emitter or code in CAUSES_WITHOUT_EMITTER, (
            f"{code.name} é declarada, ninguém a emite e ela não está registrada "
            "em CAUSES_WITHOUT_EMITTER"
        )
        assert not (has_emitter and code in CAUSES_WITHOUT_EMITTER), (
            f"{code.name} está registrada como sem emissor, mas o Engine a emite"
        )


def test_the_geographic_barrier_is_declared_and_its_absence_is_explained() -> None:
    """Causa canônica da especiação alopátrica, sem geografia que a produza."""
    assert EvolutionCauseCode.GEOGRAPHIC_BARRIER in CAUSES_WITHOUT_EMITTER
    text = Path("src/ecosfera_ai/engines/evolution/events.py").read_text(encoding="utf-8")
    assert "geografia" in text.lower(), (
        "o código está declarado sem emissor e sem a razão escrita ao lado"
    )


def test_the_gradual_mechanic_is_declared_as_post_m6_debt() -> None:
    """A Fase 0 anexa a causa e NÃO torna a especiação gradual — por decisão."""
    text = Path("src/ecosfera_ai/engines/evolution/domain.py").read_text(encoding="utf-8")
    assert "pós-M6" in text or "pos-M6" in text, (
        "a mecânica gradual da especiação seguiu sem ser declarada como dívida"
    )
