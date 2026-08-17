"""A distinção do ADR 0019 sob dossiês AMBÍGUOS, e não sob os exemplos limpos.

Todos os testes anteriores usaram cenários de manual: um meteoro que mata de uma
vez, uma temperatura que sai da faixa tolerada. A pergunta do M6.4 é outra — a
distinção sobrevive quando o caso é menos nítido?

Três formas de "menos nítido", e elas são as que um planeta real produz:

  1. **as duas extinções no mesmo tick.** Nada as separa no tempo, e a única
     coisa que as distingue é o `cause_code` e o elo causal;
  2. **a catastrófica encadeada a um efeito INTERMEDIÁRIO** — o meteoro causa
     resfriamento, e a extinção aponta para o resfriamento. A tentação é narrar
     como ecológica ("não aguentou o frio"), quando o ADR 0019 §4 manda apontar
     para o evento;
  3. **a ecológica logo depois de uma catástrofe.** A vizinhança temporal sugere
     causa comum, e a leitura errada colapsa as duas numa só.

O que se afirma aqui é sobre o VERIFICADOR e o DOSSIÊ, não sobre o modelo: que a
informação necessária para distinguir continua presente e conferível mesmo nos
casos ambíguos. Se ela sumisse, nenhum prompt salvaria a narração.
"""

from __future__ import annotations

from tests.support_explanation import explain
from tests.support_generation import ScriptedModel, spec, use_case

from ecosfera_ai.domain.consumers.factual_context import (
    ContextSlice,
    ExtinctionNature,
    FactualContext,
)
from ecosfera_ai.domain.generation.grounding import verify_grounding
from ecosfera_ai.engines.climate.events import TEMPERATURE_SHIFT, ClimateCauseCode
from ecosfera_ai.engines.event.events import METEOR_IMPACT, EventCauseCode
from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT, EvolutionCauseCode
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter


def _emit(engine: str, event_type: str, cause: object, tick: int, **extra: object) -> DomainEvent:
    emitter = EventEmitter(engine_id=engine, seed=2027, tick=tick, era=1)
    return emitter.emit(event_type, cause, **extra)  # type: ignore[arg-type]


def _simultaneous() -> FactualContext:
    """As duas extinções no MESMO tick — o tempo não as separa."""
    meteor = _emit("event", METEOR_IMPACT, EventCauseCode.EVENT_ONSET, 300)
    catastrophic = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.CATASTROPHIC_EVENT,
        301,
        causation_id=meteor.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 40.0},
    )
    ecological = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        301,
        participants=("species:community",),
        cause_detail={"biomass_before": 8.0},
    )
    return FactualContext.of(
        "planet-borderline", ContextSlice.of_era(1), (meteor, catastrophic, ecological)
    )


def _catastrophe_through_an_intermediate() -> FactualContext:
    """A extinção catastrófica aponta para o RESFRIAMENTO, não para o meteoro.

    O caso do ADR 0019 §4: a cadeia passa por um efeito intermediário, e narrar
    "não aguentou o frio" transformaria a catástrofe em falha de adaptação.
    """
    meteor = _emit("event", METEOR_IMPACT, EventCauseCode.EVENT_ONSET, 400)
    cooling = _emit(
        "climate",
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        401,
        causation_id=meteor.event_id,
        cause_detail={"change": -18.0},
    )
    catastrophic = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.CATASTROPHIC_EVENT,
        402,
        causation_id=cooling.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 30.0},
    )
    return FactualContext.of(
        "planet-chain", ContextSlice.of_era(1), (meteor, cooling, catastrophic)
    )


SIMULTANEOUS = _simultaneous()
THROUGH_INTERMEDIATE = _catastrophe_through_an_intermediate()


# --- A informação que distingue continua no dossiê ----------------------------


def test_two_extinctions_in_the_same_tick_stay_distinguishable() -> None:
    """O tempo não separa; a natureza da causa sim — e ela é DADO."""
    natures = {extinction.nature for extinction in SIMULTANEOUS.extinctions}

    assert natures == {ExtinctionNature.CATASTROPHIC, ExtinctionNature.ECOLOGICAL}
    ticks = {extinction.occurred_at.tick for extinction in SIMULTANEOUS.extinctions}
    assert len(ticks) == 1, "o cenário precisa mesmo ser simultâneo para valer"


def test_a_catastrophe_reached_through_an_intermediate_is_still_catastrophic() -> None:
    """Encadear pelo resfriamento não converte a catástrofe em ecológica.

    A natureza vem do `cause_code`, e não da forma da cadeia — é o que impede a
    leitura "morreu de frio" de virar "não se adaptou".
    """
    extinctions = THROUGH_INTERMEDIATE.extinctions
    assert len(extinctions) == 1
    assert extinctions[0].nature is ExtinctionNature.CATASTROPHIC


# --- A narração que colapsa a distinção é barrada, nos dois cenários ----------


async def test_blaming_adaptation_in_the_simultaneous_case_is_refused() -> None:
    floor = explain(list(SIMULTANEOUS.events))
    seduced = "As duas comunidades desapareceram porque eram inferiores ao ambiente."

    result = await use_case(ScriptedModel(seduced)).execute(floor=floor, context=SIMULTANEOUS)

    assert result.fell_back
    assert "Q5" in result.fallback_reason


async def test_blaming_adaptation_through_the_intermediate_is_refused() -> None:
    """O caso mais sutil: a frase é quase razoável, e é a concepção a desfazer."""
    floor = explain(list(THROUGH_INTERMEDIATE.events))
    seduced = "A comunidade não era boa o suficiente para o frio e por isso se extinguiu."

    result = await use_case(ScriptedModel(seduced)).execute(
        floor=floor, context=THROUGH_INTERMEDIATE
    )

    assert result.fell_back
    assert "Q5" in result.fallback_reason


# --- E a narração correta continua passando nos dois --------------------------


def test_the_correct_framing_passes_in_both_borderline_scenarios() -> None:
    """Contraprova: ambiguidade não pode virar recusa de tudo.

    Um verificador que reprovasse toda prosa sobre cenário ambíguo seria
    indistinguível de um que funciona, em toda suíte que só testa o caso ruim.
    """
    correct = (
        "O evento extremo eliminou a comunidade de uma vez, por mais bem adaptada que "
        "ela estivesse: um acontecimento assim não escolhe quem sobrevive."
    )
    for context in (SIMULTANEOUS, THROUGH_INTERMEDIATE):
        floor = explain(list(context.events))
        verdict = verify_grounding(correct, floor=floor, context=context, spec=spec())
        assert verdict.passed, verdict.reasons
