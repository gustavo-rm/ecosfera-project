"""A identidade de evento é única POR PLANETA, não globalmente.

Revision ID: 0005
Revises: 0004
Create Date: correção da dívida do M5

O M4 fixou `event_id = uuid5(seed, era, tick, engine_id, event_type, sequência)`
para que o replay seja bit-a-bit: a mesma trajetória tem de gerar exatamente os
mesmos identificadores (RF-023). Nenhuma das partes é o planeta — e a Spec §4
mantém planeta fora do envelope de propósito.

A consequência só apareceu quando o M6.0 foi montar o primeiro consumidor: DOIS
PLANETAS COM A MESMA SEMENTE PRODUZEM `event_id` IDÊNTICOS. Não parecidos —
iguais, byte a byte, porque a derivação não os distingue.

O índice único da 0004 era global:

    CREATE UNIQUE INDEX event_log_event_id_key ON simulation.event_log (event_id)

Com ele, gravar o segundo planeta de mesma semente VIOLA a restrição: o banco
recusa a corrida inteira do segundo aluno como se fosse reprocessamento do
primeiro. E dois alunos escolhendo a mesma semente não é caso de laboratório — é
o que acontece quando uma turma recebe "usem a semente 2027".

A correção segue a decisão de que planeta é dimensão de ARMAZENAMENTO e não do
fato (ADR 0023): o MESMO fato pode existir em dois planetas, e quem os distingue
é onde estão guardados. Logo a chave é `(planet_id, event_id)`.

A idempotência que a 0004 buscava fica preservada — no grão correto. Reprocessar
a corrida de um planeta continua não podendo duplicar a trilha dele; o que deixa
de acontecer é um planeta bloquear o outro.
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ordem importa: cria a composta ANTES de derrubar a global, para que não
    # exista uma janela sem garantia de unicidade alguma.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS event_log_planet_event_id_key "
        "ON simulation.event_log (planet_id, event_id) WHERE event_id IS NOT NULL"
    )
    op.execute("DROP INDEX IF EXISTS simulation.event_log_event_id_key")


def downgrade() -> None:
    # A volta pode FALHAR legitimamente, e é correto que falhe: se dois planetas
    # de mesma semente já convivem na tabela, a restrição global não é
    # satisfazível e restaurá-la significaria descartar a trilha de um deles.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS event_log_event_id_key "
        "ON simulation.event_log (event_id) WHERE event_id IS NOT NULL"
    )
    op.execute("DROP INDEX IF EXISTS simulation.event_log_planet_event_id_key")
