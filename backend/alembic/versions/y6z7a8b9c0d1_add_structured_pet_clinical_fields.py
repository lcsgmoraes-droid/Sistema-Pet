"""add structured pet clinical fields

Revision ID: y6z7a8b9c0d1
Revises: w2x3y4z5a6b7
Create Date: 2026-03-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "y6z7a8b9c0d1"
down_revision = "w2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pets", sa.Column("alergias_lista", sa.JSON(), nullable=True))
    op.add_column("pets", sa.Column("condicoes_cronicas_lista", sa.JSON(), nullable=True))
    op.add_column("pets", sa.Column("medicamentos_continuos_lista", sa.JSON(), nullable=True))
    op.add_column("pets", sa.Column("restricoes_alimentares_lista", sa.JSON(), nullable=True))
    op.add_column("pets", sa.Column("tipo_sanguineo", sa.String(length=20), nullable=True))
    op.add_column("pets", sa.Column("pedigree_registro", sa.String(length=100), nullable=True))
    op.add_column("pets", sa.Column("castrado_data", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("pets", "castrado_data")
    op.drop_column("pets", "pedigree_registro")
    op.drop_column("pets", "tipo_sanguineo")
    op.drop_column("pets", "restricoes_alimentares_lista")
    op.drop_column("pets", "medicamentos_continuos_lista")
    op.drop_column("pets", "condicoes_cronicas_lista")
    op.drop_column("pets", "alergias_lista")
