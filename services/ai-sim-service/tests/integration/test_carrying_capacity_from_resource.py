"""A capacidade de suporte vem do Resource, e a biologia só a CONSOME.

É a fronteira do ADR 0013, reafirmada depois de a biologia mudar de dono no M3
(ADR 0016). Ela é fácil de violar por conveniência: bastaria a Evolution
recalcular a capacidade "para ficar coerente" e passariam a existir duas
definições do mesmo limite, divergindo em silêncio.

Aqui se afirma a direção da seta: ambiente → capacidade → ocupação, e nunca de
volta.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.domain import LocalConditions, population_change
from ecosfera_ai.engines.resource.contracts import READS as RESOURCE_READS
from ecosfera_ai.engines.resource.contracts import WRITES as RESOURCE_WRITES
from ecosfera_ai.shared_kernel.world_state import SliceRef
from ecosfera_ai.simulation_engine.biology.genome import Genome
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
EVOLUTION = evolution_params()


def test_only_the_resource_engine_writes_the_capacity() -> None:
    """Um dono, e é o Resource — a moldura recusaria dois no boot."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    assert planet.registry.owned_slices[SliceRef.RESOURCE] == "resource"
    assert RESOURCE_WRITES is SliceRef.RESOURCE


def test_the_capacity_is_derived_from_the_environment_not_from_life() -> None:
    """O Resource lê o ambiente físico; a biota entra só como consumo defasado."""
    from ecosfera_ai.engines.resource.contracts import LAGGED_READS as RESOURCE_LAGGED

    assert SliceRef.BIOTA not in RESOURCE_READS, (
        "o Resource passou a derivar a capacidade a partir da vida instalada: "
        "o limite viraria função da ocupação, que é circular"
    )
    assert SliceRef.BIOTA in RESOURCE_LAGGED, "o consumo é leitura defasada, e declarada"
    assert {SliceRef.CLIMATE, SliceRef.CHEMISTRY, SliceRef.HYDROLOGY} <= RESOURCE_READS


def test_the_capacity_moves_with_the_environment() -> None:
    """Contraprova viva: mudando o ambiente, a capacidade responde."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("capacity", 2027), PARAMS))
    for _ in range(120):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    baseline = snapshot.resource.carrying_capacity
    assert baseline > 0.0

    # Um planeta congelado não sustenta a mesma vida que um temperado.
    frozen = snapshot.with_slice(SliceRef.CLIMATE, replace(snapshot.climate, temperature=-40.0))
    frozen = planet.tick(frozen, publish=False).snapshot
    assert frozen.resource.carrying_capacity < baseline, (
        "congelar o planeta não reduziu a capacidade: ela não depende do clima"
    )


def test_the_capacity_is_published_on_the_planet_state() -> None:
    """A ponte carrega a capacidade — é assim que o caso de uso a recebe.

    Até o M1 o `EvolveBiologyUseCase` instanciava um subsistema só para calcular
    a capacidade. Desde o M2 ela chega publicada (ADR 0013), e o M3 depende
    disso continuar valendo.
    """
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("bridge", 2027), PARAMS))
    for _ in range(120):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    state = planet_state_of(snapshot)
    assert state.carrying_capacity == pytest.approx(snapshot.resource.carrying_capacity)


def test_the_capacity_is_the_ceiling_the_growth_reads() -> None:
    """A ocupação entra na conta da vida como LOTAÇÃO contra esse teto.

    Mesma coorte, mesma população, mesmo ambiente — só o teto muda. Se a
    capacidade não fosse o limite, o excedente seria o mesmo nos dois casos.
    """
    cohort = Genome(
        temp_optimum=20.0,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()

    def growth(capacity: float) -> float:
        return population_change(
            cohort,
            50.0,
            LocalConditions(
                temperature=20.0,
                water_available=0.6,
                energy_available=0.10,
                carrying_capacity=capacity,
                occupied=50.0,
                predation_pressure=0.0,
            ),
            EVOLUTION,
        )

    assert growth(500.0) > growth(100.0) > growth(30.0), (
        "o teto publicado não está governando o crescimento"
    )


def test_an_uninhabitable_planet_supports_no_life() -> None:
    """Capacidade zero é ocupação zero — o limite manda, sempre."""
    cohort = Genome(
        temp_optimum=20.0,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()

    change = population_change(
        cohort,
        10.0,
        LocalConditions(
            temperature=20.0,
            water_available=0.6,
            energy_available=0.10,
            carrying_capacity=0.0,
            occupied=10.0,
            predation_pressure=0.0,
        ),
        EVOLUTION,
    )
    assert change < 0.0, "sem capacidade alguma, a comunidade deveria minguar"
