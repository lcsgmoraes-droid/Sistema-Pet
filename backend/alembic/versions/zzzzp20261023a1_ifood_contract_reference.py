"""Record provenance of store-declared iFood forecast rules.

Revision ID: zzzzp20261023a1
Revises: zzzzo20261023a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzp20261023a1"
down_revision = "zzzzo20261023a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ifood_merchant_configs", sa.Column("rates_reference", sa.String(240))
    )
    op.add_column("ifood_merchant_configs", sa.Column("rates_valid_from", sa.Date()))
    op.create_table(
        "ifood_margin_rules_revisions",
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
        sa.Column("merchant_id", sa.String(36)),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_ifood_margin_rules_revisions_tenant_id",
        "ifood_margin_rules_revisions",
        ["tenant_id"],
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=("ifood_margin_rules_revisions",),
        enable=True,
    )


def downgrade():
    op.drop_table("ifood_margin_rules_revisions")
    op.drop_column("ifood_merchant_configs", "rates_valid_from")
    op.drop_column("ifood_merchant_configs", "rates_reference")
