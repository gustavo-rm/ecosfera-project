"""baseline do schema rag: tabela de embeddings do RAG (pgvector)

Revision ID: 0001
Revises:
Create Date: baseline
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Dimensão do embedding. Ajuste conforme o modelo de sentence-transformers usado
# (ex.: all-mpnet-base-v2 = 768; all-MiniLM-L6-v2 = 384).
EMBED_DIM = 768


def upgrade() -> None:
    # Redundância segura: no dev o init do container já criou o schema/extensão.
    op.execute("CREATE SCHEMA IF NOT EXISTS rag")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag.embedding (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_type  text NOT NULL,            -- 'curriculum' | 'planet_state' | ...
            source_id    text NOT NULL,
            chunk_index  integer NOT NULL DEFAULT 0,
            content      text NOT NULL,
            embedding    vector({EMBED_DIM}) NOT NULL,
            metadata     jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            created_at   timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    # Índice ANN por similaridade de cosseno (HNSW).
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS embedding_vector_idx
        ON rag.embedding USING hnsw (embedding vector_cosine_ops)
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS embedding_source_idx "
        "ON rag.embedding (source_type, source_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rag.embedding")
