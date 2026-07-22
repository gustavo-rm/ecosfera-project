from __future__ import annotations

from fastapi.testclient import TestClient


def test_explain_endpoint_contract(client: TestClient) -> None:
    payload = {"planet_id": "p1", "observations": [{"variable": "co2", "delta": 0.4}]}
    resp = client.post("/ai/api/v1/ai/explain", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["planet_id"] == "p1"
    assert body["source"] == "rules"
    assert body["grounded"] is True
    assert any(step["effect"] == "temperature" for step in body["chain"])


def test_telemetry_without_consent_returns_403(client: TestClient) -> None:
    payload = {
        "student_id": "s1", "planet_id": "p1",
        "action": "intervene", "payload": {}, "consent": False,
    }
    resp = client.post("/ai/api/v1/assessment/events", json=payload)
    assert resp.status_code == 403
    assert resp.headers["content-type"].startswith("application/problem+json")
