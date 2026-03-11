"""create canal_descontos table

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6, k4l5m6n7o8p9
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n2o3p4q5r6s7"
down_revision: Union[str, Sequence[str], None] = ("m1n2o3p4q5r6", "k4l5m6n7o8p9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canal_descontos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("desconto_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("data_inicio", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("data_fim", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_canal_descontos_tenant_id", "canal_descontos", ["tenant_id"])
    op.create_index("ix_canal_descontos_canal", "canal_descontos", ["canal"])
    op.create_index("ix_canal_descontos_ativo", "canal_descontos", ["ativo"])


def downgrade() -> None:
    op.drop_index("ix_canal_descontos_ativo", table_name="canal_descontos")
    op.drop_index("ix_canal_descontos_canal", table_name="canal_descontos")
    op.drop_index("ix_canal_descontos_tenant_id", table_name="canal_descontos")
    op.drop_table("canal_descontos")
