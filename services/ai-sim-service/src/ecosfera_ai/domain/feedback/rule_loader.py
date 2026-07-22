"""Carrega regras causais do YAML versionado (dados, não código)."""
from __future__ import annotations

from pathlib import Path

import yaml

from ecosfera_ai.domain.feedback.causal_rules import CausalRule, CausalRuleEngine


def load_rules(path: Path) -> list[CausalRule]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules = []
    for item in raw.get("rules", []):
        rules.append(
            CausalRule(
                rule_id=item["id"],
                cause=item["cause"],
                effect=item["effect"],
                same_direction=item.get("same_direction", True),
                template=item["template"],
            )
        )
    return rules


def build_engine(path: Path, max_depth: int = 3) -> CausalRuleEngine:
    return CausalRuleEngine(load_rules(path), max_depth=max_depth)
