"""Erros de aplicação da simulação — módulo LEVE, sem dependência científica.

Existe para desfazer uma inversão de camadas que quebrava o boot. `core/errors.py`
registra os handlers HTTP e precisava de `SpeciesNotFoundError`; a classe morava
em `evolve_biology.py`, que importa `BiologyEngine`, que importa `ecology.py`, que
importava `mesa` no topo. Resultado: **registrar um handler de 404 exigia o extra
`sim` instalado**, e sem ele `create_app()` levantava `ModuleNotFoundError`.

Uma classe de exceção de três linhas não pode arrastar um framework de simulação
por agente atrás de si. Este módulo não importa nada além do necessário, e é a
raiz que `core/errors.py` passa a consumir (ADR 0017).
"""

from __future__ import annotations


class SpeciesNotFoundError(Exception):
    """Espécie inexistente no códex do planeta (HTTP 404)."""
