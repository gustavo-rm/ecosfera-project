"""Montagem do motor para os testes — um lugar só, e não um por arquivo.

Antes do M2 os testes chamavam `build_orchestrator(params)`, a fábrica do
`TickOrchestrator` monolítico. Ele foi removido junto com o adaptador legado
(ADR 0014), e o motor passou a ser sempre o mesmo: os oito Engines pelo Planet
Engine.

Centralizar aqui não é conveniência: enquanto cada teste montava o próprio
orquestrador, mudar a composição exigia tocar em quinze arquivos, e um deles
inevitavelmente ficaria para trás montando um motor que a produção não usa mais.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.engines.composition import FrameworkTickOrchestrator, build_planet_engine
from ecosfera_ai.shared_kernel.observability import ObservabilitySink
from ecosfera_ai.simulation_engine.params import SimulationParams, load_params

PARAMS_PATH = Path("configs/simulation_params.yaml")


def test_params() -> SimulationParams:
    """Os parâmetros versionados de produção — testar outros testaria outra coisa."""
    return load_params(PARAMS_PATH)


def build_orchestrator(
    params: SimulationParams, *, sink: ObservabilitySink | None = None
) -> FrameworkTickOrchestrator:
    """O motor de produção: oito Engines na ordem canônica (ADR 0012/0013)."""
    planet = build_planet_engine(params, budget=params.engine_budget, sink=sink)
    return FrameworkTickOrchestrator(planet, params.bounds)
