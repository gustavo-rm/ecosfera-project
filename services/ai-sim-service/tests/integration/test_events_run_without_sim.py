"""Sem o extra `sim`: as perturbações FÍSICAS aplicam; a biologia fica de fora.

O `sim` (`mesa`, `deap`, `scipy`, `networkx`) é opcional, e o M3 tornou isso
verdadeiro e verificado. O M4 não pode desfazer: o Event Engine e o Diretor são
aritmética e RNG semeado, e nada no catálogo de eventos precisa de framework.

O subprocesso é necessário — bloquear o import no processo do pytest exigiria
expurgar `ecosfera_ai` do `sys.modules`, o que reexecuta o registro de métricas
do Prometheus e falha por conta do teste, não do código (ADR 0017).
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

BLOCKER = """
import builtins
BLOCKED = {"mesa", "deap", "scipy", "networkx"}
_real = builtins.__import__
def _guard(name, *a, **k):
    if name.split(".")[0] in BLOCKED:
        raise ImportError("No module named %r (extra 'sim' ausente)" % name.split(".")[0])
    return _real(name, *a, **k)
builtins.__import__ = _guard
"""


def _run(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", BLOCKER + textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_the_event_engine_imports_without_the_sim_extra() -> None:
    done = _run(
        """
        from ecosfera_ai.engines.event.service import EventEngine
        from ecosfera_ai.engines.event.director import decide
        from ecosfera_ai.engines.composition import ENGINE_ORDER
        assert ENGINE_ORDER[-1] == "event"
        import sys
        assert "mesa" not in sys.modules and "deap" not in sys.modules
        print("IMPORTOU")
        """
    )
    assert done.returncode == 0, done.stderr
    assert "IMPORTOU" in done.stdout


def test_the_physical_perturbations_apply_without_the_sim_extra() -> None:
    """Um meteoro esfria o planeta mesmo sem o extra instalado."""
    done = _run(
        """
        import sys; sys.path.insert(0, "tests")
        from pathlib import Path
        from ecosfera_ai.engines.bridge import snapshot_of
        from ecosfera_ai.shared_kernel.world_state import EventSlice, SliceRef
        from ecosfera_ai.simulation_engine.params import initial_state, load_params
        from ecosfera_ai.simulation_engine.state import PlanetSeed
        from support import build_quiet_planet

        params = load_params(Path("configs/simulation_params.yaml"))
        planet = build_quiet_planet()
        s = snapshot_of(initial_state(PlanetSeed("nosim-m4", 2027), params))
        for _ in range(120):
            s = planet.tick(s, publish=False).snapshot

        calm = planet.tick(s, publish=False).snapshot
        struck = planet.tick(
            s.with_slice(SliceRef.EVENT, EventSlice(cooling_forcing=6.0, dust_load=0.5)),
            publish=False,
        ).snapshot
        assert struck.climate.temperature < calm.climate.temperature, "o meteoro nao esfriou"
        print("PERTURBOU", round(calm.climate.temperature - struck.climate.temperature, 4))
        """
    )
    assert done.returncode == 0, done.stderr
    assert "PERTURBOU" in done.stdout


def test_the_director_schedules_without_the_sim_extra() -> None:
    done = _run(
        """
        import sys; sys.path.insert(0, "tests")
        from pathlib import Path
        from ecosfera_ai.engines.bridge import snapshot_of
        from ecosfera_ai.engines.composition import build_planet_engine
        from ecosfera_ai.simulation_engine.params import initial_state, load_params
        from ecosfera_ai.simulation_engine.state import PlanetSeed

        params = load_params(Path("configs/simulation_params.yaml"))
        planet = build_planet_engine(params, budget=params.engine_budget)
        s = snapshot_of(initial_state(PlanetSeed("nosim-director", 2027), params))
        seen = False
        for _ in range(400):
            s = planet.tick(s, publish=False).snapshot
            seen = seen or bool(s.event.active_kind)
        assert seen, "o Diretor nao agendou nada sem o extra"
        print("AGENDOU")
        """
    )
    assert done.returncode == 0, done.stderr
    assert "AGENDOU" in done.stdout


def test_the_legacy_biology_still_needs_the_extra() -> None:
    """O contraponto honesto: o caminho B dormente continua exigindo o `deap`."""
    done = _run(
        """
        from ecosfera_ai.simulation_engine.biology.evolution import _deap
        try:
            _deap()
        except ImportError:
            print("EXIGE O EXTRA")
        """
    )
    assert done.returncode == 0, done.stderr
    assert "EXIGE O EXTRA" in done.stdout
