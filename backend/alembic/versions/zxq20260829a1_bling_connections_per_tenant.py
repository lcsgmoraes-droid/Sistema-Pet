"""store Bling OAuth connections per tenant

Revision ID: zxq20260829a1
Revises: zxp20260829a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zxq20260829a1"
down_revision = "zxp20260829a1"
branch_labels = None
depends_on = None


CONNECTIONS = "bling_connections"
COMPANY_LINKS = "bling_company_tenant_links"
POLICY = "bling_connections_tenant_isolation"
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(CONNECTIONS):
        op.create_table(
            CONNECTIONS,
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("access_token_encrypted", sa.Text(), nullable=False),
            sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
            sa.Column("company_id", sa.String(length=100), nullable=True),
            sa.Column(
                "status", sa.String(length=24), server_default="active", nullable=False
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "connected_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "renewal_count", sa.Integer(), server_default="0", nullable=False
            ),
            sa.Column("last_error", sa.Text(), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", name="uq_bling_connections_tenant"),
        )
        op.create_index("ix_bling_connections_tenant_id", CONNECTIONS, ["tenant_id"])
        op.create_index("ix_bling_connections_company_id", CONNECTIONS, ["company_id"])

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(COMPANY_LINKS):
        op.create_table(
            COMPANY_LINKS,
            sa.Column("company_id", sa.String(length=100), nullable=False),
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
            sa.PrimaryKeyConstraint("company_id"),
            sa.UniqueConstraint(
                "tenant_id", name="uq_bling_company_tenant_links_tenant"
            ),
        )
        op.create_index(
            "ix_bling_company_tenant_links_tenant_id", COMPANY_LINKS, ["tenant_id"]
        )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TABLE {CONNECTIONS} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {CONNECTIONS} FORCE ROW LEVEL SECURITY")
        policies = {
            row[0]
            for row in op.get_bind().execute(
                sa.text("SELECT policyname FROM pg_policies WHERE tablename = :table"),
                {"table": CONNECTIONS},
            )
        }
        if POLICY not in policies:
            op.execute(
                f"CREATE POLICY {POLICY} ON {CONNECTIONS} "
                f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(COMPANY_LINKS):
        op.drop_table(COMPANY_LINKS)
    if inspector.has_table(CONNECTIONS):
        op.drop_table(CONNECTIONS)
