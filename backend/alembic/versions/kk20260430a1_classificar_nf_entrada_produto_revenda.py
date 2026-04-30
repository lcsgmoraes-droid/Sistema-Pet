"""classificar contas de nf entrada como produto para revenda

Revision ID: kk20260430a1
Revises: jj20260429a2
Create Date: 2026-04-30 00:30:00.000000
"""

from alembic import op


revision = "kk20260430a1"
down_revision = "jj20260429a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE contas_pagar cp
        SET tipo_despesa_id = td.id
        FROM tipo_despesas td
        WHERE cp.nota_entrada_id IS NOT NULL
          AND cp.tipo_despesa_id IS NULL
          AND td.tenant_id = cp.tenant_id
          AND td.ativo IS TRUE
          AND lower(td.nome) IN (
            'produto para revenda',
            'fornecedor de produto para revenda'
          )
        """
    )


def downgrade() -> None:
    pass
