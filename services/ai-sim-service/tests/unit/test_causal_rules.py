from __future__ import annotations

from pathlib import Path

from ecosfera_ai.domain.feedback.models import Direction, Observation
from ecosfera_ai.domain.feedback.rule_loader import build_engine

ENGINE = build_engine(Path("configs/causal_rules.yaml"))


def test_co2_up_raises_temperature_deterministically() -> None:
    r1 = ENGINE.explain("p1", [Observation("co2", 0.3)])
    r2 = ENGINE.explain("p1", [Observation("co2", 0.3)])
    # determinismo (RF-023): mesma entrada, mesma saída
    assert r1.summary == r2.summary
    effects = {(s.effect, s.direction) for s in r1.chain}
    assert ("temperature", Direction.UP) in effects


def test_cascade_propagates_to_albedo() -> None:
    r = ENGINE.explain("p1", [Observation("co2", 0.5)])
    ids = {s.rule_id for s in r.chain}
    # CO2↑ -> temp↑ -> gelo↓ -> albedo↓  (cascata)
    assert {"R-CO2-TEMP", "R-TEMP-ICE", "R-ICE-ALBEDO"}.issubset(ids)


def test_inverse_rule_flips_direction() -> None:
    r = ENGINE.explain("p1", [Observation("temperature", 0.2)])
    ice = next(s for s in r.chain if s.effect == "ice_cover")
    assert ice.direction is Direction.DOWN  # temp↑ => gelo↓


def test_no_observation_yields_safe_summary() -> None:
    r = ENGINE.explain("p1", [])
    assert r.chain == []
    assert "Nenhuma" in r.summary
