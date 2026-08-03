"""Event Engine — os acontecimentos extraordinários e o Diretor (M4).

Roda por ÚLTIMO no tick (Spec §5.3). Escreve UMA fatia — a `EventSlice` — e
nunca as fatias que perturba: quem aplica a perturbação é o Engine dono da
grandeza, lendo o escalar publicado aqui (ADR 0018).

## Os dois canais, e o que cada um carrega

  - **Canal A (`EventSlice`)**: a CONSEQUÊNCIA física contínua — poeira que
    decai, forçamento negativo, intensidade de seca. É float, aditivo e
    replayável, e é o que os Engines afetados leem.
  - **Canal B (Domain Events)**: a OCORRÊNCIA discreta — `MeteorImpact`,
    `DroughtBegan`. É o que o Tutor narra e o que encadeia a cadeia causal.

Separá-los é o que permite ao Atmosphere reagir à poeira sem saber que existe um
catálogo de eventos, e ao Tutor explicar o meteoro sem recalcular física.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.event.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    EventEngineParams,
    load_params,
)
from ecosfera_ai.engines.event.director import decide
from ecosfera_ai.engines.event.domain import EventKind, is_catastrophic, perturbation_at
from ecosfera_ai.engines.event.events import (
    DROUGHT_BEGAN,
    DROUGHT_ENDED,
    EVENT_FORECAST,
    ICE_AGE_ONSET,
    METEOR_IMPACT,
    STORM_OCCURRED,
    SUPERVOLCANIC_ERUPTION,
    WILDFIRE_IGNITED,
    EventCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import EventSlice, SliceRef, StateDelta

# Nome do evento de Canal B que anuncia o INÍCIO de cada tipo. O `DroughtEnded`
# é o único fim que vira evento próprio: uma seca que acaba é notícia para o
# aluno; um meteoro cuja poeira assentou não é um segundo acontecimento.
_ONSET = {
    EventKind.METEOR: METEOR_IMPACT,
    EventKind.DROUGHT: DROUGHT_BEGAN,
    EventKind.WILDFIRE: WILDFIRE_IGNITED,
    EventKind.ICE_AGE: ICE_AGE_ONSET,
    EventKind.STORM: STORM_OCCURRED,
    EventKind.SUPERVOLCANO: SUPERVOLCANIC_ERUPTION,
}

_PERTURBATION_FIELDS = (
    "dust_load",
    "cooling_forcing",
    "drought_intensity",
    "supervolcanic_intensity",
    "impact_energy",
    "catastrophic_mortality",
)


@dataclass(slots=True)
class EventEngine:
    """Implementa a porta `Engine` (Spec §5.2) para os eventos extraordinários."""

    params: EventEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.event
        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        events: list[DomainEvent] = []

        target = _advance(current, self.params, emitter, events)
        if target.active_kind == 0.0 and target.forecast_kind == 0.0:
            target = _maybe_schedule(target, ctx, self.params, emitter, events)

        target = _with_perturbation(target, self.params)
        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values=_delta_values(current, target),
                caused_by=tuple(e.event_id for e in events),
            ),
            events=tuple(events),
            # O Diretor decide a CADA tick, mesmo que decida nada — é uma
            # avaliação processada, e contá-la mantém a série comparável
            # entre ticks calmos e ticks de evento.
            entities_processed=1,
        )


def _advance(
    current: EventSlice,
    params: EventEngineParams,
    emitter: EventEmitter,
    events: list[DomainEvent],
) -> EventSlice:
    """Move o relógio: envelhece o evento ativo, aproxima o anunciado, gasta o silêncio."""
    active_kind = int(current.active_kind)
    elapsed = int(current.active_elapsed)
    quiet = max(0.0, current.quiet_remaining - 1.0)

    # 1. O evento ativo envelhece e, no fim da janela, termina.
    if active_kind:
        elapsed += 1
        if elapsed >= params.profile(EventKind(active_kind)).duration:
            if active_kind == int(EventKind.DROUGHT):
                events.append(
                    emitter.emit(
                        DROUGHT_ENDED,
                        EventCauseCode.EVENT_SUBSIDED,
                        location={"region_id": "global"},
                        participants=["event:drought"],
                        environmental_factors=["water:recovering"],
                        cause_detail={"duration": float(elapsed)},
                    )
                )
            return _replace_state(
                current, kind=0, elapsed=0, severity=0.0, quiet=params.quiet_ticks_after
            )
        return _replace_state(
            current,
            kind=active_kind,
            elapsed=elapsed,
            severity=current.active_severity,
            quiet=quiet,
        )

    # 2. O evento anunciado se aproxima; ao chegar a zero, ACONTECE.
    pending = int(current.forecast_kind)
    if pending:
        remaining = current.forecast_ticks_ahead - 1.0
        if remaining > 0.0:
            return _replace_state(
                current,
                kind=0,
                elapsed=0,
                severity=0.0,
                quiet=quiet,
                forecast=(pending, remaining, current.forecast_severity),
            )
        kind = EventKind(pending)
        profile = params.profile(kind)
        events.append(
            emitter.emit(
                _ONSET[kind],
                EventCauseCode.EVENT_ONSET,
                location={"region_id": "global"},
                participants=[f"event:{kind.name.lower()}"],
                environmental_factors=_factors_of(kind),
                resources=["biomass"] if is_catastrophic(profile) else [],
                # `consequences` NÃO sai daqui. Anunciar "extinction" no impacto
                # seria adivinhar um efeito que ainda não aconteceu — pode não
                # haver extinção alguma. A relação causa->efeito é PROJETADA do
                # Event Store, invertendo os `causation_id` depois do fato
                # (ADR-ARCH-0002). O envelope carrega `cause_detail`, que é o
                # que o consumidor precisa para descobrir isso sozinho.
                cause_detail={
                    "kind": float(int(kind)),
                    "severity": current.forecast_severity,
                    "duration": float(profile.duration),
                    "catastrophic": 1.0 if is_catastrophic(profile) else 0.0,
                },
            )
        )
        return _replace_state(
            current, kind=int(kind), elapsed=0, severity=current.forecast_severity, quiet=quiet
        )

    return _replace_state(current, kind=0, elapsed=0, severity=0.0, quiet=quiet)


def _maybe_schedule(
    state: EventSlice,
    ctx: TickContext,
    params: EventEngineParams,
    emitter: EventEmitter,
    events: list[DomainEvent],
) -> EventSlice:
    """Consulta o Diretor e, havendo decisão, TELEGRAFA o evento (RF-019/020).

    O anúncio é o ponto do desenho: o aluno precisa poder AGIR antes, e um evento
    que chega sem aviso não ensina antecipação — ensina azar.
    """
    if state.quiet_remaining > 0.0:
        return state

    schedule = decide(ctx.snapshot, ctx.rng, params, quiet=False)
    if schedule.kind is EventKind.NONE:
        return state

    events.append(
        emitter.emit(
            EVENT_FORECAST,
            EventCauseCode.FORECAST_ANNOUNCED,
            location={"region_id": "global"},
            participants=[f"event:{schedule.kind.name.lower()}"],
            environmental_factors=_factors_of(schedule.kind),
            cause_detail={
                "kind": float(int(schedule.kind)),
                "ticks_ahead": float(schedule.ticks_ahead),
                "severity": schedule.severity,
            },
        )
    )
    return _replace_state(
        state,
        kind=0,
        elapsed=0,
        severity=0.0,
        quiet=state.quiet_remaining,
        forecast=(int(schedule.kind), float(schedule.ticks_ahead), schedule.severity),
    )


def _with_perturbation(state: EventSlice, params: EventEngineParams) -> EventSlice:
    """Preenche os escalares de perturbação a partir do evento ativo."""
    if not state.active_kind:
        return state
    profile = params.profile(EventKind(int(state.active_kind)))
    scaled = {
        name: value * state.active_severity
        for name, value in perturbation_at(profile, int(state.active_elapsed)).items()
    }
    return EventSlice(**{**_state_dict(state), **scaled})


def _factors_of(kind: EventKind) -> list[str]:
    """Fatores ambientais declarados no envelope — dado, não prosa."""
    return {
        EventKind.METEOR: ["climate:dust", "climate:cooling"],
        EventKind.DROUGHT: ["water:scarce"],
        EventKind.WILDFIRE: ["biomass:burning"],
        EventKind.ICE_AGE: ["climate:cooling"],
        EventKind.STORM: ["climate:turbulence"],
        EventKind.SUPERVOLCANO: ["climate:dust", "geology:outgassing"],
    }[kind]


def _state_dict(state: EventSlice) -> dict[str, float]:
    return {name: float(getattr(state, name)) for name in EventSlice.__dataclass_fields__}


def _replace_state(
    current: EventSlice,
    *,
    kind: int,
    elapsed: int,
    severity: float,
    quiet: float,
    forecast: tuple[int, float, float] = (0, 0.0, 0.0),
) -> EventSlice:
    """Novo estado de bookkeeping, com as perturbações ZERADAS.

    Zerar aqui e repreencher em `_with_perturbation` é o que garante que uma
    perturbação nunca sobreviva ao evento que a causou. Um resíduo que não zera
    manteria o planeta perturbado para sempre e faria a linha de base derivar sem
    causa — o defeito que `test_baseline_quasi_stationary` existe para pegar.
    """
    del current
    return EventSlice(
        active_kind=float(kind),
        active_elapsed=float(elapsed),
        active_severity=severity,
        quiet_remaining=quiet,
        forecast_kind=float(forecast[0]),
        forecast_ticks_ahead=forecast[1],
        forecast_severity=forecast[2],
    )


def _delta_values(before: EventSlice, after: EventSlice) -> dict[str, float]:
    """O Canal A é ADITIVO: publica-se a diferença, não o valor absoluto."""
    return {
        name: float(getattr(after, name)) - float(getattr(before, name))
        for name in EventSlice.__dataclass_fields__
    }


__all__ = ["_PERTURBATION_FIELDS", "EventEngine"]
