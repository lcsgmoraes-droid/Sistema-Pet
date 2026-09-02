"""store Bling stock deposit per tenant

Revision ID: zyv20260830a1
Revises: zyu20260830a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zyv20260830a1"
down_revision = "zyu20260830a1"
branch_labels = None
depends_on = None


CONNECTIONS = "bling_connections"
COLUMN = "stock_deposit_id"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns(CONNECTIONS)}
    if COLUMN not in columns:
        op.add_column(CONNECTIONS, sa.Column(COLUMN, sa.BigInteger(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns(CONNECTIONS)}
    if COLUMN in columns:
        op.drop_column(CONNECTIONS, COLUMN)
