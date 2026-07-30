"""schema simulation: códex de espécies (biologia emergente do Inc 3)

Revision ID: 0003
Revises: 0002
Create Date: incremento de ecossistemas / IA emergente

`species` é a projeção CORRENTE do códex (upsert por espécie): genoma, linhagem,
população e aptidão. A HISTÓRIA de especiação/extinção não ganha tabela própria —
ela já vive no `event_log` append-only criado na 0002, com `event_type` igual a
'speciation'/'extinction'. Manter um único log de eventos preserva a ordenação
temporal entre fatos físicos e biológicos, que é o que o replay percorre
(ADR 0004/0006).
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS simulation")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation.species (
            id           bigserial PRIMARY KEY,
            planet_id    text NOT NULL,
            species_id   text NOT NULL,
            genome       jsonb NOT NULL,
            emerged_era  integer NOT NULL,
            extinct_era  integer,
            ancestor_id  text,
            population   double precision NOT NULL DEFAULT 0,
            fitness      double precision NOT NULL DEFAULT 0,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT species_planet_species_uniq UNIQUE (planet_id, species_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS species_planet_idx ON simulation.species (planet_id)"
    )
    # Consulta mais frequente do códex: "quem está vivo neste planeta?".
    op.execute(
        "CREATE INDEX IF NOT EXISTS species_living_idx "
        "ON simulation.species (planet_id) WHERE extinct_era IS NULL"
    )
    # Navegação da árvore filogenética (linhagem) exibida no códex.
    op.execute(
        "CREATE INDEX IF NOT EXISTS species_ancestor_idx "
        "ON simulation.species (planet_id, ancestor_id)"
    )
    # Os eventos biológicos reutilizam o event_log da 0002; este índice parcial
    # acelera a leitura por tipo ao reconstruir a biologia de uma era.
    op.execute(
        "CREATE INDEX IF NOT EXISTS event_log_type_idx "
        "ON simulation.event_log (planet_id, event_type, tick)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS simulation.event_log_type_idx")
    op.execute("DROP TABLE IF EXISTS simulation.species")
