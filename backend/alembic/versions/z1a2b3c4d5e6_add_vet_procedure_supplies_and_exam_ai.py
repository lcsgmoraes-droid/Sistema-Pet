"""add vet procedure supplies and exam ai

Revision ID: z1a2b3c4d5e6
Revises: y6z7a8b9c0d1
Create Date: 2026-03-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "z1a2b3c4d5e6"
down_revision = "y6z7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vet_catalogo_procedimentos", sa.Column("insumos", sa.JSON(), nullable=True))
    op.add_column("vet_procedimentos_consulta", sa.Column("insumos", sa.JSON(), nullable=True))
    op.add_column("vet_procedimentos_consulta", sa.Column("estoque_baixado", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("vet_procedimentos_consulta", sa.Column("estoque_movimentacao_ids", sa.JSON(), nullable=True))

    op.add_column("vet_exames", sa.Column("interpretacao_ia_resumo", sa.Text(), nullable=True))
    op.add_column("vet_exames", sa.Column("interpretacao_ia_confianca", sa.Float(), nullable=True))
    op.add_column("vet_exames", sa.Column("interpretacao_ia_alertas", sa.JSON(), nullable=True))
    op.add_column("vet_exames", sa.Column("interpretacao_ia_payload", sa.JSON(), nullable=True))

    op.alter_column("vet_procedimentos_consulta", "estoque_baixado", server_default=None)


def downgrade() -> None:
    op.drop_column("vet_exames", "interpretacao_ia_payload")
    op.drop_column("vet_exames", "interpretacao_ia_alertas")
    op.drop_column("vet_exames", "interpretacao_ia_confianca")
    op.drop_column("vet_exames", "interpretacao_ia_resumo")

    op.drop_column("vet_procedimentos_consulta", "estoque_movimentacao_ids")
    op.drop_column("vet_procedimentos_consulta", "estoque_baixado")
    op.drop_column("vet_procedimentos_consulta", "insumos")
    op.drop_column("vet_catalogo_procedimentos", "insumos")