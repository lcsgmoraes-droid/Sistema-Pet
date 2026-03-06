"""add_customer_merge_logs

Cria tabela customer_merge_logs para registrar unificações de clientes
via CPF/telefone/e-mail (Sprint 8 — Unificação Cross-Canal).

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-03-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_merge_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_keep_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_remove_id", sa.BigInteger(), nullable=False),
        sa.Column("motivo", sa.String(100), nullable=True),
        sa.Column(
            "merged_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("merged_by_user_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "undone",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cml_tenant_keep",
        "customer_merge_logs",
        ["tenant_id", "customer_keep_id"],
    )
    op.create_index(
        "ix_cml_tenant_remove",
        "customer_merge_logs",
        ["tenant_id", "customer_remove_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cml_tenant_remove", table_name="customer_merge_logs")
    op.drop_index("ix_cml_tenant_keep", table_name="customer_merge_logs")
    op.drop_table("customer_merge_logs")
