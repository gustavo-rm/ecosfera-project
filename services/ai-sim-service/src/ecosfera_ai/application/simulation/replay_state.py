"""Caso de uso: reconstruir o estado de uma era passada (RF-016/023).

Rebobinar a simulação é reexecutar o motor a partir do checkpoint da era anterior,
reaplicando os eventos registrados. Como o motor é determinístico por semente, a
reconstrução tem de bater EXATAMENTE com o estado gravado na época — e este caso
de uso verifica isso explicitamente (`matches_checkpoint`), transformando o
determinismo (RF-023) numa garantia observável em produção, não só nos testes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.evolve_biology import EvolveBiologyUseCase
from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.ticker import Ticker
from ecosfera_ai.simulation_engine.timeline import replay


class EraNotFoundError(Exception):
    """Era inexistente na linha do tempo do planeta (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class ReplayOutcome:
    """Estado reconstruído e o veredito da verificação de determinismo."""

    era: int
    state: PlanetState
    matches_checkpoint: bool
    # Biologia reconstruída da era (Inc 3). É re-DERIVADA do motor semeado, não
    # lida do códex corrente: é isso que prova que a vida emergente também é
    # reprodutível (RF-016/023).
    species: list[SpeciesRecord] = field(default_factory=list)


class ReplayStateUseCase:
    def __init__(
        self,
        repo: PlanetRepository,
        orchestrator: Ticker,
        biology: EvolveBiologyUseCase | None = None,
    ) -> None:
        self._repo = repo
        self._orchestrator = orchestrator
        self._biology = biology

    async def execute(self, planet_id: str, era: int) -> ReplayOutcome:
        target = await self._repo.load_checkpoint(planet_id, era)
        if target is None:
            raise EraNotFoundError(f"{planet_id}#{era}")

        # A era 0 é a gênese: o próprio checkpoint já é o estado reconstruído.
        base = await self._repo.load_checkpoint(planet_id, era - 1) if era > 0 else None
        if base is None:
            return ReplayOutcome(era=era, state=target.state, matches_checkpoint=True)

        events = await self._repo.load_events(planet_id, base.end_tick, target.end_tick)
        rebuilt = replay(
            base.state,
            events,
            target.end_tick,
            self._orchestrator,
            self._orchestrator.bounds,
        )
        return ReplayOutcome(
            era=era,
            state=rebuilt,
            matches_checkpoint=rebuilt == target.state,
            species=await self._replay_biology(planet_id, era),
        )

    async def _replay_biology(self, planet_id: str, era: int) -> list[SpeciesRecord]:
        """Reconstrói o códex reexecutando a biologia de TODAS as eras até `era`.

        Não basta reproduzir a última era: a evolução é cumulativa, então o
        replay parte do vazio e reaplica era a era, exatamente como aconteceu.
        Como cada era é semeada por (semente do planeta, era), o resultado é
        idêntico ao original — sem nunca ler o códex persistido.
        """
        if self._biology is None:
            return []
        catalog: list[SpeciesRecord] = []
        for step in range(1, era + 1):
            checkpoint = await self._repo.load_checkpoint(planet_id, step)
            if checkpoint is None:
                break
            catalog = self._biology.run(
                catalog, checkpoint.state, planet_id=planet_id, era=step
            ).catalog
        return catalog
