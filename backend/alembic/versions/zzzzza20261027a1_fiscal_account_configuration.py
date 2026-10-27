"""Autoridade única por empresa: consentimento de upload e revisão da configuração."""

from alembic import op
import sqlalchemy as sa

revision = "zzzzza20261027a1"
down_revision = "zzzzz20261027a1"
branch_labels = None
depends_on = None
TABLE = "ecommerceai_fiscal_accounts"


def upgrade():
    op.add_column(
        TABLE,
        sa.Column(
            "upload_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "configuration_version", sa.Integer(), nullable=False, server_default="1"
        ),
    )
    op.alter_column(
        TABLE,
        "active",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.false(),
    )


def downgrade():
    op.execute("SET LOCAL row_security = off")
    history = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM ecommerceai_fiscal_accounts WHERE upload_enabled OR configuration_version > 1 LIMIT 1"
            )
        )
        .first()
    )
    if history:
        raise RuntimeError(
            "Existe consentimento ou revisão de configuração fiscal; preserve o histórico."
        )
    op.alter_column(
        TABLE,
        "active",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=None,
    )
    op.drop_column(TABLE, "configuration_version")
    op.drop_column(TABLE, "upload_enabled")
