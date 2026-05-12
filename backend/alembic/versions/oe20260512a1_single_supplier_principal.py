"""mark single active supplier links as principal

Revision ID: oe20260512a1
Revises: od20260511a1
Create Date: 2026-05-12 19:35:00.000000
"""

from alembic import op


revision = "oe20260512a1"
down_revision = "od20260511a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH unicos AS (
            SELECT
                produto_id,
                tenant_id,
                MIN(id) AS vinculo_id,
                MIN(fornecedor_id) AS fornecedor_id
            FROM produto_fornecedores
            WHERE ativo IS TRUE
            GROUP BY produto_id, tenant_id
            HAVING COUNT(*) = 1
        )
        UPDATE produto_fornecedores pf
        SET
            e_principal = TRUE,
            updated_at = NOW()
        FROM unicos u
        WHERE pf.id = u.vinculo_id
          AND (pf.e_principal IS DISTINCT FROM TRUE)
        """
    )
    op.execute(
        """
        WITH unicos AS (
            SELECT
                produto_id,
                tenant_id,
                MIN(fornecedor_id) AS fornecedor_id
            FROM produto_fornecedores
            WHERE ativo IS TRUE
            GROUP BY produto_id, tenant_id
            HAVING COUNT(*) = 1
        )
        UPDATE produtos p
        SET
            fornecedor_id = u.fornecedor_id,
            updated_at = NOW()
        FROM unicos u
        WHERE p.id = u.produto_id
          AND p.tenant_id = u.tenant_id
          AND (p.fornecedor_id IS DISTINCT FROM u.fornecedor_id)
        """
    )


def downgrade() -> None:
    # Data normalization only. Do not unset supplier principals on downgrade.
    pass
