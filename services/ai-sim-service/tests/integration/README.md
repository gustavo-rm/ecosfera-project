# Integration tests

Tests that exercise real adapters (Postgres/pgvector, MongoDB, Redis) against
the docker-compose dev stack (`infra/compose/dev.yml`), as opposed to the
in-memory unit tests in `tests/unit/`.
