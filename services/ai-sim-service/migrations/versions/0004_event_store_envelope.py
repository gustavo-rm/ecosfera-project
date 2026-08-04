"""Event Store completo: o envelope §4 vira COLUNA, não só payload (M5).

Revision ID: 0004
Revises: 0003
Create Date: M5

O M2 criou `simulation.event_log` com o mínimo — `planet_id, tick, event_type,
payload`. Servia à linha do tempo e não serve ao Event Store: o envelope §4
(cause_code, correlation_id, causation_id, era, engine_id, granularity) ficava
inteiro dentro do JSONB, o que torna impossível indexar por correlação ou por
causa sem varrer a tabela.

ESTENDE o schema do M2 em vez de criar um segundo mecanismo (ADR 0021). As
colunas novas são NULLABLE de propósito: as linhas que o M2 já gravou continuam
válidas, sem backfill e sem downtime — elas simplesmente não têm envelope, que é
a verdade sobre elas.

Append-only, como o resto da linha do tempo: nunca UPDATE nem DELETE em operação
normal, o que preserva a auditabilidade (Dossiê §9).
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS simulation")

    # O envelope §4, coluna a coluna. `IF NOT EXISTS` mantém a migration
    # idempotente — reaplicá-la num banco parcialmente migrado não quebra.
    for column, ddl in (
        ("event_id", "text"),
        ("engine_id", "text"),
        ("era", "integer"),
        ("seed", "bigint"),
        ("cause_code", "text"),
        ("correlation_id", "text"),
        ("causation_id", "text"),
        ("granularity", "text"),
    ):
        op.execute(f"ALTER TABLE simulation.event_log ADD COLUMN IF NOT EXISTS {column} {ddl}")

    # Índices que sustentam o contrato de query do M6 (EventQuery):
    #
    #  - por planeta/era/tick: a leitura da visão científica, sempre ordenada por
    #    tempo de simulação;
    #  - por correlation_id: agrupa tudo que aconteceu no MESMO tick, que é como
    #    a cadeia causal é reconstruída;
    #  - por causation_id: sobe a cadeia efeito -> causa (Meteoro -> Extinção);
    #  - por cause_code: "quantas extinções catastróficas houve?" sem varredura.
    op.execute(
        "CREATE INDEX IF NOT EXISTS event_log_planet_era_tick_idx "
        "ON simulation.event_log (planet_id, era, tick)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS event_log_correlation_idx "
        "ON simulation.event_log (correlation_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS event_log_causation_idx "
        "ON simulation.event_log (causation_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS event_log_cause_code_idx "
        "ON simulation.event_log (planet_id, cause_code)"
    )

    # `event_id` é determinístico (uuid5 sobre seed/engine/tick/sequência), então
    # reprocessar a mesma corrida não pode duplicar a trilha. O índice único é o
    # que torna a idempotência uma propriedade do BANCO, e não da disciplina de
    # quem escreve.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS event_log_event_id_key "
        "ON simulation.event_log (event_id) WHERE event_id IS NOT NULL"
    )


def downgrade() -> None:
    for index in (
        "event_log_event_id_key",
        "event_log_cause_code_idx",
        "event_log_causation_idx",
        "event_log_correlation_idx",
        "event_log_planet_era_tick_idx",
    ):
        op.execute(f"DROP INDEX IF EXISTS simulation.{index}")
    for column in (
        "granularity",
        "causation_id",
        "correlation_id",
        "cause_code",
        "seed",
        "era",
        "engine_id",
        "event_id",
    ):
        op.execute(f"ALTER TABLE simulation.event_log DROP COLUMN IF EXISTS {column}")
