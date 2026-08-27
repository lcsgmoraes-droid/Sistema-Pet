"""add feed end estimate to sale items

Revision ID: zxi20260827a1
Revises: zxh20260827a1
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "zxi20260827a1"
down_revision = "zxh20260827a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "venda_itens",
        sa.Column("racao_data_prevista_fim", sa.Date(), nullable=True),
    )
    op.add_column(
        "venda_itens",
        sa.Column("racao_prazo_estimado_dias", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_venda_itens_racao_prazo_estimado",
        "venda_itens",
        "racao_prazo_estimado_dias IS NULL OR "
        "racao_prazo_estimado_dias BETWEEN 1 AND 365",
    )
    op.create_check_constraint(
        "ck_venda_itens_racao_previsao_unica",
        "venda_itens",
        "NOT (racao_data_prevista_fim IS NOT NULL "
        "AND racao_prazo_estimado_dias IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_venda_itens_racao_previsao_unica",
        "venda_itens",
        type_="check",
    )
    op.drop_constraint(
        "ck_venda_itens_racao_prazo_estimado",
        "venda_itens",
        type_="check",
    )
    op.drop_column("venda_itens", "racao_prazo_estimado_dias")
    op.drop_column("venda_itens", "racao_data_prevista_fim")
