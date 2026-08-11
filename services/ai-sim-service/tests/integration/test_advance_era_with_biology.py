"""Fluxo HTTP com o caminho de biologia POR ERA ligado (fila inline).

Desde o M3 esse caminho está DESLIGADO por padrão (ADR 0017, tempo 1): ele roda o
AG do DEAP sobre uma função de aptidão escalar, que a DEC-01 proíbe. Estes testes
o exercitam, então precisam LIGÁ-LO explicitamente — herdar o padrão faria o
arquivo testar silenciosamente outra coisa no dia em que o padrão mudasse (que é
exatamente o que acabou de acontecer).

O arquivo inteiro sai no tempo 3, junto com o caminho legado.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tests.support import build_orchestrator

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.ports.job_queue import JobRef, JobResult, JobStatus
from ecosfera_ai.application.simulation.advance_era import AdvanceEraUseCase
from ecosfera_ai.application.simulation.create_planet import CreatePlanetUseCase
from ecosfera_ai.config.settings import get_settings
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import InMemoryPlanetRepository
from ecosfera_ai.interfaces.http import deps
from ecosfera_ai.main import create_app
from ecosfera_ai.simulation_engine.params import load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))

BASE = "/ai/api/v1/simulation"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Cliente com o caminho de biologia por era LIGADO, explicitamente.

    Sobrescreve a fixture global do `conftest`. As caches de composição são
    limpas antes e depois: `get_settings` e os provedores de `deps` são
    `lru_cache`, e um cliente montado com a flag desligada continuaria valendo
    para os testes seguintes.
    """
    monkeypatch.setenv("ECOSFERA_BIOLOGY_ENABLED", "true")
    _reset_composition_caches()
    try:
        yield TestClient(create_app())
    finally:
        monkeypatch.delenv("ECOSFERA_BIOLOGY_ENABLED", raising=False)
        _reset_composition_caches()


def _reset_composition_caches() -> None:
    get_settings.cache_clear()
    for name in dir(deps):
        candidate = getattr(deps, name)
        if hasattr(candidate, "cache_clear"):
            candidate.cache_clear()


def test_advance_era_returns_new_and_extinct_species(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 2027}).json()["planet_id"]

    body = client.post(f"{BASE}/planets/{planet_id}/advance-era").json()
    biology = body["biology"]
    assert biology is not None, "com a fila inline o resultado resolve na hora (200)"
    assert biology["era"] == 1
    assert biology["speciated"], "a primeira era semeia a vida"
    assert body["job"] is None  # inline não devolve referência de job


def test_codex_and_biology_events_are_persisted(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 4242}).json()["planet_id"]
    for _ in range(4):
        client.post(f"{BASE}/planets/{planet_id}/advance-era")

    codex = client.get(f"{BASE}/planets/{planet_id}/species").json()
    assert codex["planet_id"] == planet_id
    assert codex["living"] >= 1
    assert len(codex["species"]) == codex["living"] + codex["extinct"]

    # Genoma inspecionável (RF-031): traços nomeados, não pesos opacos.
    first = codex["species"][0]
    assert set(first["genome"]) == {
        "temp_optimum",
        "temp_tolerance",
        "water_need",
        "size",
        "metabolism",
        "trophic_level",
    }
    assert first["trophic_class"] in (1, 2, 3)

    # Os eventos biológicos entram no MESMO event log append-only da timeline.
    eras = client.get(f"{BASE}/planets/{planet_id}/timeline").json()["eras"]
    assert sum(era["event_count"] for era in eras) >= 1


def test_ecology_snapshot_respects_the_carrying_capacity(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 555}).json()["planet_id"]
    for _ in range(3):
        client.post(f"{BASE}/planets/{planet_id}/advance-era")

    ecology = client.get(f"{BASE}/planets/{planet_id}/ecology").json()
    assert ecology["carrying_capacity"] > 0.0
    assert ecology["total_population"] >= 0.0
    # A capacidade vem da camada determinística e limita a vida emergente.
    assert ecology["total_population"] <= ecology["carrying_capacity"] * 1.5
    assert all(p["population"] >= 0.0 for p in ecology["populations"])


def test_causal_explanation_mentions_emergent_biology(client: TestClient) -> None:
    """O feedback continua sem LLM, e a era continua narrando efeito biológico.

    Desde o M6.1 a narração de eventos sai de templates ancorados no dossiê, e
    não da propagação de variáveis do motor de regras (ADR 0026) — então os ids
    do rastro passaram a ser `T-*` em vez de `R-*`. A promessa verificada é a
    mesma de antes: uma era não pode ser narrada só como física, ignorando o que
    aconteceu com a vida.
    """
    planet_id = client.post(f"{BASE}/planets", json={"seed": 31337}).json()["planet_id"]
    body = client.post(f"{BASE}/planets/{planet_id}/advance-era").json()

    explanation = body["explanation"]
    assert explanation["source"] == "rules"
    assert explanation["grounded"] is True
    biological_templates = {
        "T-LIFE-EMERGED",
        "T-TRAIT-ADAPTATION",
        "T-TRAIT-ADAPTATION-REPEATED",
        "T-EXTINCTION-ECOLOGICAL",
        "T-EXTINCTION-CATASTROPHIC",
        "T-EXTINCTION-CATASTROPHIC-UNTRACED",
        "T-MASS-MORTALITY",
        "T-MASS-MORTALITY-CATASTROPHIC",
        "T-TROPHIC-COLLAPSE",
        "T-SPECIATION-COMMON-ANCESTOR",
    }
    fired = {step["rule_id"] for step in explanation["chain"]}
    assert fired & biological_templates, "a era deveria narrar ao menos um efeito biológico"


def test_unknown_species_returns_problem_404(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 1}).json()["planet_id"]
    resp = client.get(f"{BASE}/planets/{planet_id}/species/nao-existe")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_ecology_of_unknown_planet_returns_404(client: TestClient) -> None:
    resp = client.get(f"{BASE}/planets/fantasma/ecology")
    assert resp.status_code == 404


def test_job_status_endpoint_reports_unknown_job(client: TestClient) -> None:
    resp = client.get(f"{BASE}/jobs/nao-existe")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_async_backend_returns_a_job_reference_instead_of_the_result() -> None:
    """Caminho ARQ (202): a era fecha, mas a biologia fica pendente no job.

    Usa um duplo da porta `JobQueue` — o que se verifica aqui é o CONTRATO do
    caso de uso no modo assíncrono, não o transporte Redis (esse tem teste
    próprio, com Testcontainers).
    """
    repo = InMemoryPlanetRepository()
    await CreatePlanetUseCase(repo, PARAMS).execute(PlanetSeed("async", 12))

    class _StubQueue:
        def __init__(self) -> None:
            self.enqueued: list[tuple[str, dict[str, Any]]] = []

        async def enqueue(self, job_name: str, payload: dict[str, Any]) -> JobRef:
            self.enqueued.append((job_name, payload))
            return JobRef(job_id="job-1", job_name=job_name)

        async def get_status(self, job_id: str) -> JobResult | None:
            return JobResult(job_id=job_id, job_name="run_evolution", status=JobStatus.PENDING)

    queue = _StubQueue()
    use_case = AdvanceEraUseCase(
        repo,
        build_orchestrator(PARAMS),
        ExplainCausalUseCase(build_engine(Path("configs/causal_rules.yaml"))),
        PARAMS.timeline.era_length,
        queue,
        biology_enabled=True,
        resolves_inline=False,  # backend ARQ
    )

    outcome = await use_case.execute("async")

    assert queue.enqueued == [("run_evolution", {"planet_id": "async", "era": 1})]
    assert outcome.job is not None and outcome.job.job_id == "job-1"
    assert outcome.biology is None  # ainda pendente: a rota responderá 202
    # A era determinística, porém, JÁ está fechada e persistida.
    assert outcome.end_tick == PARAMS.timeline.era_length
    assert await repo.load_checkpoint("async", 1) is not None
