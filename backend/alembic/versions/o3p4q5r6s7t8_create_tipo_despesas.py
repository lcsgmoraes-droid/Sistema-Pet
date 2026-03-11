"""create tipo_despesas table and add tipo_despesa_id to contas_pagar

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-03-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o3p4q5r6s7t8"
down_revision: Union[str, Sequence[str], None] = "n2o3p4q5r6s7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar tabela tipo_despesas
    op.create_table(
        "tipo_despesas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("e_custo_fixo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tipo_despesas_tenant_id", "tipo_despesas", ["tenant_id"])

    # 2. Adicionar FK em contas_pagar
    op.add_column(
        "contas_pagar",
        sa.Column("tipo_despesa_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_contas_pagar_tipo_despesa_id", "contas_pagar", ["tipo_despesa_id"])
    op.create_foreign_key(
        "fk_contas_pagar_tipo_despesa",
        "contas_pagar",
        "tipo_despesas",
        ["tipo_despesa_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_contas_pagar_tipo_despesa", "contas_pagar", type_="foreignkey")
    op.drop_index("ix_contas_pagar_tipo_despesa_id", table_name="contas_pagar")
    op.drop_column("contas_pagar", "tipo_despesa_id")
    op.drop_index("ix_tipo_despesas_tenant_id", table_name="tipo_despesas")
    op.drop_table("tipo_despesas")
