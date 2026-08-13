"""corpus pedagógico do M6.2: proveniência como invariante de banco

Revision ID: 0006
Revises: 0005
Create Date: M6.2

A migration 0001 criou `rag.embedding` como tabela genérica de baseline
(`source_type`, `source_id`, `metadata jsonb`). Ela nunca teve escritor nem
leitor, e não serve ao M6.2 pelo motivo que decide esta subetapa: proveniência
guardada em `metadata jsonb` é convenção, não invariante — nada impede uma linha
sem origem, e nada impede uma referência externa sem licença.

Este serviço já pagou duas vezes por campos declarados que ninguém exercitava (o
`atmosphere.oxygen` sem escritor, o `EventQuery.planet_id` que não filtrava). Aqui
a regra de proveniência é NOT NULL + CHECK: uma entrada anônima não entra, e uma
`external_reference` sem licença não entra. O banco recusa, e não a disciplina de
quem escreve o YAML.

`rag.embedding` fica INTACTA e continua sem uso. Removê-la é decisão própria — ela
é baseline de um plano anterior — mas fica registrado que ela é candidata a
remoção, para que ninguém a confunda com o corpus de verdade.
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# Dimensão do vetor, alinhada à 0001 (`vector(768)`) e à porta de embedding
# (`EMBEDDING_DIMENSIONS`). Um modelo de outra dimensão falha na construção do
# adaptador, antes de qualquer escrita.
EMBED_DIM = 768

# As quatro categorias do ADR 0027, em ordem de prioridade do corpus.
CATEGORIES = (
    "vocabulary_rule",
    "validated_correction",
    "curriculum_objective",
    "external_reference",
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS rag")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    categories = ", ".join(f"'{name}'" for name in CATEGORIES)
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag.corpus_entry (
            entry_id      text NOT NULL,
            model_name    text NOT NULL,
            category      text NOT NULL CHECK (category IN ({categories})),
            -- Proveniência OBRIGATÓRIA: sem documento de origem a entrada não
            -- entra. É a pergunta "por que o Tutor falou assim?" tendo resposta.
            source        text NOT NULL CHECK (length(btrim(source)) > 0),
            content       text NOT NULL CHECK (length(btrim(content)) > 0),
            topic         text NOT NULL DEFAULT '',
            cause_codes   text[] NOT NULL DEFAULT '{{}}',
            bncc_codes    text[] NOT NULL DEFAULT '{{}}',
            grade_band    text NOT NULL DEFAULT '',
            -- NULL fora de `curriculum_objective`; para objetivos, `false`
            -- preserva o "(conferir)" do Dossiê (código ainda não validado).
            code_verified boolean,
            license       text NOT NULL DEFAULT '',
            embedding     vector({EMBED_DIM}) NOT NULL,
            created_at    timestamptz NOT NULL DEFAULT now(),
            -- A chave inclui o MODELO: o mesmo corpus indexado por dois modelos
            -- coexiste, e nenhuma consulta mistura os dois espaços vetoriais.
            PRIMARY KEY (model_name, entry_id),
            -- Referência externa sem licença é recusada pelo banco. A regra de
            -- direito autoral não é julgamento a relaxar sob pressão de prazo.
            CONSTRAINT external_reference_needs_license CHECK (
                category <> 'external_reference' OR length(btrim(license)) > 0
            )
        )
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS corpus_entry_vector_idx
        ON rag.corpus_entry USING hnsw (embedding vector_cosine_ops)
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS corpus_entry_model_category_idx "
        "ON rag.corpus_entry (model_name, category)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rag.corpus_entry")
