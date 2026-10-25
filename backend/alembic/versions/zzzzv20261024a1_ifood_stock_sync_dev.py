"""Fila duravel de estoque iFood exclusiva do piloto DEV.

Revision ID: zzzzv20261024a1
Revises: zzzzu20261024a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzv20261024a1"
down_revision = "zzzzu20261024a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ifood_catalog_submissions",
        sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
    )
    op.create_check_constraint(
        "ck_ifood_catalog_submission_source",
        "ifood_catalog_submissions",
        "source IN ('manual','auto_stock')",
    )
    op.create_table(
        "ifood_stock_sync_states",
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
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("link_revision", sa.Integer(), nullable=False),
        sa.Column("desired_stock", sa.Integer(), nullable=True),
        sa.Column("last_accepted_stock", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_request_key", sa.String(36), nullable=True),
        sa.Column("last_confirmation_id", sa.Integer(), nullable=True),
        sa.Column("reference_source", sa.String(16), nullable=True),
        sa.Column("error_code", sa.String(40), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "merchant_id", "link_id", name="uq_ifood_stock_sync_link"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "link_id"],
            ["ifood_catalog_links.tenant_id", "ifood_catalog_links.id"],
            name="fk_ifood_stock_sync_link",
        ),
        sa.CheckConstraint("link_revision > 0", name="ck_ifood_stock_sync_revision"),
        sa.CheckConstraint(
            "desired_stock IS NULL OR desired_stock >= 0",
            name="ck_ifood_stock_sync_desired",
        ),
        sa.CheckConstraint(
            "last_accepted_stock IS NULL OR last_accepted_stock >= 0",
            name="ck_ifood_stock_sync_accepted",
        ),
        sa.CheckConstraint("failure_count >= 0", name="ck_ifood_stock_sync_failures"),
        sa.CheckConstraint(
            "reference_source IS NULL OR reference_source IN ('portal','api_acceptance')",
            name="ck_ifood_stock_sync_reference",
        ),
        sa.CheckConstraint(
            "status IN ('queued','sending','accepted','backoff','blocked','uncertain')",
            name="ck_ifood_stock_sync_status",
        ),
    )
    op.create_index(
        "ix_ifood_stock_sync_states_tenant_id", "ifood_stock_sync_states", ["tenant_id"]
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=("ifood_stock_sync_states",),
        enable=True,
    )


def downgrade():
    # Nao apagar a fila nem a origem das tentativas: sao provas operacionais.
    op.execute("SET LOCAL row_security = off")
    bind = op.get_bind()
    found = bind.execute(
        sa.text("SELECT 1 FROM ifood_stock_sync_states LIMIT 1")
    ).first()
    automated = bind.execute(
        sa.text(
            "SELECT 1 FROM ifood_catalog_submissions WHERE source = 'auto_stock' LIMIT 1"
        )
    ).first()
    if found or automated:
        raise RuntimeError(
            "Existe historico de estoque automatico iFood; downgrade recusado."
        )
    op.drop_table("ifood_stock_sync_states")
    op.drop_constraint(
        "ck_ifood_catalog_submission_source", "ifood_catalog_submissions", type_="check"
    )
    op.drop_column("ifood_catalog_submissions", "source")
