"""Climate Engine — resolve a temperatura a partir do forçamento radiativo.

Último elo da fatia vertical do M1. Lê o forçamento já calculado na
`AtmosphereSlice` (Canal A) e resolve o balanço de energia. Não sabe o que é CO2
— e é justamente por não saber que a fronteira se sustenta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.climate.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    ClimateEngineParams,
    load_params,
)
from ecosfera_ai.engines.climate.domain import (
    absorbed_energy,
    equilibrium_temperature,
    ocean_heat_flux,
    temperature_band,
)
from ecosfera_ai.engines.climate.events import (
    CLIMATE_THRESHOLD_CROSSED,
    TEMPERATURE_SHIFT,
    ClimateCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta


@dataclass(slots=True)
class ClimateEngine:
    """Implementa a porta `Engine` (Spec §5.2) para o domínio climático."""

    params: ClimateEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.climate
        hydrology = ctx.snapshot.hydrology
        forcing = ctx.snapshot.atmosphere.greenhouse_forcing
        # Irradiância do MESMO tick, escrita pelo Astronomy Engine. Antes do M2
        # ela vinha da `LegacySlice`; com o adaptador aposentado e sem este
        # Engine, o clima recairia no `params.insolation` e o planeta perderia
        # estações em silêncio — daí `test_solar_flux_has_writer` (ADR 0013).
        solar_flux = ctx.snapshot.astronomy.solar_flux
        # Criosfera: a fração de gelo é PUBLICADA pela hidrologia, não recalculada
        # aqui — um Engine não importa outro, e derivar a mesma grandeza duas
        # vezes é ciência duplicada. Leitura defasada: ela roda depois (ADR 0012).
        ice_cover = hydrology.ice_fraction

        absorbed = absorbed_energy(solar_flux, ice_cover, self.params)
        target = equilibrium_temperature(absorbed, forcing, self.params)

        drift = self.params.thermal_inertia * (target - current.temperature)
        weather = float(ctx.rng.normal(0.0, self.params.weather_variability))
        ocean = ocean_heat_flux(current.temperature, hydrology.ocean_circulation, self.params)
        d_temperature = drift + weather + ocean
        temperature = current.temperature + d_temperature

        events = self._notable(ctx, current.temperature, temperature, d_temperature, forcing)

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "temperature": d_temperature,
                    "energy": absorbed - current.energy,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=1,
        )

    def _notable(
        self,
        ctx: TickContext,
        before: float,
        after: float,
        change: float,
        forcing: float,
    ) -> tuple[DomainEvent, ...]:
        """Traduz o tick em ocorrências notáveis — nunca em todo tick.

        Dois gatilhos distintos: uma variação grande o bastante em um único tick
        (`TemperatureShift`) e a travessia de um patamar climático
        (`ClimateThresholdCrossed`). O segundo é o que interessa ao aluno; o
        primeiro é o que interessa a quem investiga um transiente.
        """
        band_before = temperature_band(before, self.params)
        band_after = temperature_band(after, self.params)
        big_shift = abs(change) >= self.params.shift_threshold
        if not big_shift and band_before == band_after:
            return ()

        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        # Encadeia com o evento da atmosfera do MESMO tick, quando houve.
        causation = ctx.caused_by_slice(SliceRef.ATMOSPHERE)
        detail: dict[str, float | int | str] = {
            "temperature": after,
            "change": change,
            "forcing": forcing,
        }
        events: list[DomainEvent] = []
        if big_shift:
            events.append(
                emitter.emit(
                    TEMPERATURE_SHIFT,
                    ClimateCauseCode.RADIATIVE_FORCING,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    environmental_factors=[f"forcing:{'high' if forcing > 0 else 'low'}"],
                    cause_detail=detail,
                    causation_id=causation,
                )
            )
        if band_before != band_after:
            events.append(
                emitter.emit(
                    CLIMATE_THRESHOLD_CROSSED,
                    ClimateCauseCode.RADIATIVE_FORCING,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    cause_detail={**detail, "band_from": band_before, "band_to": band_after},
                    # Se houve TemperatureShift neste tick, ele é a causa direta;
                    # senão, herda a causa da atmosfera.
                    causation_id=events[0].event_id if events else causation,
                )
            )
        return tuple(events)
