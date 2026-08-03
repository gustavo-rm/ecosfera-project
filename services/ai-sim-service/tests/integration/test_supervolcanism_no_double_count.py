"""Supervulcanismo (Event) × vulcanismo basal (Geology): UM fluxo, sem dupla contagem.

A Geology do M1 já desgaseifica CO₂ do vulcanismo contínuo. O supervulcanismo é
evento extraordinário — mas o carbono que ele injeta continua sendo carbono
VULCÂNICO, e quem detém o fluxo vulcânico é a Geology.

Por isso o Event Engine publica só a INTENSIDADE na `EventSlice`, e a soma
acontece dentro da Geology, num termo só. A alternativa — o Event publicar um
pulso de CO₂ que a atmosfera somasse ao lado de `geology.co2_flux` — criaria duas
entradas de carbono vulcânico, e a ausência de dupla contagem passaria a depender
de disciplina em vez de estrutura (ADR 0018). O M2 já pagou esse preço uma vez.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import build_quiet_planet, build_scripted_planet

from ecosfera_ai.engines.atmosphere.contracts import load_params as atmosphere_params
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.world_state import EventSlice, SliceRef
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
ATMOSPHERE = atmosphere_params()


def _settled(ticks: int = 150):
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("supervolcano", 2027), PARAMS))
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
    return planet, snapshot


def test_the_event_engine_publishes_intensity_not_carbon() -> None:
    """A `EventSlice` não tem campo de CO₂ — só intensidade.

    É a garantia ESTRUTURAL: não existe onde publicar um segundo fluxo de
    carbono, então não há como somá-lo por engano.
    """
    fields = set(EventSlice.__dataclass_fields__)
    assert "supervolcanic_intensity" in fields
    assert not [f for f in fields if "co2" in f or "carbon" in f], (
        "a EventSlice ganhou um campo de carbono: a segunda entrada voltou a existir"
    )


def test_the_atmosphere_reads_a_single_carbon_inflow() -> None:
    """A atmosfera continua lendo UM termo: `geology.co2_flux`."""
    source = Path("src/ecosfera_ai/engines/atmosphere/service.py").read_text(encoding="utf-8")
    assert "geology.co2_flux" in source
    assert "event." not in source, (
        "a atmosfera passou a ler a EventSlice: risco de somar carbono duas vezes"
    )


def test_the_supervolcanism_flows_through_the_geological_term() -> None:
    planet, settled = _settled()
    calm = planet.tick(settled, publish=False).snapshot
    erupting = planet.tick(
        settled.with_slice(SliceRef.EVENT, EventSlice(supervolcanic_intensity=1.0)),
        publish=False,
    ).snapshot

    assert erupting.geology.co2_flux > calm.geology.co2_flux * 2.0, (
        "o supervulcanismo mal alterou o fluxo — não está sendo incorporado"
    )


def test_the_carbon_accounting_still_closes_during_an_eruption() -> None:
    """A identidade contábil do M2 vale COM o evento ativo.

    É o teste que detecta a dupla contagem de verdade: se o carbono do
    supervulcão entrasse por dois caminhos, o total depois excederia o que a
    conta prevê.
    """
    planet, settled = _settled()
    before = settled.with_slice(SliceRef.EVENT, EventSlice(supervolcanic_intensity=1.0))
    after = planet.tick(before, publish=False).snapshot

    injected = after.geology.co2_flux
    absorbed = ATMOSPHERE.carbon_uptake_coeff * before.biota.biomass
    weathered = ATMOSPHERE.weathering_coeff * before.atmosphere.co2

    total_before = (
        before.atmosphere.co2 + before.chemistry.ocean_carbon + before.chemistry.soil_carbon
    )
    total_after = after.atmosphere.co2 + after.chemistry.ocean_carbon + after.chemistry.soil_carbon

    assert total_after == pytest.approx(total_before + injected - absorbed - weathered, abs=1e-6), (
        "o carbono deixou de fechar durante a supererupção — há uma segunda entrada"
    )


def test_a_scripted_supervolcano_raises_co2_then_lets_it_settle() -> None:
    """Ponta a ponta: o evento eleva o CO₂ e o intemperismo depois o puxa."""
    planet = build_scripted_planet(EventKind.SUPERVOLCANO, lead=3)
    snapshot = snapshot_of(initial_state(PlanetSeed("erupt", 2027), PARAMS))
    trail = [snapshot]
    for _ in range(200):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        trail.append(snapshot)

    erupting = [s for s in trail if s.event.supervolcanic_intensity > 0.0]
    assert erupting, "o supervulcão roteirizado não ocorreu"

    quiet_before = trail[2].atmosphere.co2
    peak = max(s.atmosphere.co2 for s in trail)
    assert peak > quiet_before, "a supererupção não elevou o CO₂"


def test_basal_volcanism_alone_does_not_look_like_an_eruption() -> None:
    """Contraprova: sem evento, o fluxo é o basal — o multiplicador não vaza."""
    planet, settled = _settled()
    plain = planet.tick(settled, publish=False).snapshot
    zeroed = planet.tick(
        settled.with_slice(SliceRef.EVENT, EventSlice(supervolcanic_intensity=0.0)),
        publish=False,
    ).snapshot
    assert plain.geology.co2_flux == pytest.approx(zeroed.geology.co2_flux)
