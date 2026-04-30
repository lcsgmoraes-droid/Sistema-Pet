"""renomear tipo de despesa produto para revenda

Revision ID: kk20260430a3
Revises: kk20260430a2
Create Date: 2026-04-30 00:40:00.000000
"""

from alembic import op


revision = "kk20260430a3"
down_revision = "kk20260430a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE tipo_despesas
        SET nome = 'Produto para Revenda'
        WHERE lower(nome) = 'fornecedor de produto para revenda'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE tipo_despesas
        SET nome = 'Fornecedor de Produto para Revenda'
        WHERE lower(nome) = 'produto para revenda'
        """
    )
