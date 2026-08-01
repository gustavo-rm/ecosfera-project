"""Astronomy Engine — órbita e irradiância (o antigo subsystem `physics`).

Abre a ordem do tick porque a insolação é a **entrada de energia** de tudo o que
vem abaixo: sem ela, o clima recairia numa constante de referência e o planeta
perderia estações e excentricidade. Ver ADR 0013 (`physics` → Astronomy Engine).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.astronomy.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    AstronomyEngineParams,
    load_params,
)
from ecosfera_ai.engines.astronomy.domain import integrate, solar_flux_at
from ecosfera_ai.engines.astronomy.events import INSOLATION_SHIFT, AstronomyCauseCode
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta

_EPS = 1e-9


@dataclass(slots=True)
class AstronomyEngine:
    """Implementa a porta `Engine` (Spec §5.2) para a órbita e a radiação."""

    params: AstronomyEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.astronomy
        x, y, vx, vy = integrate(
            current.orbital_x,
            current.orbital_y,
            current.orbital_vx,
            current.orbital_vy,
            self.params,
        )
        flux = solar_flux_at(x, y, self.params)
        d_flux = flux - current.solar_flux

        events: tuple[DomainEvent, ...] = ()
        # Variação RELATIVA: a insolação de um planeta distante é pequena em
        # termos absolutos, e a estação dele não é menos estação por isso. O zero
        # de abertura não conta como travessia — é ausência de medida.
        reference = max(abs(current.solar_flux), _EPS)
        notable = abs(d_flux) / reference >= self.params.insolation_shift_threshold
        if current.solar_flux > 0.0 and notable:
            emitter = EventEmitter(
                engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era
            )
            events = (
                emitter.emit(
                    INSOLATION_SHIFT,
                    AstronomyCauseCode.ORBITAL_ECCENTRICITY,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    resources=["energy"],
                    cause_detail={"solar_flux": flux, "change": d_flux},
                ),
            )

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "orbital_x": x - current.orbital_x,
                    "orbital_y": y - current.orbital_y,
                    "orbital_vx": vx - current.orbital_vx,
                    "orbital_vy": vy - current.orbital_vy,
                    "solar_flux": d_flux,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=1,
        )
