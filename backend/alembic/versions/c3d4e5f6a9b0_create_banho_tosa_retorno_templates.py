"""create banho tosa retorno templates

Revision ID: c3d4e5f6a9b0
Revises: b2c3d4e5f6a8
Create Date: 2026-04-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "c3d4e5f6a9b0"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "banho_tosa_retorno_templates",
        *_tenant_columns(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("tipo_retorno", sa.String(40), nullable=False, server_default="todos"),
        sa.Column("canal", sa.String(30), nullable=False, server_default="app"),
        sa.Column("assunto", sa.String(180), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "nome", "canal", name="uq_bt_retorno_templates_nome_canal"),
    )
    op.create_index("ix_banho_tosa_retorno_templates_tenant_id", "banho_tosa_retorno_templates", ["tenant_id"])
    op.create_index("ix_bt_retorno_templates_nome", "banho_tosa_retorno_templates", ["nome"])
    op.create_index("ix_bt_retorno_templates_tipo_retorno", "banho_tosa_retorno_templates", ["tipo_retorno"])
    op.create_index("ix_bt_retorno_templates_canal", "banho_tosa_retorno_templates", ["canal"])
    op.create_index(
        "ix_bt_retorno_templates_tipo_canal",
        "banho_tosa_retorno_templates",
        ["tenant_id", "tipo_retorno", "canal", "ativo"],
    )


def downgrade() -> None:
    op.drop_index("ix_bt_retorno_templates_tipo_canal", table_name="banho_tosa_retorno_templates")
    op.drop_index("ix_bt_retorno_templates_canal", table_name="banho_tosa_retorno_templates")
    op.drop_index("ix_bt_retorno_templates_tipo_retorno", table_name="banho_tosa_retorno_templates")
    op.drop_index("ix_bt_retorno_templates_nome", table_name="banho_tosa_retorno_templates")
    op.drop_index("ix_banho_tosa_retorno_templates_tenant_id", table_name="banho_tosa_retorno_templates")
    op.drop_table("banho_tosa_retorno_templates")
