"""make pet code unique per tenant

Revision ID: ol20260515a3
Revises: ok20260515a2
Create Date: 2026-05-15 16:05:00.000000
"""

from alembic import op


revision = "ol20260515a3"
down_revision = "ok20260515a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pets_codigo")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pets_codigo ON pets (codigo)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_pets_tenant_codigo ON pets (tenant_id, codigo)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_pets_tenant_codigo")
    op.execute("DROP INDEX IF EXISTS ix_pets_codigo")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_pets_codigo ON pets (codigo)")
