"""A virada de chave do M1 e o que ela custa em paridade (ADR 0010/0011).

**Paridade bit-a-bit entre legado e moldura não existe mais, e isso é
proposital.** O M1 corrigiu duas coisas que mudam números:

1. o efeito estufa passou de LINEAR (`coef × CO2`) para LOGARÍTMICO
   (Myhre et al. 1998), que satura como a física real satura;
2. a geologia passou a rodar ANTES da atmosfera, eliminando a defasagem de um
   tick entre desgaseificação e estoque de carbono.

Exigir paridade seria exigir que a ciência não melhorasse. O que estes testes
garantem no lugar dela é mais forte e verificável: cada caminho é determinístico,
o novo é cientificamente defensável, o planeta continua fisicamente são, e a
troca não quebra nenhum contrato HTTP.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ecosfera_ai.config.settings import Settings
from ecosfera_ai.engines.legacy.orchestrator import (
    FrameworkTickOrchestrator,
    build_planet_engine,
    reduced_params,
)
from ecosfera_ai.simulation_engine.params import build_orchestrator, initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TICKS = 60
BASE = "/ai/api/v1/simulation"


def _framework() -> FrameworkTickOrchestrator:
    return FrameworkTickOrchestrator(
        build_planet_engine(PARAMS, budget=PARAMS.engine_budget), PARAMS.bounds
    )


def _run(ticker, seed: int, ticks: int = TICKS):
    state = initial_state(PlanetSeed("switch", seed), PARAMS)
    for _ in range(ticks):
        state = ticker.tick(state).state
    return state


def test_the_framework_is_the_default_path() -> None:
    assert Settings().engines_framework is True


def test_both_paths_are_individually_deterministic() -> None:
    """O que se exige de cada caminho é reprodutibilidade, não igualdade mútua."""
    assert _run(_framework(), 2027) == _run(_framework(), 2027)
    legacy = build_orchestrator(PARAMS)
    assert _run(legacy, 2027) == _run(build_orchestrator(PARAMS), 2027)


def test_the_two_paths_diverge_and_that_is_the_point() -> None:
    framed = _run(_framework(), 2027)
    legacy = _run(build_orchestrator(PARAMS), 2027)
    assert framed != legacy, "se batesse, o forçamento logarítmico não teria entrado em produção"


def test_the_new_path_saturates_where_the_old_one_did_not() -> None:
    """A diferença tem SENTIDO: o aquecimento POR DUPLICAÇÃO ficou constante.

    Comparar o forçamento (W/m²) com o termo antigo (°C) seria erro de grandeza —
    o que se compara aqui é o AQUECIMENTO em °C que cada modelo entrega, e como
    ele se comporta a cada duplicação sucessiva do estoque de carbono.
    """
    from ecosfera_ai.engines.atmosphere.contracts import load_params as atmo_params
    from ecosfera_ai.engines.atmosphere.domain import radiative_forcing
    from ecosfera_ai.engines.climate.contracts import load_params as climate_params

    atmo, clima = atmo_params(), climate_params()
    linear_coeff = PARAMS.climate.greenhouse_coeff

    doublings = [(280.0, 560.0), (560.0, 1120.0), (1120.0, 2240.0)]
    log_gains = [
        clima.climate_sensitivity
        * (radiative_forcing(after, atmo) - radiative_forcing(before, atmo))
        for before, after in doublings
    ]
    linear_gains = [linear_coeff * (after - before) for before, after in doublings]

    # O modelo logarítmico entrega o MESMO acréscimo a cada duplicação.
    assert log_gains[0] == pytest.approx(log_gains[1]) == pytest.approx(log_gains[2])
    # O linear DOBRA a cada duplicação — a resposta que a física não tem.
    assert linear_gains[1] == pytest.approx(2 * linear_gains[0])
    # E por isso ele diverge cada vez mais do modelo correto.
    assert linear_gains[-1] > 2 * log_gains[-1]


def test_the_new_path_keeps_the_planet_habitable() -> None:
    """A troca não podia transformar o planeta em Vênus nem em bola de neve."""
    state = _run(_framework(), 2027)
    assert -50.0 < state.temperature < 60.0
    assert state.co2 > 0.0
    assert 0.0 <= state.ice_cover <= 1.0


def test_migrated_science_is_zeroed_at_the_source_not_masked() -> None:
    """O legado reduzido não recalcula carbono nem sequestro de calor."""
    reduced = reduced_params(PARAMS)
    assert reduced.chemistry.outgassing == 0.0
    assert reduced.chemistry.weathering_coeff == 0.0
    assert reduced.chemistry.carbon_uptake_coeff == 0.0
    assert reduced.ocean.heat_uptake == 0.0
    # O ciclo da água continua intacto: só o carbono saiu.
    assert reduced.chemistry.melt_coeff == PARAMS.chemistry.melt_coeff


def test_geology_and_climate_left_the_legacy_adapter() -> None:
    from ecosfera_ai.engines.legacy.orchestrator import build_legacy_orchestrator

    remaining = build_legacy_orchestrator(PARAMS).subsystem_names
    assert "geology" not in remaining
    assert "climate" not in remaining
    # chemistry e ocean continuam no adaptador até o M2, como previsto.
    assert {"chemistry", "ocean"} <= set(remaining)


def test_the_registry_runs_engines_in_the_coupling_order() -> None:
    assert _framework().subsystem_names == (
        "geology",
        "atmosphere",
        "climate",
        "legacy_planet",
    )


def test_http_contract_is_unchanged_under_the_new_path(client: TestClient) -> None:
    """Virar a chave não pode mexer no contrato que o front já consome."""
    planet_id = client.post(f"{BASE}/planets", json={"seed": 2027}).json()["planet_id"]

    tick = client.post(f"{BASE}/planets/{planet_id}/tick")
    assert tick.status_code == 200
    body = tick.json()
    assert {"state", "delta", "explanation"} <= set(body)
    assert body["explanation"]["source"] == "rules"

    era = client.post(f"{BASE}/planets/{planet_id}/advance-era")
    assert era.status_code == 200

    replay = client.get(f"{BASE}/planets/{planet_id}/eras/1").json()
    assert replay["matches_checkpoint"] is True, "replay pela moldura tem de bater"


@pytest.mark.parametrize("seed", [1, 2027, 31337])
def test_replay_through_http_holds_for_several_seeds(client: TestClient, seed: int) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": seed}).json()["planet_id"]
    client.post(f"{BASE}/planets/{planet_id}/advance-era")
    assert client.get(f"{BASE}/planets/{planet_id}/eras/1").json()["matches_checkpoint"]


def test_replay_does_not_republish_the_event_trail(client: TestClient) -> None:
    """Reconstruir uma era é reproduzir, não reocorrer (ADR 0011).

    Sem esta guarda, cada `GET /eras/{era}` reemitia a trilha inteira daquela era
    no Event Store, e o Tutor passaria a ver a mesma erupção várias vezes.
    """
    from ecosfera_ai.interfaces.http.deps import get_event_store

    planet_id = client.post(f"{BASE}/planets", json={"seed": 2027}).json()["planet_id"]
    for _ in range(3):
        client.post(f"{BASE}/planets/{planet_id}/advance-era")

    before = len(get_event_store().events)
    client.get(f"{BASE}/planets/{planet_id}/eras/3")
    client.get(f"{BASE}/planets/{planet_id}/eras/2")

    assert len(get_event_store().events) == before
