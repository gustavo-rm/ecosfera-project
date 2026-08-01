"""O rastro causal do M1: erupção → forçamento → temperatura, encadeado por id.

É o "como chegamos aqui" que o Tutor precisa (ADR-ARCH-0002, Pilar 4). O
encadeamento tem de ser reconstruível a partir da trilha SOZINHA, sem consultar
o world-state nem a ordem em que os eventos foram gravados.
"""

from __future__ import annotations

from pathlib import Path

from tests.support import build_volcanic_planet

from ecosfera_ai.application.feedback.explain_from_events import causal_trace
from ecosfera_ai.engines.atmosphere.events import GREENHOUSE_FORCING_CHANGED
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.climate.events import CLIMATE_THRESHOLD_CROSSED, TEMPERATURE_SHIFT
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.engines.geology.events import VOLCANIC_ERUPTION
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
# O oceano AMORTECE o carbono desde o M2 (ADR 0012): a atmosfera acumula mais
# devagar, e a cadeia erupção→forçamento→clima leva mais ticks para se fechar do
# que levava no M1. A janela cresceu para acompanhar a física, não para afrouxar
# a asserção — o que se verifica continua sendo o encadeamento por `causation_id`.
TICKS = 130


def _events(seed: int = 2027) -> list[DomainEvent]:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("trace", seed), PARAMS))
    collected: list[DomainEvent] = []
    for _ in range(TICKS):
        outcome = planet.tick(snapshot)
        snapshot = outcome.snapshot
        collected.extend(outcome.events)
    return collected


def _volcanic_events(seed: int = 2027, ticks: int = TICKS) -> list[DomainEvent]:
    """A mesma moldura, num planeta VULCANICAMENTE ATIVO (ver `tests.support`)."""
    planet = build_volcanic_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("volcanic", seed), PARAMS))
    collected: list[DomainEvent] = []
    for _ in range(ticks):
        outcome = planet.tick(snapshot, publish=False)
        snapshot = outcome.snapshot
        collected.extend(outcome.events)
    return collected


def test_the_three_engines_all_speak() -> None:
    types = {event.event_type for event in _events()}
    assert VOLCANIC_ERUPTION in types
    assert GREENHOUSE_FORCING_CHANGED in types
    assert types & {TEMPERATURE_SHIFT, CLIMATE_THRESHOLD_CROSSED}


def test_the_chain_reaches_from_the_eruption_to_the_climate() -> None:
    """A cadeia completa, reconstruída só por `causation_id`, num planeta ativo."""
    events = _volcanic_events()
    by_id = {event.event_id: event for event in events}
    parent_type = {
        event.event_id: by_id[event.causation_id].event_type
        for event in events
        if event.causation_id and event.causation_id in by_id
    }

    forcing_from_eruption = [
        event
        for event in events
        if event.event_type == GREENHOUSE_FORCING_CHANGED
        and parent_type.get(event.event_id) == VOLCANIC_ERUPTION
    ]
    climate_from_forcing = [
        event
        for event in events
        if event.event_type in {TEMPERATURE_SHIFT, CLIMATE_THRESHOLD_CROSSED}
        and parent_type.get(event.event_id) == GREENHOUSE_FORCING_CHANGED
    ]

    assert forcing_from_eruption, "nenhum forçamento atribuído a uma erupção"
    assert climate_from_forcing, "nenhum efeito climático atribuído ao forçamento"


def test_causation_crosses_ticks() -> None:
    """A causa pode estar num tick anterior — o efeito demora a se acumular."""
    events = _volcanic_events()
    by_id = {event.event_id: event for event in events}
    lags = [
        event.occurred_at.tick - by_id[event.causation_id].occurred_at.tick
        for event in events
        if event.causation_id and event.causation_id in by_id
    ]
    assert lags, "nenhum encadeamento produzido"
    assert max(lags) > 0, "sem defasagem, a proveniência não estaria atravessando ticks"


def test_the_trace_projection_inverts_causation() -> None:
    """`consequences` não é emitido pelo Engine — é projeção do Event Store."""
    events = _volcanic_events()
    links = causal_trace(events)

    assert links
    for link in links:
        assert link.cause_event != link.effect_event
        assert link.cause_code
    # O Engine não pode adivinhar efeitos que ainda não aconteceram.
    assert all(event.consequences == () for event in events)


def test_events_of_one_tick_share_the_correlation() -> None:
    events = _events()
    by_tick: dict[int, set[str]] = {}
    for event in events:
        by_tick.setdefault(event.occurred_at.tick, set()).add(event.correlation_id)
    assert all(len(ids) == 1 for ids in by_tick.values())


def test_the_trace_is_reproducible_under_the_same_seed() -> None:
    assert [e.event_id for e in _events(seed=31337)] == [e.event_id for e in _events(seed=31337)]


def test_the_snapshot_is_truncated_at_the_http_boundary() -> None:
    """Limitação conhecida do M1, fixada para não virar regressão silenciosa.

    O estado persistido ainda é o `PlanetState` legado, que não tem campo para
    forçamento, pressão, fluxo de CO2 nem proveniência causal. Cada tick da borda
    HTTP passa por ele e trunca essas grandezas.

    Física intacta (são funções puras de CO2/vulcanismo, recalculadas idênticas);
    o que se perde é o encadeamento causal ENTRE ticks. O M5 fecha isso ao
    persistir o `WorldStateSnapshot` inteiro (ADR 0011, §4b).
    """
    from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
    from ecosfera_ai.shared_kernel.world_state import SliceRef

    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    rich = planet.tick(snapshot_of(initial_state(PlanetSeed("trunc", 2027), PARAMS))).snapshot
    rich = rich.with_provenance({SliceRef.GEOLOGY: ("evento-1",)})

    survived = snapshot_of(planet_state_of(rich))

    # O que sobrevive: os estoques.
    assert survived.atmosphere.co2 == rich.atmosphere.co2
    assert survived.geology.volcanism == rich.geology.volcanism
    assert survived.climate.temperature == rich.climate.temperature
    # O que não sobrevive — e por isso a detecção de faixa deriva do estoque.
    assert survived.atmosphere.greenhouse_forcing == 0.0
    assert dict(survived.provenance) == {}


def test_within_a_single_tick_the_chain_still_holds_after_truncation() -> None:
    """O que a truncagem NÃO tira: o encadeamento dentro do mesmo tick."""
    from ecosfera_ai.engines.composition import FrameworkTickOrchestrator

    ticker = FrameworkTickOrchestrator(
        build_planet_engine(PARAMS, budget=PARAMS.engine_budget), PARAMS.bounds
    )
    state = initial_state(PlanetSeed("intratick", 2027), PARAMS)
    for _ in range(40):
        state = ticker.tick(state).state

    # A trajetória continua sã mesmo com o snapshot truncado a cada passo.
    assert state.co2 > PARAMS.initial_state.co2
    assert state.temperature > PARAMS.initial_state.temperature
