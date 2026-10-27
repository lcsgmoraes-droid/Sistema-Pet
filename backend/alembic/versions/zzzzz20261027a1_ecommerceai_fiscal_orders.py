"""Pedidos fiscais externos e consentimento Amazon, com isolamento obrigatório."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzz20261027a1"
down_revision = "zzzzy20261026a1"
branch_labels = None
depends_on = None
TABLES = (
    "ecommerceai_fiscal_accounts",
    "ecommerceai_fiscal_sku_mappings",
    "ecommerceai_fiscal_orders",
)


def base():
    return [
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
    ]


def upgrade():
    op.create_table(
        TABLES[0],
        *base(),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("seller_id", sa.String(80), nullable=False),
        sa.Column("marketplace_id", sa.String(80), nullable=False),
        sa.Column("emitter_cnpj", sa.String(14), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("auto_issue_enabled", sa.Boolean(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("discount_policy", sa.String(40), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "channel", "seller_id", name="uq_eai_fiscal_seller"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_eai_fiscal_account_tenant"),
        sa.CheckConstraint(
            "discount_policy IN ('source_discounts','buyer_payment_total')",
            name="ck_eai_fiscal_policy",
        ),
        sa.CheckConstraint("channel = 'amazon'", name="ck_eai_fiscal_channel"),
    )
    op.create_table(
        TABLES[1],
        *base(),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("seller_sku", sa.String(100), nullable=False),
        sa.Column(
            "product_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "account_id"], [TABLES[0] + ".tenant_id", TABLES[0] + ".id"]
        ),
        sa.UniqueConstraint(
            "tenant_id", "account_id", "seller_sku", name="uq_eai_fiscal_sku"
        ),
    )
    op.create_table(
        TABLES[2],
        *base(),
        sa.Column("account_id", sa.Integer()),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("ecommerceai_connections.id"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("seller_id", sa.String(80), nullable=False),
        sa.Column("external_order_id", sa.String(80), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("historical_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by_user_id", sa.Integer()),
        sa.Column("payload", sa.JSON()),
        sa.Column("payload_hash", sa.String(64)),
        sa.Column("discount_audit", sa.JSON()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.String(36)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("correlation_id", sa.String(128)),
        sa.Column("numero", sa.String(20)),
        sa.Column("chave", sa.String(44)),
        sa.Column("protocolo", sa.String(128)),
        sa.Column("xml", sa.LargeBinary()),
        sa.Column("xml_sha256", sa.String(64)),
        sa.ForeignKeyConstraint(
            ["tenant_id", "account_id"], [TABLES[0] + ".tenant_id", TABLES[0] + ".id"]
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "channel",
            "seller_id",
            "external_order_id",
            name="uq_eai_fiscal_order_identity",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_eai_fiscal_idempotency"),
        sa.CheckConstraint("source_revision > 0", name="ck_eai_fiscal_revision"),
        sa.CheckConstraint(
            "status IN ('blocked','ready','processing','unknown','authorized','rejected','canceled')",
            name="ck_eai_fiscal_status",
        ),
    )
    for table in TABLES:
        op.create_index("ix_" + table + "_tenant_id", table, ["tenant_id"])
    op.create_index(
        "ix_eai_fiscal_order_queue", TABLES[2], ["tenant_id", "status", "lease_until"]
    )
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLES, enable=True)


def downgrade():
    bind = op.get_bind()
    op.execute("SET LOCAL row_security = off")
    for table in TABLES:
        if bind.execute(sa.text("SELECT 1 FROM " + table + " LIMIT 1")).first():
            raise RuntimeError(
                "Existem configurações ou documentos fiscais externos; preserve o histórico."
            )
    for table in reversed(TABLES):
        op.drop_table(table)
