"""Caso de uso: gerar explicação causal de um resultado do tick (RF-033/039).

Orquestra o motor de regras (determinístico). No Inc 6, este mesmo caso de uso
ganha uma etapa opcional de reescrita pelo LLM+RAG mantendo a cadeia rastreável
como âncora anti-alucinação (RF-034) — sem quebrar o contrato de saída.
"""
from __future__ import annotations

from ecosfera_ai.domain.feedback.causal_rules import CausalRuleEngine
from ecosfera_ai.domain.feedback.models import CausalExplanation, Observation


class ExplainCausalUseCase:
    def __init__(self, engine: CausalRuleEngine) -> None:
        self._engine = engine

    def execute(
        self, planet_id: str, observations: list[Observation]
    ) -> CausalExplanation:
        return self._engine.explain(planet_id, observations)
