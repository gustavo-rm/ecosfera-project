"""O serviço sobe e roda a física INTEIRA sem o extra `sim` instalado.

O `sim` (`mesa`, `deap`, `scipy`, `networkx`) é declarado **opcional** no
`pyproject.toml`, e o walking skeleton depende disso: sem o extra, o serviço roda
com adaptadores in-memory. Mas "opcional" só é verdade se algo verificar — e o
M3 encontrou que não era.

`simulation_engine/params.py` importa `EvolutionParams` de
`biology/evolution.py`, que fazia `from deap import ...` no topo. Como
`engines/composition.py` importa `params.py`, a cadeia tornava o `deap` requisito
de importação de TODA a física: o serviço não subia sem o extra. A fábrica
`_deap()` desfaz isso (ADR 0017).

## Por que subprocesso

Bloquear o import no processo do pytest exigiria expurgar `ecosfera_ai` do
`sys.modules` para forçar a reimportação — e isso reexecuta o registro de
métricas do Prometheus, que falha com `Duplicated timeseries`. O defeito seria do
teste, não do código. Um interpretador novo é a única forma honesta de afirmar
"importa do zero sem o extra".
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

BLOCKER = """
import builtins, sys
BLOCKED = {"mesa", "deap", "scipy", "networkx"}
_real = builtins.__import__
def _guard(name, *a, **k):
    if name.split(".")[0] in BLOCKED:
        raise ImportError("No module named %r (extra 'sim' ausente)" % name.split(".")[0])
    return _real(name, *a, **k)
builtins.__import__ = _guard
"""


def _run_without_sim(body: str) -> subprocess.CompletedProcess[str]:
    """Roda `body` num interpretador onde o extra `sim` não existe."""
    return subprocess.run(
        [sys.executable, "-c", BLOCKER + textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_the_blocker_actually_blocks() -> None:
    """Contraprova do mecanismo: sem ela o resto seria vacuamente verde."""
    done = _run_without_sim(
        """
        try:
            import mesa
        except ImportError:
            print("BLOQUEADO")
        else:
            print("PASSOU")
        """
    )
    assert "BLOQUEADO" in done.stdout, done.stderr


def test_the_engine_framework_imports_without_the_sim_extra() -> None:
    """A importação da moldura não pode arrastar `deap` nem `mesa`."""
    done = _run_without_sim(
        """
        from ecosfera_ai.engines.composition import ENGINE_ORDER, build_planet_engine
        assert len(ENGINE_ORDER) == 10, ENGINE_ORDER
        import sys
        assert "deap" not in sys.modules and "mesa" not in sys.modules
        print("IMPORTOU", len(ENGINE_ORDER))
        """
    )
    assert done.returncode == 0, done.stderr
    assert "IMPORTOU 10" in done.stdout


def test_the_whole_tick_runs_without_the_sim_extra() -> None:
    """E rodar, não só importar: os nove Engines produzem um planeta vivo."""
    done = _run_without_sim(
        """
        from pathlib import Path
        from ecosfera_ai.engines.bridge import snapshot_of
        from ecosfera_ai.engines.composition import build_planet_engine
        from ecosfera_ai.simulation_engine.params import initial_state, load_params
        from ecosfera_ai.simulation_engine.state import PlanetSeed

        params = load_params(Path("configs/simulation_params.yaml"))
        planet = build_planet_engine(params, budget=params.engine_budget)
        snapshot = snapshot_of(initial_state(PlanetSeed("nosim", 2027), params))
        for _ in range(120):
            snapshot = planet.tick(snapshot, publish=False).snapshot

        assert snapshot.tick == 120
        assert snapshot.biota.biomass > 0.0, "a vida nao se estabeleceu sem o extra"
        assert snapshot.ecology.producer_biomass > 0.0
        print("RODOU", round(snapshot.biota.biomass, 3))
        """
    )
    assert done.returncode == 0, done.stderr
    assert "RODOU" in done.stdout


def test_the_ecology_engine_needs_no_agent_based_framework() -> None:
    """O Ecology PORTA a ciência do ABM; não o envolve.

    Envolvê-lo exigiria materializar a lista de espécies a cada tick só para
    agregá-la de volta em três níveis tróficos — que é tudo o que cabe no
    Canal A. O ABM com `mesa` segue vivo no caminho por era (ADR 0017).
    """
    done = _run_without_sim(
        """
        from ecosfera_ai.engines.ecology.service import EcologyEngine
        assert EcologyEngine().engine_id == "ecology"
        print("ECOLOGY OK")
        """
    )
    assert done.returncode == 0, done.stderr
    assert "ECOLOGY OK" in done.stdout


def test_the_legacy_biology_still_needs_the_extra_and_says_so() -> None:
    """O contraponto honesto: o AG por era CONTINUA exigindo o `deap`.

    O que mudou é QUANDO ele é exigido — na execução, não na importação. Sem esta
    afirmação, alguém poderia concluir que o extra virou supérfluo.
    """
    done = _run_without_sim(
        """
        from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine, _deap
        try:
            _deap()
        except ImportError:
            print("EXIGE O EXTRA")
        else:
            print("NAO EXIGE")
        """
    )
    assert done.returncode == 0, done.stderr
    assert "EXIGE O EXTRA" in done.stdout
