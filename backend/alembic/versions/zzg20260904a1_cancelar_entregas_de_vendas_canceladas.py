"""cancela entregas vinculadas a vendas canceladas

Revision ID: zzg20260904a1
Revises: zzf20260903a1
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "zzg20260904a1"
down_revision = "zzf20260903a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE vendas
               SET status_entrega = 'cancelada',
                   ordem_entrega_otimizada = NULL
             WHERE status = 'cancelada'
               AND tem_entrega = TRUE
               AND (
                    status_entrega IS NULL
                    OR status_entrega <> 'cancelada'
                    OR ordem_entrega_otimizada IS NOT NULL
               )
            """
        )
    )


def downgrade() -> None:
    # O estado anterior da entrega nao e recuperavel com seguranca. A venda
    # continua cancelada e, portanto, deve permanecer fora da operacao.
    pass
