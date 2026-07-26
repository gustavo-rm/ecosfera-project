"""schema simulation: planetas, checkpoints de era e log de eventos

Revision ID: 0002
Revises: 0001
Create Date: incremento de timeline/persistência

Suporta o event-sourcing-lite do núcleo determinístico (ADR 0004/0005):
`planets` guarda a projeção do estado corrente (upsert), enquanto
`era_checkpoints` e `event_log` são append-only — nunca sofrem UPDATE/DELETE em
operação normal, o que preserva a auditabilidade da trajetória (Dossiê §9).
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Redundância segura: em dev o initdb já criou os schemas; em bancos
    # efêmeros (Testcontainers) esta é a única criação.
    op.execute("CREATE SCHEMA IF NOT EXISTS simulation")

    # Projeção do estado corrente do planeta (uma linha por planeta).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation.planets (
            planet_id   text PRIMARY KEY,
            seed        bigint NOT NULL,
            tick        integer NOT NULL,
            state       jsonb NOT NULL,
            created_at  timestamptz NOT NULL DEFAULT now(),
            updated_at  timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    # Histórico append-only de eras. A unicidade (planet_id, era) torna a
    # gravação idempotente e impede reescrever uma era já fechada.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation.era_checkpoints (
            id          bigserial PRIMARY KEY,
            planet_id   text NOT NULL,
            era         integer NOT NULL,
            seed        bigint NOT NULL,
            start_tick  integer NOT NULL,
            end_tick    integer NOT NULL,
            state       jsonb NOT NULL,
            created_at  timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT era_checkpoints_planet_era_uniq UNIQUE (planet_id, era)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS era_checkpoints_planet_idx "
        "ON simulation.era_checkpoints (planet_id, era)"
    )

    # Log append-only de eventos (intervenções do aluno e marcos narrativos).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation.event_log (
            id          bigserial PRIMARY KEY,
            planet_id   text NOT NULL,
            tick        integer NOT NULL,
            event_type  text NOT NULL,
            payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at  timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS event_log_planet_tick_idx "
        "ON simulation.event_log (planet_id, tick)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS simulation.event_log")
    op.execute("DROP TABLE IF EXISTS simulation.era_checkpoints")
    op.execute("DROP TABLE IF EXISTS simulation.planets")
