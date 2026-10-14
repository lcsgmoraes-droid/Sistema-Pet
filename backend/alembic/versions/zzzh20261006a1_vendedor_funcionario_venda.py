"""Registra o funcionario que atendeu a venda independentemente de comissao.

Revision ID: zzzh20261006a1
Revises: zzzg20261006a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzh20261006a1"
down_revision = "zzzg20261006a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendas", sa.Column("vendedor_funcionario_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_vendas_vendedor_funcionario_id_clientes",
        "vendas", "clientes", ["vendedor_funcionario_id"], ["id"],
    )
    op.create_index(
        "ix_vendas_vendedor_funcionario_id", "vendas", ["vendedor_funcionario_id"]
    )
    op.execute(
        "UPDATE vendas SET vendedor_funcionario_id = funcionario_id "
        "WHERE funcionario_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_vendas_vendedor_funcionario_id", table_name="vendas")
    op.drop_constraint(
        "fk_vendas_vendedor_funcionario_id_clientes", "vendas", type_="foreignkey"
    )
    op.drop_column("vendas", "vendedor_funcionario_id")
