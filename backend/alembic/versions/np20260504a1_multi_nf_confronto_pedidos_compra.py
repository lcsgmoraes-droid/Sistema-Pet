"""allow multiple entry invoices per purchase order confrontation

Revision ID: np20260504a1
Revises: mo20260503a1
Create Date: 2026-05-04 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "np20260504a1"
down_revision = "mo20260503a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pedidos_compra_notas_entrada",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pedido_compra_id", sa.Integer(), nullable=False),
        sa.Column("nota_entrada_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pedido_compra_id"], ["pedidos_compra.id"]),
        sa.ForeignKeyConstraint(["nota_entrada_id"], ["notas_entrada.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "pedido_compra_id", "nota_entrada_id", name="uq_pedido_compra_nota_entrada"),
    )
    op.create_index(op.f("ix_pedidos_compra_notas_entrada_id"), "pedidos_compra_notas_entrada", ["id"], unique=False)
    op.create_index(op.f("ix_pedidos_compra_notas_entrada_tenant_id"), "pedidos_compra_notas_entrada", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_pedidos_compra_notas_entrada_pedido_compra_id"), "pedidos_compra_notas_entrada", ["pedido_compra_id"], unique=False)
    op.create_index(op.f("ix_pedidos_compra_notas_entrada_nota_entrada_id"), "pedidos_compra_notas_entrada", ["nota_entrada_id"], unique=False)
    op.create_index(op.f("ix_pedidos_compra_notas_entrada_user_id"), "pedidos_compra_notas_entrada", ["user_id"], unique=False)

    op.execute(
        """
        INSERT INTO pedidos_compra_notas_entrada
            (tenant_id, pedido_compra_id, nota_entrada_id, user_id, created_at, updated_at)
        SELECT DISTINCT
            tenant_id, id, nota_entrada_id, user_id, COALESCE(data_confronto, now()), now()
        FROM pedidos_compra
        WHERE nota_entrada_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pedidos_compra_notas_entrada_user_id"), table_name="pedidos_compra_notas_entrada")
    op.drop_index(op.f("ix_pedidos_compra_notas_entrada_nota_entrada_id"), table_name="pedidos_compra_notas_entrada")
    op.drop_index(op.f("ix_pedidos_compra_notas_entrada_pedido_compra_id"), table_name="pedidos_compra_notas_entrada")
    op.drop_index(op.f("ix_pedidos_compra_notas_entrada_tenant_id"), table_name="pedidos_compra_notas_entrada")
    op.drop_index(op.f("ix_pedidos_compra_notas_entrada_id"), table_name="pedidos_compra_notas_entrada")
    op.drop_table("pedidos_compra_notas_entrada")
