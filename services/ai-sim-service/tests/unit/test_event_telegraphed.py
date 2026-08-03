"""Os eventos são TELEGRAFADOS com antecedência (RF-019/020).

Um evento que chega sem aviso não ensina antecipação — ensina azar. O aluno
precisa poder AGIR antes, e para isso o anúncio tem de: (a) sair pelo Canal B
como `EventForecast`, (b) aparecer na `EventSlice`, que é o que a API expõe ao
frontend, e (c) preceder a ocorrência pelo horizonte declarado no catálogo.

Nem todo evento tem o mesmo horizonte: a era glacial é lenta e muito anunciada;
o incêndio quase não dá aviso. O horizonte é parâmetro, não constante.
"""

from __future__ import annotations

from pathlib import Path

from tests.support import build_scripted_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.event.contracts import load_params as event_params
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
CATALOG = event_params()

ONSET = {
    EventKind.METEOR: "MeteorImpact",
    EventKind.DROUGHT: "DroughtBegan",
    EventKind.WILDFIRE: "WildfireIgnited",
    EventKind.ICE_AGE: "IceAgeOnset",
    EventKind.STORM: "StormOccurred",
    EventKind.SUPERVOLCANO: "SupervolcanicEruption",
}


def _run(kind: EventKind, lead: int, ticks: int = 60):
    store = InMemoryEventStore()
    planet = build_scripted_planet(kind, lead=lead, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("telegraph", 2027), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot).snapshot
        trail.append(snapshot)
    return list(store.events), trail


def test_the_forecast_precedes_the_occurrence() -> None:
    """O anúncio sai ANTES, com a antecedência declarada."""
    events, _ = _run(EventKind.METEOR, lead=10)
    forecasts = [e for e in events if e.event_type == "EventForecast"]
    impacts = [e for e in events if e.event_type == "MeteorImpact"]

    assert forecasts, "nenhum evento foi anunciado"
    assert impacts, "o evento anunciado nunca aconteceu"
    assert forecasts[0].occurred_at.tick < impacts[0].occurred_at.tick, (
        "o anúncio não precedeu a ocorrência"
    )
    assert impacts[0].occurred_at.tick - forecasts[0].occurred_at.tick == 10, (
        "a antecedência não corresponde ao horizonte declarado"
    )


def test_the_forecast_is_visible_on_the_slice_for_the_api() -> None:
    """A telegrafia chega ao frontend pela `EventSlice`, não só pelo Canal B."""
    _, trail = _run(EventKind.METEOR, lead=10)
    announced = [s for s in trail if s.event.forecast_kind]

    assert announced, "o anúncio nunca apareceu na fatia — a API não teria o que expor"
    assert announced[0].event.forecast_kind == float(int(EventKind.METEOR))
    assert announced[0].event.forecast_ticks_ahead > 0.0
    assert 0.0 < announced[0].event.forecast_severity <= 1.0


def test_the_countdown_decreases_toward_the_event() -> None:
    """O aviso não é estático: ele conta para baixo, e é isso que dá urgência."""
    _, trail = _run(EventKind.METEOR, lead=10)
    # Só o PRIMEIRO ciclo de anúncio: o cenário roteirizado reagenda assim que o
    # evento termina, e concatenar dois ciclos mostraria a contagem "subindo" na
    # emenda entre eles — que é o próximo aviso começando, não o atual voltando.
    countdown: list[float] = []
    for snapshot in trail:
        if snapshot.event.forecast_kind:
            if countdown and snapshot.event.forecast_ticks_ahead > countdown[-1]:
                break
            countdown.append(snapshot.event.forecast_ticks_ahead)
        elif countdown:
            break

    assert len(countdown) > 3, f"ciclo de anúncio curto demais para afirmar algo: {countdown}"
    assert countdown == sorted(countdown, reverse=True), f"a contagem não decresce: {countdown}"


def test_the_forecast_clears_once_the_event_arrives() -> None:
    """Anunciado e ocorrido, o aviso sai da fatia — senão avisaria duas vezes."""
    _, trail = _run(EventKind.METEOR, lead=6)
    struck = next(s for s in trail if s.event.active_kind)
    assert struck.event.forecast_kind == 0.0, "o evento começou e o anúncio continuou na fatia"


def test_the_warning_horizon_differs_per_event_kind() -> None:
    """A era glacial é muito anunciada; o incêndio quase não avisa (parâmetro)."""
    slow = CATALOG.profile(EventKind.ICE_AGE).forecast_lead
    fast = CATALOG.profile(EventKind.WILDFIRE).forecast_lead
    assert slow > fast, "todos os eventos têm o mesmo horizonte — a telegrafia é constante"


def test_every_occurrence_was_announced_first() -> None:
    """Nenhum evento aparece sem aviso prévio — a regra do RF-019/020."""
    for kind in (EventKind.METEOR, EventKind.DROUGHT, EventKind.STORM):
        events, _ = _run(kind, lead=5)
        forecasts = [e for e in events if e.event_type == "EventForecast"]
        onsets = [e for e in events if e.event_type == ONSET[kind]]
        assert len(forecasts) >= len(onsets), (
            f"{kind.name}: {len(onsets)} ocorrências para {len(forecasts)} avisos"
        )
        for onset in onsets:
            assert any(f.occurred_at.tick < onset.occurred_at.tick for f in forecasts)


def test_the_perturbation_is_exactly_zero_outside_the_event_window() -> None:
    """Fora da janela, ZERO — e não um resíduo numérico.

    Um resíduo que nunca zera manteria o planeta perturbado para sempre e faria a
    linha de base derivar sem causa. É a afirmação de que o teste de
    quase-estacionariedade depende.
    """
    from ecosfera_ai.engines.event.domain import decay_at, perturbation_at

    profile = CATALOG.profile(EventKind.METEOR)
    assert decay_at(profile, -1) == 0.0, "antes do evento já havia perturbação"
    assert decay_at(profile, profile.duration) == 0.0, "a perturbação sobreviveu à janela"
    assert decay_at(profile, profile.duration + 50) == 0.0

    spent = perturbation_at(profile, profile.duration)
    assert all(value == 0.0 for value in spent.values()), f"resíduo após a janela: {spent}"


def test_a_step_profile_does_not_decay_inside_its_window() -> None:
    """`decay = 0` é degrau: a seca dura enquanto dura, com intensidade cheia."""
    from dataclasses import replace

    from ecosfera_ai.engines.event.domain import decay_at

    step = replace(CATALOG.profile(EventKind.DROUGHT), decay=0.0)
    assert decay_at(step, 0) == 1.0
    assert decay_at(step, step.duration // 2) == 1.0
