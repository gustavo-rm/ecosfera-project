"""Roteiro de fumaça do M6.3 — a geração ancorada, IMPRESSA para inspeção humana.

    uv run python scripts/smoke_m6_3.py           # sem Ollama: mostra o caminho de recuo
    ECOSFERA_OLLAMA_BASE_URL=http://localhost:11434 uv run python scripts/smoke_m6_3.py

Imprime, para cada cenário: o piso do M6.1, as passagens que informaram o
registro (com categoria, para se ver a arbitragem operando), o que o modelo
devolveu, e o veredito. Depois afirma.

A ordem — imprimir antes de afirmar — é a lição do M6.1, onde o roteiro revelou
300 parágrafos quase idênticos que nenhum teste de forma tinha visto, e do M6.2,
onde revelou três defeitos de recuperação. Com saída não-determinística ela vale
mais ainda: um texto pode passar em toda asserção mecânica e ainda assim ler mal,
e a única maneira de descobrir isso é lendo.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.application.generation.generate_explanation import (
    GenerateAnchoredExplanationUseCase,
    arbitrate_by_category,
)
from ecosfera_ai.application.generation.language_model import LanguageModelPort
from ecosfera_ai.application.rag.corpus_index import InMemoryCorpusIndex
from ecosfera_ai.application.rag.index_corpus import IndexCorpusUseCase
from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase
from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.consumers.templates import load_templates
from ecosfera_ai.domain.consumers.wording import (
    absolute_fitness_phrases_in,
    teleological_phrases_in,
)
from ecosfera_ai.domain.generation.anchoring import GeneratedExplanation
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


def _rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


async def _register_for(cause_code: str) -> tuple[RetrievedPassage, ...]:
    manifest = load_manifest(CORPUS)
    index = InMemoryCorpusIndex()
    embedder = DeterministicEmbedder()
    await IndexCorpusUseCase(embedder, index).execute(manifest)
    found = await RetrievePassagesUseCase(embedder, index).for_cause_code(cause_code, limit=3)
    return arbitrate_by_category(found)


def _model() -> LanguageModelPort:
    """O Ollama se houver um respondendo; o modelo nulo se não houver.

    O roteiro roda dos dois jeitos de propósito: sem daemon ele exercita e mostra
    o caminho de RECUO, que é o que o aluno vê quando a infraestrutura falha — e
    que precisa ser inspecionado tanto quanto o caminho feliz.
    """
    base_url = os.environ.get("ECOSFERA_OLLAMA_BASE_URL", "").strip()
    if not base_url:
        return NullLanguageModel()
    spec = load_prompt_spec()
    return OllamaLanguageModel(spec.model, base_url=base_url, timeout_seconds=120.0)


def _print_result(
    floor: Explanation, passages: tuple[RetrievedPassage, ...], result: GeneratedExplanation
) -> None:
    print("\n--- PISO DO M6.1 (o que aconteceu, segundo o event log) ---")
    print(f"  {floor.summary}")

    print("\n--- REGISTRO RECUPERADO (como se diz), já arbitrado por categoria ---")
    if not passages:
        print("  (nenhuma passagem recuperada)")
    for position, passage in enumerate(passages, start=1):
        label = f"[{passage.category.value}]"
        print(f"  {position}. {label} {passage.entry_id}  sim={passage.similarity:.3f}")
        print(f"       {passage.text[:110]}...")
        print(f"       origem: {passage.source}")

    print("\n--- O QUE CHEGA AO ALUNO ---")
    print(f"  modelo   : {result.model_name}")
    print(f"  recuou?  : {'SIM — ' + result.fallback_reason if result.fell_back else 'não'}")
    print(f"  veredito : {result.verdict.summary}")
    for reason in result.verdict.reasons:
        print(f"       · {reason}")
    print(f"\n  {result.text}")


async def _scenario(
    title: str, events: list, cause_code: str, model: LanguageModelPort
) -> GeneratedExplanation:
    _rule(title)
    context = FactualContext.of("planet-smoke", ContextSlice.of_era(1), tuple(events))
    floor = ExplanationRenderer(load_templates(TEMPLATES)).render(context, Register.STANDARD)
    passages = await _register_for(cause_code)

    result = await GenerateAnchoredExplanationUseCase(model, load_prompt_spec()).execute(
        floor=floor, context=context, passages=list(passages)
    )
    _print_result(floor, passages, result)

    # As invariantes, afirmadas DEPOIS de impressas.
    assert result.text.strip(), "chegou texto vazio ao aluno"
    assert teleological_phrases_in(result.text) == (), "formulação teleológica na saída"
    assert absolute_fitness_phrases_in(result.text) == (), "aptidão absoluta na saída"
    if result.fell_back:
        assert result.text == floor.summary, "o recuo tem de entregar o piso inteiro"
    return result


def _cascade() -> list[DomainEvent]:
    """Meteoro com as duas famílias de extinção no mesmo recorte.

    Montado aqui, e não importado de `tests/`: um roteiro que se pretende
    executável por qualquer pessoa não pode depender do pacote de testes estar no
    caminho de import. As duas extinções coexistem de propósito — é assim que a
    distinção do ADR 0019 fica visível numa leitura só.
    """

    def emit(
        engine: str, event_type: str, cause: object, tick: int, **extra: object
    ) -> DomainEvent:
        emitter = EventEmitter(engine_id=engine, seed=2027, tick=tick, era=1)
        return emitter.emit(event_type, cause, **extra)  # type: ignore[arg-type]

    meteor = emit(
        "event",
        METEOR_IMPACT,
        EventCauseCode.EVENT_ONSET,
        100,
        participants=("event:meteor",),
        cause_detail={"impact_energy": 0.9},
    )
    cooling = emit(
        "climate",
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        101,
        causation_id=meteor.event_id,
        cause_detail={"delta": -14.0},
    )
    catastrophic = emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.CATASTROPHIC_EVENT,
        102,
        causation_id=meteor.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 40.0, "removed_fraction": 1.0},
    )
    ecological = emit(
        "evolution",
        SPECIES_EXTINCT,
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        103,
        causation_id=cooling.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 12.0},
    )
    return [meteor, cooling, catastrophic, ecological]


def _ecological_only() -> list[DomainEvent]:
    """O mesmo planeta SEM o meteoro: só o esfriamento e a extinção ecológica.

    Cenário separado porque a primeira versão deste roteiro imprimia a mesma
    cascata duas vezes, mudando só a consulta de registro — e o piso idêntico nos
    dois blocos dava a impressão de que a distinção catastrófica × ecológica
    estava sendo mostrada quando não estava. Aqui a extinção ecológica aparece
    sozinha, que é como um leitor a compara com a de cima.
    """
    cooling = EventEmitter(engine_id="climate", seed=2027, tick=200, era=1).emit(
        TEMPERATURE_SHIFT,
        ClimateCauseCode.RADIATIVE_FORCING,
        cause_detail={"delta": -9.0},
    )
    ecological = EventEmitter(engine_id="evolution", seed=2027, tick=201, era=1).emit(
        SPECIES_EXTINCT,
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        causation_id=cooling.event_id,
        participants=("species:community",),
        cause_detail={"biomass_before": 12.0},
    )
    return [cooling, ecological]


async def main() -> int:
    model = _model()
    print("=" * 78)
    print("ROTEIRO DE FUMAÇA — M6.3, geração ancorada")
    print("=" * 78)
    print(f"modelo de linguagem: {model.model_name}")
    if isinstance(model, NullLanguageModel):
        print("(sem ECOSFERA_OLLAMA_BASE_URL: este roteiro exercita o CAMINHO DE RECUO)")

    cascade = _cascade()
    results = [
        await _scenario(
            "CENÁRIO 1 — extinção CATASTRÓFICA (meteoro do ciclo 100)",
            cascade,
            "CATASTROPHIC_EVENT",
            model,
        ),
        await _scenario(
            "CENÁRIO 2 — extinção ECOLÓGICA, sem catástrofe no recorte",
            _ecological_only(),
            "THERMAL_INTOLERANCE",
            model,
        ),
    ]

    _rule("RESUMO")
    for result in results:
        state = "recuou ao piso" if result.fell_back else "prosa do modelo, verificada"
        print(f"  · {state}")
    print("\nOK — nenhuma saída trouxe formulação proibida, e todo recuo entregou o piso.")
    print("A avaliação adversarial é o M6.4; aqui só se olha se o caminho está de pé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
