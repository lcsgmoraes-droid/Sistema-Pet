"""Registra tributação da entrada XML no item e no lote.

Revision ID: zzq20260914a1
Revises: zzp20260914a1
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "zzq20260914a1"
down_revision = "zzp20260914a1"
branch_labels = None
depends_on = None


def upgrade():
    for column in (
        sa.Column("cst_icms", sa.String(3), nullable=True),
        sa.Column("icms_st", sa.Boolean(), nullable=True),
        sa.Column("icms_base_st", sa.Float(), nullable=True),
        sa.Column("icms_valor_st", sa.Float(), nullable=True),
    ):
        op.add_column("notas_entrada_itens", column)

    for column in (
        sa.Column("fiscal_ncm", sa.String(8), nullable=True),
        sa.Column("fiscal_cest", sa.String(7), nullable=True),
        sa.Column("fiscal_origem_mercadoria", sa.String(1), nullable=True),
        sa.Column("fiscal_cfop_entrada", sa.String(4), nullable=True),
        sa.Column("fiscal_cst_icms_entrada", sa.String(3), nullable=True),
        sa.Column("fiscal_icms_st", sa.Boolean(), nullable=True),
    ):
        op.add_column("produto_lotes", column)


def downgrade():
    for column in (
        "fiscal_icms_st",
        "fiscal_cst_icms_entrada",
        "fiscal_cfop_entrada",
        "fiscal_origem_mercadoria",
        "fiscal_cest",
        "fiscal_ncm",
    ):
        op.drop_column("produto_lotes", column)

    for column in ("icms_valor_st", "icms_base_st", "icms_st", "cst_icms"):
        op.drop_column("notas_entrada_itens", column)
