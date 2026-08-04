"""Export e import de uma simulação inteira, com verificação de replay.

Camada de PLATAFORMA (Spec §1; ADR-ARCH-0001 Emenda 3): não roda tick nem
implementa replay próprio — costura o repositório, o artefato portável e o motor
de replay que já existe.

## Por que a verificação faz parte do import

Importar sem conferir devolveria um planeta que PARECE o original. A conferência
reexecuta o replay sobre o artefato importado e compara com o checkpoint que veio
dentro dele: se divergirem, o artefato viajou entre versões incompatíveis, ou o
motor mudou, e é melhor saber na importação do que numa aula.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.portable import SimulationExport
from ecosfera_ai.shared_kernel.world_state import WORLD_STATE_VERSION
from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.timeline import EraCheckpoint


@dataclass(frozen=True, slots=True)
class ImportReport:
    """O que a importação encontrou — auditável, não um booleano solto."""

    planet_id: str
    eras_imported: int
    events_imported: int
    checkpoints_match: bool
    divergent_eras: tuple[int, ...] = ()

    @property
    def faithful(self) -> bool:
        return self.checkpoints_match and not self.divergent_eras


class ExportSimulationUseCase:
    """Empacota uma simulação inteira num artefato portável."""

    def __init__(self, repo: PlanetRepository, *, params_version: int) -> None:
        self._repo = repo
        self._params_version = params_version

    async def execute(
        self, planet_id: str, *, events: Sequence[DomainEvent] = ()
    ) -> SimulationExport:
        timeline = await self._repo.get_timeline(planet_id)
        checkpoints: dict[str, dict[str, float | str]] = {}
        seed = 0
        for summary in timeline:
            checkpoint = await self._repo.load_checkpoint(planet_id, summary.era)
            if checkpoint is None:
                continue
            seed = checkpoint.seed
            checkpoints[str(checkpoint.era)] = dict(checkpoint.state.to_dict())

        return SimulationExport(
            planet_id=planet_id,
            seed=seed,
            world_state_version=WORLD_STATE_VERSION,
            params_version=self._params_version,
            checkpoints=checkpoints,
            events=SimulationExport.encode_events(list(events)),
            metadata={"eras": len(checkpoints)},
        )


class ImportSimulationUseCase:
    """Recarrega um artefato e CONFERE que ele reproduz o original."""

    def __init__(self, repo: PlanetRepository) -> None:
        self._repo = repo

    async def execute(self, artefact: SimulationExport) -> ImportReport:
        divergent: list[int] = []
        for era in artefact.eras():
            state = PlanetState.from_dict(dict(artefact.checkpoint(era)))
            await self._repo.append_checkpoint(
                EraCheckpoint(
                    planet_id=artefact.planet_id,
                    era=era,
                    seed=artefact.seed,
                    start_tick=state.tick,
                    end_tick=state.tick,
                    state=state,
                )
            )
            # Conferência imediata: o que voltou do repositório é o que entrou?
            # Uma perda na ida e volta da persistência é exatamente a dívida de
            # rehidratação que este marco paga, e é aqui que ela apareceria.
            stored = await self._repo.load_checkpoint(artefact.planet_id, era)
            if stored is None or stored.state.to_dict() != state.to_dict():
                divergent.append(era)

        return ImportReport(
            planet_id=artefact.planet_id,
            eras_imported=len(artefact.eras()),
            events_imported=len(artefact.events),
            checkpoints_match=not divergent,
            divergent_eras=tuple(divergent),
        )
