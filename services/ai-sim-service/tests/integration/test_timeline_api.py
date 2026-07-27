"""Fluxo HTTP da linha do tempo: criar -> avançar era -> listar -> reconstruir."""

from __future__ import annotations

from fastapi.testclient import TestClient

BASE = "/ai/api/v1/simulation"


def test_advance_era_then_rebuild_it_from_the_timeline(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 2026}).json()["planet_id"]

    advanced = client.post(f"{BASE}/planets/{planet_id}/advance-era")
    assert advanced.status_code == 200
    era = advanced.json()
    assert era["era"] == 1
    assert era["start_tick"] == 0
    assert era["end_tick"] > 0
    assert era["state"]["tick"] == era["end_tick"]

    # A linha do tempo lista a gênese (era 0) e a era recém-fechada.
    timeline = client.get(f"{BASE}/planets/{planet_id}/timeline")
    assert timeline.status_code == 200
    eras = timeline.json()["eras"]
    assert [e["era"] for e in eras] == [0, 1]

    # RF-016/023: reconstruir a era 1 tem de devolver EXATAMENTE o estado gravado.
    rebuilt = client.get(f"{BASE}/planets/{planet_id}/eras/1")
    assert rebuilt.status_code == 200
    body = rebuilt.json()
    assert body["matches_checkpoint"] is True
    assert body["state"] == era["state"]


def test_consecutive_eras_are_numbered_and_persisted(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 7}).json()["planet_id"]
    first = client.post(f"{BASE}/planets/{planet_id}/advance-era").json()
    second = client.post(f"{BASE}/planets/{planet_id}/advance-era").json()

    assert (first["era"], second["era"]) == (1, 2)
    # As eras são contíguas: a seguinte começa onde a anterior terminou.
    assert second["start_tick"] == first["end_tick"]

    eras = client.get(f"{BASE}/planets/{planet_id}/timeline").json()["eras"]
    assert [e["era"] for e in eras] == [0, 1, 2]
    assert client.get(f"{BASE}/planets/{planet_id}/eras/2").json()["matches_checkpoint"] is True


def test_genesis_era_is_reconstructible(client: TestClient) -> None:
    created = client.post(f"{BASE}/planets", json={"seed": 3}).json()
    rebuilt = client.get(f"{BASE}/planets/{created['planet_id']}/eras/0")
    assert rebuilt.status_code == 200
    assert rebuilt.json()["state"] == created


def test_advance_era_on_unknown_planet_returns_problem_404(client: TestClient) -> None:
    resp = client.post(f"{BASE}/planets/does-not-exist/advance-era")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_unknown_era_returns_problem_404(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 1}).json()["planet_id"]
    resp = client.get(f"{BASE}/planets/{planet_id}/eras/99")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_timeline_of_unknown_planet_is_empty(client: TestClient) -> None:
    resp = client.get(f"{BASE}/planets/nobody/timeline")
    assert resp.status_code == 200
    assert resp.json()["eras"] == []
