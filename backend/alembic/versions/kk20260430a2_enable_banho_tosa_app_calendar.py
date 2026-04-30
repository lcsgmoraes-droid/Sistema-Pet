"""habilitar calendario do banho e tosa no app

Revision ID: kk20260430a2
Revises: kk20260430a1
Create Date: 2026-04-30 00:35:00.000000
"""

from alembic import op


revision = "kk20260430a2"
down_revision = "kk20260430a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE banho_tosa_configuracoes
        SET mostrar_calendario_cliente = TRUE
        WHERE mostrar_calendario_cliente IS FALSE
        """
    )


def downgrade() -> None:
    pass
