"""Guards the bounded-context/layer package scaffolding (see docs/adr/)."""

import importlib


def test_bounded_contexts_are_importable() -> None:
    for module in [
        "ai_sim_service",
        "ai_sim_service.shared",
        "ai_sim_service.interface",
        "ai_sim_service.simulation",
        "ai_sim_service.simulation.domain",
        "ai_sim_service.simulation.application",
        "ai_sim_service.simulation.infrastructure",
        "ai_sim_service.tutor",
        "ai_sim_service.tutor.agents",
        "ai_sim_service.tutor.prompts",
        "ai_sim_service.tutor.pipelines",
        "ai_sim_service.tutor.pipelines.ingestion",
        "ai_sim_service.tutor.pipelines.retrieval",
        "ai_sim_service.tutor.embeddings",
        "ai_sim_service.tutor.memory",
        "ai_sim_service.tutor.evaluation",
        "ai_sim_service.tutor.infrastructure",
    ]:
        importlib.import_module(module)
