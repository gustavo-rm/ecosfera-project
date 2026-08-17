"""A avaliação do M6.4 — a taxa de aprovação, IMPRESSA com as ressalvas juntas.

    uv run python scripts/evaluate_m6_4.py                      # sem Ollama: só o registro
    ECOSFERA_OLLAMA_BASE_URL=http://localhost:11434 uv run python scripts/evaluate_m6_4.py
    ECOSFERA_EVAL_MODELS=llama3.2:1b,llama3.1:8b uv run python scripts/evaluate_m6_4.py

Roda os cenários contra o modelo real, registra CADA tentativa, e agrega o que foi
registrado. Nada aqui inventa número: o relatório sai do arquivo de tentativas.

## Por que dois modelos, e não um

O pre-flight do M6.4 perguntou se a medição deve usar `llama3.2:1b` — o modelo
com que o M6.3 provou o pipeline — ou um maior. A resposta honesta é medir os
dois e mostrar a diferença: escolher em silêncio faria o número parecer uma
propriedade do SISTEMA quando é, em parte, propriedade do modelo escolhido.

## Por que o relatório quebra por cenário antes de agregar

O ADR 0028 registrou um confundidor: o piso da cascata é um parágrafo repetitivo
de cinco frases, e o prompt pede reescrita em no máximo o dobro do tamanho. Uma
média única não distingue "o modelo é pior" de "o texto que ele recebeu é
difícil". A cascata sai separada, sempre.

## O que este roteiro NÃO mede

Qualidade pedagógica. Passar na fundamentação diz que a prosa não inventou nada;
não diz que ela ensina melhor que o piso do M6.1. Essa comparação exige leitor
humano com critério, e segue em aberto.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.application.generation.evaluation import EvaluationReport, evaluate
from ecosfera_ai.application.generation.generate_explanation import (
    GenerateAnchoredExplanationUseCase,
    arbitrate_by_category,
)
from ecosfera_ai.application.generation.language_model import LanguageModelPort
from ecosfera_ai.application.generation.rejection_log import (
    GenerationAttempt,
    InMemoryAttemptRecorder,
    JsonlAttemptRecorder,
)
from ecosfera_ai.application.rag.corpus_index import InMemoryCorpusIndex
from ecosfera_ai.application.rag.index_corpus import IndexCorpusUseCase
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase
from ecosfera_ai.domain.consumers.explanation import Register
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.consumers.templates import load_templates
from ecosfera_ai.domain.generation.prompt import load_prompt_spec
from ecosfera_ai.domain.rag.corpus import load_manifest
from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder
from ecosfera_ai.domain.rag.passage import RetrievedPassage
from ecosfera_ai.engines.climate.events import TEMPERATURE_SHIFT, ClimateCauseCode
from ecosfera_ai.engines.event.events import METEOR_IMPACT, EventCauseCode
from ecosfera_ai.engines.evolution.events import SPECIES_EXTINCT, EvolutionCauseCode
from ecosfera_ai.infrastructure.llm.ollama import NullLanguageModel, OllamaLanguageModel
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter

CORPUS = Path("configs/pedagogical_corpus.yaml")
TEMPLATES = Path("configs/explanation_templates.yaml")
LOG_PATH = Path(os.environ.get("ECOSFERA_EVAL_LOG", "var/generation_attempts.jsonl"))
SAMPLES = int(os.environ.get("ECOSFERA_EVAL_SAMPLES", "3"))


def _emit(engine: str, event_type: str, cause: object, tick: int, **extra: object) -> DomainEvent:
    emitter = EventEmitter(engine_id=engine, seed=2027, tick=tick, era=1)
    return emitter.emit(event_type, cause, **extra)  # type: ignore[arg-type]


def _cascade() -> FactualContext:
    """O cenário CONFUNDIDOR: piso longo e repetitivo (ADR 0028)."""
    meteor = _emit(
        "event",
        METEOR_IMPACT,
        EventCauseCode.EVENT_ONSET,
        100,
        participants=("event:meteor",),
        cause_detail={"impact_energy": 0.9},
    )
    cooling = _emit(
        "climate",
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        101,
        causation_id=meteor.event_id,
        cause_detail={"change": -14.0},
    )
    catastrophic = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.CATASTROPHIC_EVENT,
        102,
        causation_id=meteor.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 40.0},
    )
    return FactualContext.of("planet-eval", ContextSlice.of_era(1), (meteor, cooling, catastrophic))


def _ecological() -> FactualContext:
    """Piso curto: duas frases. O controle contra o confundidor da cascata."""
    cooling = _emit(
        "climate",
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        200,
        cause_detail={"change": -9.0},
    )
    ecological = _emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        201,
        causation_id=cooling.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 12.0},
    )
    return FactualContext.of("planet-eval", ContextSlice.of_era(1), (cooling, ecological))


SCENARIOS: tuple[tuple[str, FactualContext, str], ...] = (
    ("cascata (piso longo — CONFUNDIDOR)", _cascade(), "CATASTROPHIC_EVENT"),
    ("extinção ecológica (piso curto)", _ecological(), "THERMAL_INTOLERANCE"),
)


async def _register_for(cause_code: str) -> tuple[RetrievedPassage, ...]:
    manifest = load_manifest(CORPUS)
    index = InMemoryCorpusIndex()
    embedder = DeterministicEmbedder()
    await IndexCorpusUseCase(embedder, index).execute(manifest)
    found = await RetrievePassagesUseCase(embedder, index).for_cause_code(cause_code, limit=3)
    return arbitrate_by_category(found)


def _models() -> list[LanguageModelPort]:
    base_url = os.environ.get("ECOSFERA_OLLAMA_BASE_URL", "").strip()
    if not base_url:
        return [NullLanguageModel()]
    names = [
        name.strip()
        for name in os.environ.get("ECOSFERA_EVAL_MODELS", load_prompt_spec().model).split(",")
        if name.strip()
    ]
    return [OllamaLanguageModel(name, base_url=base_url, timeout_seconds=180.0) for name in names]


def _print_report(title: str, report: EvaluationReport) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print(f"modelos observados: {', '.join(sorted(report.models)) or '(nenhum)'}")

    print("\nPOR CENÁRIO (leia estes ANTES da agregada):")
    for scenario in report.scenarios:
        rate = scenario.approval_rate
        shown = "n/d (nada avaliado)" if rate is None else f"{rate:6.1%}"
        print(f"\n  {scenario.scenario}")
        print(f"    tentativas ............ {scenario.attempts}")
        print(f"    avaliadas ............. {scenario.evaluated}")
        print(
            f"    falhas de infra ....... {scenario.infrastructure_failures} (fora do denominador)"
        )
        print(f"    aprovadas ............. {scenario.approved}")
        print(f"    reprovadas ............ {scenario.rejected}")
        print(f"    TAXA DE APROVAÇÃO ..... {shown}")
        coverage = scenario.full_coverage_rate
        if coverage is not None:
            print(f"    das aprovadas, com verificação COMPLETA: {coverage:.1%}")

    overall = report.overall_approval_rate
    print("\nAGREGADA (com as ressalvas acima):")
    print(f"  {'n/d' if overall is None else f'{overall:.1%}'}", end="")
    print(f"  sobre {report.total_evaluated} geração(ões) avaliada(s)")
    print(f"  falhas de infraestrutura excluídas: {report.total_infrastructure_failures}")

    if report.reason_counts:
        print("\nMOTIVOS DE REPROVAÇÃO, por família:")
        for family, count in report.reason_counts:
            print(f"  {count:3d}  {family}")


async def main() -> int:
    spec = load_prompt_spec()
    renderer = ExplanationRenderer(load_templates(TEMPLATES))
    recorder = JsonlAttemptRecorder(LOG_PATH)
    session = InMemoryAttemptRecorder()

    print("=" * 78)
    print("AVALIAÇÃO M6.4 — geração ancorada sob cenários de avaliação")
    print("=" * 78)
    print(f"amostras por cenário: {SAMPLES}   registro: {LOG_PATH}")

    for model in _models():
        print(f"\n--- modelo: {model.model_name} ---")
        for label, context, cause_code in SCENARIOS:
            floor = renderer.render(context, Register.STANDARD)
            passages = await _register_for(cause_code)
            case = GenerateAnchoredExplanationUseCase(model, spec, recorder=recorder)

            for attempt_number in range(SAMPLES):
                result = await case.execute(
                    floor=floor,
                    context=context,
                    passages=list(passages),
                    scenario=f"{model.model_name} · {label}",
                )
                session.record(
                    GenerationAttempt.of(result, scenario=f"{model.model_name} · {label}")
                )
                state = "recuou" if result.fell_back else "passou"
                print(f"  [{label}] amostra {attempt_number + 1}: {state}")
                if result.fell_back:
                    print(f"      motivo: {result.fallback_reason[:150]}")
                else:
                    print(f"      texto : {result.text[:150]}")

    _print_report("RELATÓRIO DESTA EXECUÇÃO", evaluate(session.read_all()))

    accumulated = recorder.read_all()
    if len(accumulated) > len(session.read_all()):
        _print_report(
            f"RELATÓRIO ACUMULADO ({LOG_PATH}, {len(accumulated)} tentativas)",
            evaluate(accumulated),
        )

    print("\n" + "=" * 78)
    print("RESSALVAS — nenhuma delas é opcional para ler o número acima")
    print("=" * 78)
    print("  · a cascata tem piso longo e repetitivo (ADR 0028): compare os cenários,")
    print("    e não apenas a agregada;")
    print("  · cinco tipos de evento seguem sem checagem de invenção, então uma")
    print("    aprovação não afirma verificação completa — ver DetectionCoverage;")
    print("  · isto mede FUNDAMENTAÇÃO, e não qualidade pedagógica: passar significa")
    print("    que a prosa não inventou nada, e não que ela ensina melhor que o piso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
