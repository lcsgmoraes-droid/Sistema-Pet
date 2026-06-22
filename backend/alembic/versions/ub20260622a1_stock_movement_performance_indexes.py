"""add stock movement performance indexes

Revision ID: ub20260622a1
Revises: ua20260621a1
Create Date: 2026-06-22 14:55:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ub20260622a1"
down_revision: Union[str, Sequence[str], None] = "ua20260621a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_estoque_mov_tenant_produto_created
        ON estoque_movimentacoes (tenant_id, produto_id, created_at, id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_estoque_mov_tenant_documento_motivo
        ON estoque_movimentacoes (tenant_id, documento, motivo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_estoque_mov_tenant_motivo_created
        ON estoque_movimentacoes (tenant_id, motivo, created_at, id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_bling_nf_cache_tenant_pedido_ref
        ON bling_notas_fiscais_cache (
            tenant_id,
            pedido_bling_id_ref,
            data_emissao,
            last_synced_at,
            id
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_bling_nf_cache_tenant_numero_loja
        ON bling_notas_fiscais_cache (
            tenant_id,
            numero_pedido_loja,
            data_emissao,
            last_synced_at,
            id
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bling_nf_cache_tenant_numero_loja")
    op.execute("DROP INDEX IF EXISTS ix_bling_nf_cache_tenant_pedido_ref")
    op.execute("DROP INDEX IF EXISTS ix_estoque_mov_tenant_motivo_created")
    op.execute("DROP INDEX IF EXISTS ix_estoque_mov_tenant_documento_motivo")
    op.execute("DROP INDEX IF EXISTS ix_estoque_mov_tenant_produto_created")
