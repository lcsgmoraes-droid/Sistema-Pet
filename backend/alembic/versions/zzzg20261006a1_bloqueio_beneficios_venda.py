"""Registra a decisão de não gerar benefícios de campanhas na venda.

Revision ID: zzzg20261006a1
Revises: zzzf20261006a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzg20261006a1"
down_revision = "zzzf20261006a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendas",
        sa.Column("nao_gerar_beneficios", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("vendas", sa.Column("justificativa_nao_gerar_beneficios", sa.Text()))
    op.add_column("vendas", sa.Column("beneficios_bloqueados_em", sa.DateTime()))
    op.add_column("vendas", sa.Column("beneficios_bloqueados_por_id", sa.Integer()))
    op.create_foreign_key(
        "fk_vendas_beneficios_bloqueados_por_id_users",
        "vendas", "users", ["beneficios_bloqueados_por_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_vendas_beneficios_bloqueados_por_id_users", "vendas", type_="foreignkey"
    )
    op.drop_column("vendas", "beneficios_bloqueados_por_id")
    op.drop_column("vendas", "beneficios_bloqueados_em")
    op.drop_column("vendas", "justificativa_nao_gerar_beneficios")
    op.drop_column("vendas", "nao_gerar_beneficios")
