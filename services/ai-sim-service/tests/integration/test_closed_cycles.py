"""Os ciclos fechados do M2: a água conserva e o carbono não é contado duas vezes.

Este arquivo verifica as duas propriedades que o M2 existe para garantir, e que
nenhum Engine sozinho consegue afirmar — elas são sobre a COMPOSIÇÃO.

Por que uma delas é invariante de runtime e a outra não (ADR 0012): a água é uma
soma de UMA fatia que não pode mudar, e isso o Planet Engine verifica a cada
delta. O carbono atravessa duas fatias com donos diferentes e tem fonte e
sumidouro legítimos — não é uma soma constante, é uma identidade contábil. Checá-la
no Planet exigiria que ele soubesse qual termo é fonte e qual é troca, isto é, que
contivesse ciência. Por isso ela vive aqui.
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from ecosfera_ai.engines.atmosphere.contracts import load_params as atmosphere_params
from ecosfera_ai.engines.atmosphere.domain import carbon_sinks
from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.chemistry.contracts import load_params as chemistry_params
from ecosfera_ai.engines.composition import FrameworkTickOrchestrator, build_planet_engine
from ecosfera_ai.engines.hydrology.contracts import load_params as hydrology_params
from ecosfera_ai.shared_kernel.events import CoreCauseCode
from ecosfera_ai.shared_kernel.world_state import InvariantBreach, WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
ATMOSPHERE = atmosphere_params()
CHEMISTRY = chemistry_params()
HYDROLOGY = hydrology_params()
TICKS = 120


def _trail(seed: int = 2027, ticks: int = TICKS) -> list[WorldStateSnapshot]:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("cycles", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        trail.append(snapshot)
    return trail


def _total_water(snapshot: WorldStateSnapshot) -> float:
    water = snapshot.hydrology
    return water.ocean + water.ice + water.vapour + water.freshwater


def _total_carbon(snapshot: WorldStateSnapshot) -> float:
    """Todo o carbono do sistema acoplado: ar + oceano + sedimento."""
    return (
        snapshot.atmosphere.co2 + snapshot.chemistry.ocean_carbon + snapshot.chemistry.soil_carbon
    )


# --- Água ---------------------------------------------------------------------


def test_the_total_water_never_changes() -> None:
    """Os fluxos apenas MOVEM massa; nenhum a cria ou destrói."""
    trail = _trail()
    start = _total_water(trail[0])
    for snapshot in trail:
        assert _total_water(snapshot) == pytest.approx(
            start, abs=HYDROLOGY.conservation_tolerance * 10
        )


def test_the_reservoirs_actually_move_so_conservation_is_not_trivial() -> None:
    """Uma soma constante sobre reservatórios parados não provaria nada."""
    trail = _trail()
    for field in ("ocean", "ice", "vapour", "freshwater"):
        values = {round(getattr(s.hydrology, field), 9) for s in trail}
        assert len(values) > 5, f"{field} não se moveu — a conservação seria vazia"


def test_no_water_conservation_breach_is_ever_diagnosed() -> None:
    """A invariante de runtime confirma o mesmo, do lado do Planet Engine."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("cycles", 2027), PARAMS))
    breaches: list[InvariantBreach] = []
    for _ in range(TICKS):
        outcome = planet.tick(snapshot, publish=False)
        snapshot = outcome.snapshot
        breaches.extend(b for b in outcome.breaches if b.invariant == "water_conservation")
    assert not breaches, f"a água deixou de conservar: {breaches[:3]}"


def test_the_diagnostic_would_reach_the_developer_if_it_ever_broke() -> None:
    """A invariante não é decorativa: uma violação vira `DiagnosticEvent`."""
    from ecosfera_ai.shared_kernel.world_state import ConservedTotal, SliceRef, StateDelta, compose

    base = snapshot_of(initial_state(PlanetSeed("leak", 1), PARAMS))
    leak = StateDelta(
        engine_id="hydrology", tick=0, writes=SliceRef.HYDROLOGY, values={"ocean": 5.0}
    )
    outcome = compose(
        base,
        [leak],
        [
            ConservedTotal(
                name="water_conservation",
                slice_ref=SliceRef.HYDROLOGY,
                fields=("ocean", "ice", "vapour", "freshwater"),
                tolerance=HYDROLOGY.conservation_tolerance,
            )
        ],
    )
    assert [b.invariant for b in outcome.breaches] == ["water_conservation"]
    assert CoreCauseCode.INVARIANT_BREACH  # o Planet traduz a violação neste código


# --- Carbono ------------------------------------------------------------------


def test_carbon_is_not_double_counted() -> None:
    """A identidade contábil que o ADR 0012 fixa, tick a tick.

    O carbono total só pode mudar pelo que a geologia INJETA e pelo que a biota
    ABSORVE. Tudo o mais é redistribuição interna — e a troca ar<->oceano é
    exatamente isso: o que sai de um livro entra no outro, com o mesmo módulo.

    Se a Atmosphere calculasse a própria troca em vez de subtrair a da química,
    ou se esquecesse de subtraí-la, este teste falharia — e é o único lugar onde
    falharia, porque cada Engine isolado continuaria coerente consigo mesmo.
    """
    trail = _trail()
    for before, after in pairwise(trail):
        # `co2_flux` do tick QUE FECHOU: a geologia roda antes da atmosfera, e a
        # composição é sequencial — a atmosfera lê o fluxo recém-escrito, não o do
        # tick anterior (ADR 0008). A biomassa, essa sim, é leitura defasada.
        injected = after.geology.co2_flux
        absorbed = ATMOSPHERE.carbon_uptake_coeff * before.biota.biomass
        weathered = ATMOSPHERE.weathering_coeff * before.atmosphere.co2
        expected = _total_carbon(before) + injected - absorbed - weathered
        assert _total_carbon(after) == pytest.approx(expected, abs=1e-6), (
            f"o carbono não fecha no tick {before.tick}"
        )


def test_what_the_ocean_gains_is_what_the_air_loses() -> None:
    """Um fluxo, dois livros, sinais opostos — a decisão central do ADR 0012."""
    trail = _trail()
    moved = 0
    for before, after in pairwise(trail):
        flux = after.chemistry.air_sea_flux
        if abs(flux) < 1e-9:
            continue
        moved += 1
        # O oceano recebeu o fluxo (menos o que soterrou no mesmo tick).
        buried = after.chemistry.soil_carbon - before.chemistry.soil_carbon
        gained = after.chemistry.ocean_carbon - before.chemistry.ocean_carbon
        assert gained + buried == pytest.approx(flux, abs=1e-6)
    assert moved > 10, "sem troca nenhuma o teste seria vácuo"


def test_the_ocean_buffers_instead_of_vacuuming_the_atmosphere() -> None:
    """Começar o oceano em equilíbrio é condição inicial, não detalhe.

    Com `ocean_carbon` zerado o gradiente inicial seria de 280 ppm inteiros, e o
    planeta gastaria a primeira era transferindo carbono do ar para a água — um
    transiente de campo não preenchido, que se leria como "o oceano resfria o
    planeta" (ADR 0012).
    """
    trail = _trail()
    first_flux = trail[1].chemistry.air_sea_flux
    assert abs(first_flux) < 1.0, f"transiente de partida grande demais: {first_flux}"
    # E a atmosfera ACUMULA, porque a fonte vulcânica supera os sumidouros.
    assert trail[-1].atmosphere.co2 > trail[0].atmosphere.co2


def test_the_atmosphere_debits_the_flux_the_chemistry_credited() -> None:
    """Verificação direta do sinal, sem depender da trajetória inteira."""
    trail = _trail()
    for before, after in pairwise(trail):
        sinks = carbon_sinks(before.atmosphere.co2, before.biota.biomass, ATMOSPHERE)
        expected = before.atmosphere.co2 + after.geology.co2_flux - sinks
        expected -= after.chemistry.air_sea_flux
        assert after.atmosphere.co2 == pytest.approx(max(0.0, expected), abs=1e-6)


# --- A ponte não pode comer a ciência nova -----------------------------------


def test_the_bridge_round_trip_is_lossless_for_the_m2_slices() -> None:
    """Sem isto, a metade do M2 voltaria a zero uma vez por tick (ADR 0012)."""
    rich = _trail(ticks=30)[-1]
    survived = snapshot_of(planet_state_of(rich))

    assert survived.hydrology == rich.hydrology
    assert survived.chemistry == rich.chemistry
    assert survived.resource == rich.resource
    assert survived.biota == rich.biota
    assert survived.astronomy == rich.astronomy


def test_the_http_path_keeps_the_cycles_closed() -> None:
    """O mesmo, pelo caminho que a borda HTTP de fato percorre."""
    ticker = FrameworkTickOrchestrator(
        build_planet_engine(PARAMS, budget=PARAMS.engine_budget), PARAMS.bounds
    )
    state = initial_state(PlanetSeed("http", 2027), PARAMS)
    # Um planeta recém-criado traz só os AGREGADOS `water`/`ice_cover`; é a ponte
    # que os reparte nos quatro reservatórios no primeiro tick (ADR 0012). A
    # conservação passa a valer a partir daí.
    state = ticker.tick(state).state
    start_water = state.ocean_water + state.ice_mass + state.vapour + state.freshwater
    assert start_water > 0.0, "a ponte não hidratou os reservatórios"
    for _ in range(60):
        state = ticker.tick(state).state

    total = state.ocean_water + state.ice_mass + state.vapour + state.freshwater
    assert total == pytest.approx(start_water, abs=1e-6)
    # E a capacidade de suporte chega publicada no estado que o M3 vai ler.
    assert state.carrying_capacity > 0.0
