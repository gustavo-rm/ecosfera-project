"""Seleção do adaptador de persistência por feature flag (composition root).

Não precisa de banco: `create_async_engine` é preguiçoso — só conecta na primeira
consulta —, então dá para verificar o *wiring* da flag sem infraestrutura.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from ecosfera_ai.config.settings import get_settings
from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import InMemoryPlanetRepository
from ecosfera_ai.interfaces.http.deps import get_planet_repo


@pytest.fixture(autouse=True)
def _clear_caches() -> Iterator[None]:
    """Isola o teste: settings e adaptador são singletons memoizados."""
    get_settings.cache_clear()
    get_planet_repo.cache_clear()
    yield
    get_settings.cache_clear()
    get_planet_repo.cache_clear()


def test_default_backend_is_inmemory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ECOSFERA_PERSISTENCE_BACKEND", raising=False)
    assert isinstance(get_planet_repo(), InMemoryPlanetRepository)


def test_postgres_backend_is_selected_by_the_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("sqlalchemy", reason="extra `infra` não instalado")
    from ecosfera_ai.infrastructure.persistence.postgres_planet_repo import (
        PostgresPlanetRepository,
    )

    monkeypatch.setenv("ECOSFERA_PERSISTENCE_BACKEND", "postgres")
    monkeypatch.setenv(
        "ECOSFERA_DATABASE_URL", "postgresql+asyncpg://ecosfera:ecosfera@localhost:5432/ecosfera"
    )
    assert isinstance(get_planet_repo(), PostgresPlanetRepository)


def test_unknown_backend_falls_back_to_inmemory(monkeypatch: pytest.MonkeyPatch) -> None:
    # Falha segura: um valor inválido não derruba o serviço nem vaza para produção
    # silenciosamente com um adaptador pela metade.
    monkeypatch.setenv("ECOSFERA_PERSISTENCE_BACKEND", "cassandra")
    assert isinstance(get_planet_repo(), InMemoryPlanetRepository)
