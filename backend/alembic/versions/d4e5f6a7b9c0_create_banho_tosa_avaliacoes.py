"""create banho tosa avaliacoes

Revision ID: d4e5f6a7b9c0
Revises: c3d4e5f6a9b0
Create Date: 2026-04-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "d4e5f6a7b9c0"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a9b0"
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
        "banho_tosa_avaliacoes",
        *_tenant_columns(),
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("nota_nps", sa.Integer(), nullable=False),
        sa.Column("nota_servico", sa.Integer(), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("origem", sa.String(30), nullable=False, server_default="app"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "atendimento_id", "cliente_id", name="uq_bt_avaliacao_atendimento_cliente"),
    )
    op.create_index("ix_banho_tosa_avaliacoes_tenant_id", "banho_tosa_avaliacoes", ["tenant_id"])
    op.create_index("ix_bt_avaliacoes_atendimento_id", "banho_tosa_avaliacoes", ["atendimento_id"])
    op.create_index("ix_bt_avaliacoes_cliente_id", "banho_tosa_avaliacoes", ["cliente_id"])
    op.create_index("ix_bt_avaliacoes_pet_id", "banho_tosa_avaliacoes", ["pet_id"])
    op.create_index("ix_bt_avaliacoes_cliente_pet", "banho_tosa_avaliacoes", ["tenant_id", "cliente_id", "pet_id"])


def downgrade() -> None:
    op.drop_index("ix_bt_avaliacoes_cliente_pet", table_name="banho_tosa_avaliacoes")
    op.drop_index("ix_bt_avaliacoes_pet_id", table_name="banho_tosa_avaliacoes")
    op.drop_index("ix_bt_avaliacoes_cliente_id", table_name="banho_tosa_avaliacoes")
    op.drop_index("ix_bt_avaliacoes_atendimento_id", table_name="banho_tosa_avaliacoes")
    op.drop_index("ix_banho_tosa_avaliacoes_tenant_id", table_name="banho_tosa_avaliacoes")
    op.drop_table("banho_tosa_avaliacoes")
