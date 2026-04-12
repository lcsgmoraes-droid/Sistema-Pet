"""add_stamp_index_to_loyalty_stamps

Revision ID: q7r8s9t0u1v2
Revises: c1d2e3f4a5b6
Create Date: 2026-04-11 15:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q7r8s9t0u1v2"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loyalty_stamps",
        sa.Column("stamp_index", sa.Integer(), nullable=True, server_default="1"),
    )
    op.execute("UPDATE loyalty_stamps SET stamp_index = 1 WHERE stamp_index IS NULL")
    op.alter_column(
        "loyalty_stamps",
        "stamp_index",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="1",
    )

    op.drop_constraint("uq_loyalty_stamp_venda", "loyalty_stamps", type_="unique")
    op.create_unique_constraint(
        "uq_loyalty_stamp_venda",
        "loyalty_stamps",
        ["tenant_id", "campaign_id", "customer_id", "venda_id", "stamp_index"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_loyalty_stamp_venda", "loyalty_stamps", type_="unique")
    op.create_unique_constraint(
        "uq_loyalty_stamp_venda",
        "loyalty_stamps",
        ["tenant_id", "customer_id", "venda_id"],
    )
    op.drop_column("loyalty_stamps", "stamp_index")
