"""add ops scale and purchase filter indexes

Revision ID: ns20260507a1
Revises: nr20260507a1
Create Date: 2026-05-07 13:55:00.000000
"""

from alembic import op


revision = "ns20260507a1"
down_revision = "nr20260507a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_tenant_status_data "
        "ON pedidos_compra (tenant_id, status, data_pedido DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_tenant_fornecedor_data "
        "ON pedidos_compra (tenant_id, fornecedor_id, data_pedido DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_tenant_data "
        "ON pedidos_compra (tenant_id, data_pedido DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_tenant_numero "
        "ON pedidos_compra (tenant_id, numero_pedido)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_produtos_tenant_vendaveis_lookup "
        "ON produtos (tenant_id, ativo, tipo_produto, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_produtos_tenant_codigo_barras "
        "ON produtos (tenant_id, codigo_barras)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_produtos_fornecedores_tenant_fornecedor_ativo "
        "ON produto_fornecedores (tenant_id, fornecedor_id, ativo, produto_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_bling_pedido_webhook_tenant_status_created "
        "ON bling_pedido_webhook_events (tenant_id, status, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_tenant_status_created")
    op.execute("DROP INDEX IF EXISTS ix_produtos_fornecedores_tenant_fornecedor_ativo")
    op.execute("DROP INDEX IF EXISTS ix_produtos_tenant_codigo_barras")
    op.execute("DROP INDEX IF EXISTS ix_produtos_tenant_vendaveis_lookup")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_compra_tenant_numero")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_compra_tenant_data")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_compra_tenant_fornecedor_data")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_compra_tenant_status_data")
