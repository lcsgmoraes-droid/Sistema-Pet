"""add structured pet clinical fields

Revision ID: y6z7a8b9c0d1
Revises: w2x3y4z5a6b7
Create Date: 2026-03-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "y6z7a8b9c0d1"
down_revision = "w2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("pets")}
    fields = [
        ("alergias_lista", sa.Column("alergias_lista", sa.JSON(), nullable=True)),
        (
            "condicoes_cronicas_lista",
            sa.Column("condicoes_cronicas_lista", sa.JSON(), nullable=True),
        ),
        (
            "medicamentos_continuos_lista",
            sa.Column("medicamentos_continuos_lista", sa.JSON(), nullable=True),
        ),
        (
            "restricoes_alimentares_lista",
            sa.Column("restricoes_alimentares_lista", sa.JSON(), nullable=True),
        ),
        (
            "tipo_sanguineo",
            sa.Column("tipo_sanguineo", sa.String(length=20), nullable=True),
        ),
        (
            "pedigree_registro",
            sa.Column("pedigree_registro", sa.String(length=100), nullable=True),
        ),
        ("castrado_data", sa.Column("castrado_data", sa.Date(), nullable=True)),
    ]
    for field_name, column in fields:
        if field_name not in columns:
            op.add_column("pets", column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("pets")}
    for field_name in (
        "castrado_data",
        "pedigree_registro",
        "tipo_sanguineo",
        "restricoes_alimentares_lista",
        "medicamentos_continuos_lista",
        "condicoes_cronicas_lista",
        "alergias_lista",
    ):
        if field_name in columns:
            op.drop_column("pets", field_name)
