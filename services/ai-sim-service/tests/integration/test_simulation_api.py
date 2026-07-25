"""Fluxo HTTP da simulação: criar planeta -> tick -> persistência -> 404."""

from __future__ import annotations

from fastapi.testclient import TestClient

BASE = "/ai/api/v1/simulation"


def test_create_tick_and_persist(client: TestClient) -> None:
    created = client.post(f"{BASE}/planets", json={"seed": 42})
    assert created.status_code == 201
    planet = created.json()
    planet_id = planet["planet_id"]
    assert planet["tick"] == 0
    assert planet["seed"] == 42

    ticked = client.post(f"{BASE}/planets/{planet_id}/tick")
    assert ticked.status_code == 200
    new_state = ticked.json()["state"]
    assert new_state["tick"] == 1
    # a simulação produziu efeito: o estado mudou
    assert new_state != planet

    # persistência append-only: o GET reflete o último checkpoint
    fetched = client.get(f"{BASE}/planets/{planet_id}")
    assert fetched.status_code == 200
    assert fetched.json()["tick"] == 1


def test_explicit_planet_id_is_honored(client: TestClient) -> None:
    created = client.post(f"{BASE}/planets", json={"seed": 1, "planet_id": "gaia-test"})
    assert created.status_code == 201
    assert created.json()["planet_id"] == "gaia-test"


def test_tick_unknown_planet_returns_problem_404(client: TestClient) -> None:
    resp = client.post(f"{BASE}/planets/does-not-exist/tick")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_get_unknown_planet_returns_404(client: TestClient) -> None:
    resp = client.get(f"{BASE}/planets/nope")
    assert resp.status_code == 404


def test_negative_seed_is_rejected(client: TestClient) -> None:
    resp = client.post(f"{BASE}/planets", json={"seed": -1})
    assert resp.status_code == 422
