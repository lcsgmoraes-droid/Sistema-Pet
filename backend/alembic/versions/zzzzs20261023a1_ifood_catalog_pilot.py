"""Vinculos e historico do piloto de um item, com isolamento RLS.

Revision ID: zzzzs20261023a1
Revises: zzzzr20261023a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzs20261023a1"
down_revision = "zzzzr20261023a1"
branch_labels = None
depends_on = None


def _base():
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
    op.create_index(
        "uq_produtos_tenant_id", "produtos", ["tenant_id", "id"], unique=True
    )
    op.create_table(
        "ifood_catalog_links",
        *_base(),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(13), nullable=False),
        sa.Column("mode", sa.String(12), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("portal_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("portal_checked_by", sa.Integer(), nullable=False),
        sa.UniqueConstraint("tenant_id", "id", name="uq_ifood_catalog_link_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "product_id",
            name="uq_ifood_catalog_link_product",
        ),
        sa.UniqueConstraint(
            "tenant_id", "merchant_id", "barcode", name="uq_ifood_catalog_link_barcode"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["produtos.tenant_id", "produtos.id"],
            name="fk_ifood_catalog_link_product",
        ),
        sa.CheckConstraint(
            "mode IN ('existing','new')", name="ck_ifood_catalog_link_mode"
        ),
        sa.CheckConstraint("revision > 0", name="ck_ifood_catalog_link_revision"),
    )
    op.create_table(
        "ifood_catalog_confirmations",
        *_base(),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(13), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("present", sa.Boolean(), nullable=False),
        sa.Column("portal_active", sa.Boolean(), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=True),
        sa.Column("stock", sa.Numeric(14, 3), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "link_id"],
            ["ifood_catalog_links.tenant_id", "ifood_catalog_links.id"],
            name="fk_ifood_catalog_confirmation_link",
        ),
        sa.CheckConstraint(
            "kind IN ('link','portal')", name="ck_ifood_catalog_confirmation_kind"
        ),
        sa.CheckConstraint(
            "price IS NULL OR price >= 0", name="ck_ifood_catalog_confirmation_price"
        ),
        sa.CheckConstraint(
            "stock IS NULL OR stock >= 0", name="ck_ifood_catalog_confirmation_stock"
        ),
    )
    op.create_table(
        "ifood_catalog_submissions",
        *_base(),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("barcode", sa.String(13), nullable=False),
        sa.Column("request_key", sa.String(36), nullable=False),
        sa.Column("operation", sa.String(12), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("provider_request_id", sa.String(36), nullable=True),
        sa.Column("error_code", sa.String(40), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id", "link_id"],
            ["ifood_catalog_links.tenant_id", "ifood_catalog_links.id"],
            name="fk_ifood_catalog_submission_link",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "request_key",
            name="uq_ifood_catalog_submission_request",
        ),
        sa.CheckConstraint(
            "operation IN ('create','update')",
            name="ck_ifood_catalog_submission_operation",
        ),
        sa.CheckConstraint(
            "status IN ('sending','accepted','error','uncertain')",
            name="ck_ifood_catalog_submission_status",
        ),
    )
    for table in (
        "ifood_catalog_links",
        "ifood_catalog_confirmations",
        "ifood_catalog_submissions",
    ):
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        apply_tenant_rls(op_module=op, sa_module=sa, table_names=(table,), enable=True)


def downgrade():
    op.drop_table("ifood_catalog_submissions")
    op.drop_table("ifood_catalog_confirmations")
    op.drop_table("ifood_catalog_links")
    op.drop_index("uq_produtos_tenant_id", table_name="produtos")
