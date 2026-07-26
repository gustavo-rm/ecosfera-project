"""Contrato do tick: novo estado + cadeia causal do motor de regras existente."""

from __future__ import annotations

from fastapi.testclient import TestClient

BASE = "/ai/api/v1/simulation"


def test_tick_response_includes_state_and_grounded_causal_chain(client: TestClient) -> None:
    created = client.post(f"{BASE}/planets", json={"seed": 123})
    planet_id = created.json()["planet_id"]

    resp = client.post(f"{BASE}/planets/{planet_id}/tick")
    assert resp.status_code == 200
    body = resp.json()

    # novo estado presente e avançado
    assert body["state"]["planet_id"] == planet_id
    assert body["state"]["tick"] == 1
    assert set(body["state"]) >= {
        "temperature",
        "co2",
        "ice_cover",
        "water",
        "biomass",
        "energy",
    }

    # delta agregado presente
    assert set(body["delta"]) >= {"temperature", "co2", "ice_cover"}

    # cadeia causal do motor de regras — mesmo contrato de /ai/explain (ADR 0002)
    explanation = body["explanation"]
    assert explanation["source"] == "rules"
    assert explanation["grounded"] is True
    assert explanation["planet_id"] == planet_id
    assert len(explanation["chain"]) >= 1
    first = explanation["chain"][0]
    assert {"cause", "effect", "direction", "rule_id", "explanation"} <= set(first)
