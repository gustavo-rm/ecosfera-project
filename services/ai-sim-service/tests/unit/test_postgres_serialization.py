"""Serialização do estado em JSONB do adaptador Postgres (sem precisar de banco).

O round-trip do `PlanetState` é a parte do adaptador mais sensível à evolução do
schema — o estado ganha campos a cada incremento. Estes testes rodam sem Docker,
complementando os de integração com Testcontainers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy", reason="extra `infra` não instalado")

from ecosfera_ai.infrastructure.persistence.postgres_planet_repo import (
    state_from_json,
    state_to_json,
)
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
STATE = initial_state(PlanetSeed("p", 42), PARAMS)


def test_state_survives_a_json_round_trip_exactly() -> None:
    assert state_from_json(state_to_json(STATE)) == STATE


def test_round_trip_preserves_the_extended_subsystem_fields() -> None:
    rebuilt = state_from_json(state_to_json(STATE))
    assert rebuilt.solar_flux == STATE.solar_flux
    assert rebuilt.orbital_x == STATE.orbital_x
    assert rebuilt.salinity == STATE.salinity
    assert rebuilt.ocean_circulation == STATE.ocean_circulation


def test_reading_accepts_a_dict_as_well_as_a_json_string() -> None:
    # asyncpg pode devolver jsonb já desserializado; ambos os formatos valem.
    assert state_from_json(json.loads(state_to_json(STATE))) == STATE


def test_unknown_keys_are_ignored_and_missing_ones_use_defaults() -> None:
    payload = json.loads(state_to_json(STATE))
    payload["campo_de_uma_versao_futura"] = 123
    del payload["salinity"]  # campo com default na dataclass

    rebuilt = state_from_json(json.dumps(payload))
    assert rebuilt.co2 == STATE.co2
    assert rebuilt.salinity == 0.0  # default, sem quebrar a leitura
