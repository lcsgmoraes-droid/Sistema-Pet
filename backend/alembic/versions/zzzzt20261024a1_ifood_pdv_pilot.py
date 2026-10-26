"""Ponte DEV dos pedidos de teste iFood para reserva e venda.

Revision ID: zzzzt20261024a1
Revises: zzzzs20261023a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzt20261024a1"
down_revision = "zzzzs20261023a1"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "pedidos_integrados",
        "pedido_bling_id",
        existing_type=sa.String(50),
        nullable=True,
    )
    op.create_unique_constraint(
        "uq_pedidos_integrados_tenant_id", "pedidos_integrados", ["tenant_id", "id"]
    )
    op.create_table(
        "ifood_pdv_bridges",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("ifood_order_id", sa.String(64), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("stock_decreased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "ifood_order_id", name="uq_ifood_pdv_order"),
        sa.UniqueConstraint("tenant_id", "sale_id", name="uq_ifood_pdv_sale"),
        sa.UniqueConstraint(
            "tenant_id", "reservation_id", name="uq_ifood_pdv_reservation"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "ifood_order_id"],
            ["ifood_orders.tenant_id", "ifood_orders.ifood_order_id"],
            name="fk_ifood_pdv_order",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "sale_id"],
            ["vendas.tenant_id", "vendas.id"],
            name="fk_ifood_pdv_sale",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "reservation_id"],
            ["pedidos_integrados.tenant_id", "pedidos_integrados.id"],
            name="fk_ifood_pdv_reservation",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["produtos.tenant_id", "produtos.id"],
            name="fk_ifood_pdv_product",
        ),
        sa.CheckConstraint(
            "status IN ('reserved','sold','cancelled')", name="ck_ifood_pdv_status"
        ),
        sa.CheckConstraint("quantity = 1", name="ck_ifood_pdv_one_unit"),
        sa.CheckConstraint("unit_price > 0", name="ck_ifood_pdv_positive_price"),
    )
    op.create_index(
        "ix_ifood_pdv_bridges_tenant_id", "ifood_pdv_bridges", ["tenant_id"]
    )
    apply_tenant_rls(
        op_module=op, sa_module=sa, table_names=("ifood_pdv_bridges",), enable=True
    )


def downgrade():
    # A reversao nao pode apagar a evidencia do piloto nem inventar IDs Bling.
    bind = op.get_bind()
    # Falha fechado se o operador nao puder enxergar dados protegidos por RLS;
    # nao aceitar uma tabela aparentemente vazia por falta de contexto de tenant.
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("SET LOCAL row_security = off"))
    if bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM ifood_pdv_bridges) OR EXISTS (SELECT 1 FROM pedidos_integrados WHERE pedido_bling_id IS NULL)"
        )
    ).scalar():
        raise RuntimeError(
            "Preserve os pedidos e vinculos iFood: downgrade com dados nao e permitido."
        )
    op.drop_table("ifood_pdv_bridges")
    op.drop_constraint(
        "uq_pedidos_integrados_tenant_id", "pedidos_integrados", type_="unique"
    )
    op.alter_column(
        "pedidos_integrados",
        "pedido_bling_id",
        existing_type=sa.String(50),
        nullable=False,
    )
