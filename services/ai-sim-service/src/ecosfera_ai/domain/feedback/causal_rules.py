"""Motor de regras causais determinístico (MVP — sem LLM).

Implementa a "recomendação de consultor" do Dossiê PD&I §2.1: o feedback causal
por regras ('CO2↑ → temperatura↑') precisa existir já no MVP para validar a
hipótese pedagógica central H2 (aprender por causa-efeito). As regras são DADOS
versionados (configs/causal_rules.yaml), não código — permitem revisão pedagógica
sem redeploy e preparam a ancoragem por RAG do Inc 6.
"""
from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.domain.feedback.models import (
    CausalExplanation,
    CausalStep,
    Direction,
    Observation,
)


@dataclass(frozen=True, slots=True)
class CausalRule:
    """Regra determinística: (cause, direction_in) -> (effect, direction_out)."""

    rule_id: str
    cause: str
    effect: str
    same_direction: bool  # True: causa↑ => efeito↑ ; False: causa↑ => efeito↓
    template: str  # texto apropriado à idade, com {cause} {effect}

    def applies_to(self, obs: Observation) -> bool:
        return obs.variable == self.cause

    def project(self, obs: Observation) -> CausalStep:
        effect_dir = (
            obs.direction
            if self.same_direction
            else (Direction.DOWN if obs.direction is Direction.UP else Direction.UP)
        )
        text = self.template.format(cause=self.cause, effect=self.effect)
        return CausalStep(
            cause=self.cause,
            effect=self.effect,
            direction=effect_dir,
            rule_id=self.rule_id,
            explanation=text,
        )


class CausalRuleEngine:
    """Encadeia regras a partir das observações do tick, produzindo a cadeia causal.

    Determinístico e testável (RF-023): mesma entrada => mesma saída. Faz busca em
    largura limitada por `max_depth` para evitar ciclos (feedbacks gelo-albedo/estufa
    são intencionalmente truncados no MVP; o motor climático real vive no
    simulation_engine).
    """

    def __init__(self, rules: list[CausalRule], max_depth: int = 3) -> None:
        self._by_cause: dict[str, list[CausalRule]] = {}
        for r in rules:
            self._by_cause.setdefault(r.cause, []).append(r)
        self._max_depth = max_depth

    def explain(self, planet_id: str, observations: list[Observation]) -> CausalExplanation:
        chain: list[CausalStep] = []
        seen: set[str] = set()
        frontier = list(observations)
        depth = 0
        while frontier and depth < self._max_depth:
            next_frontier: list[Observation] = []
            for obs in frontier:
                for rule in self._by_cause.get(obs.variable, []):
                    if rule.rule_id in seen:
                        continue
                    step = rule.project(obs)
                    chain.append(step)
                    seen.add(rule.rule_id)
                    # o efeito vira nova causa (propagação em cascata)
                    signed = 1.0 if step.direction is Direction.UP else -1.0
                    next_frontier.append(Observation(variable=step.effect, delta=signed))
            frontier = next_frontier
            depth += 1

        summary = self._summarize(chain)
        return CausalExplanation(
            planet_id=planet_id,
            summary=summary,
            chain=chain,
            grounded=True,
            source="rules",
        )

    @staticmethod
    def _summarize(chain: list[CausalStep]) -> str:
        if not chain:
            return "Nenhuma mudança relevante foi detectada neste período."
        parts = [s.explanation for s in chain]
        return " ".join(parts)
