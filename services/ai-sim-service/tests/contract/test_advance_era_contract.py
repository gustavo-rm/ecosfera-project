"""Contrato de advance-era: resumo da era + cadeia causal do motor de regras."""

from __future__ import annotations

from fastapi.testclient import TestClient

BASE = "/ai/api/v1/simulation"


def test_advance_era_response_includes_summary_and_grounded_chain(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 314}).json()["planet_id"]

    resp = client.post(f"{BASE}/planets/{planet_id}/advance-era")
    assert resp.status_code == 200
    body = resp.json()

    # Resumo da era
    assert {"era", "start_tick", "end_tick", "state", "delta", "events", "explanation"} <= set(body)
    assert body["era"] == 1
    assert body["end_tick"] > body["start_tick"]

    # Estado final da era, com as variáveis dos subsistemas estendidos
    assert set(body["state"]) >= {
        "temperature",
        "co2",
        "ice_cover",
        "water",
        "biomass",
        "energy",
        "solar_flux",
        "relief",
        "volcanism",
        "salinity",
        "ocean_circulation",
    }
    assert set(body["delta"]) >= {"temperature", "co2", "volcanism", "salinity"}

    # Cadeia causal — mesmo contrato de /ai/explain e do tick (ADR 0002)
    explanation = body["explanation"]
    assert explanation["source"] == "rules"
    assert explanation["grounded"] is True
    assert explanation["planet_id"] == planet_id
    assert len(explanation["chain"]) >= 1
    step = explanation["chain"][0]
    assert {"cause", "effect", "direction", "rule_id", "explanation"} <= set(step)


def test_era_events_follow_the_event_log_schema(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 2718}).json()["planet_id"]
    body = client.post(f"{BASE}/planets/{planet_id}/advance-era").json()

    # A vida surge no início da trajetória: a era 1 registra o marco.
    assert body["events"], "esperado ao menos um marco na primeira era"
    for event in body["events"]:
        assert {"tick", "event_type", "payload"} <= set(event)
        assert body["start_tick"] < event["tick"] <= body["end_tick"]
    assert any(e["event_type"] == "life_emerged" for e in body["events"])


def test_timeline_contract_lists_era_metadata(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 99}).json()["planet_id"]
    client.post(f"{BASE}/planets/{planet_id}/advance-era")

    body = client.get(f"{BASE}/planets/{planet_id}/timeline").json()
    assert body["planet_id"] == planet_id
    for era in body["eras"]:
        assert {"era", "start_tick", "end_tick", "event_count"} <= set(era)
