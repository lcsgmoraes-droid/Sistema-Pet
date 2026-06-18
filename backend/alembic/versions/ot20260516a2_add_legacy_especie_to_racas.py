"""add legacy especie column to racas

Revision ID: ot20260516a2
Revises: os20260516a1
Create Date: 2026-05-16 10:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "ot20260516a2"
down_revision = "os20260516a1"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    columns = _columns("racas")
    if not columns:
        return

    if "especie" not in columns:
        op.add_column(
            "racas", sa.Column("especie", sa.String(length=50), nullable=True)
        )

    if "ix_racas_especie" not in _indexes("racas"):
        op.create_index("ix_racas_especie", "racas", ["especie"], unique=False)


def downgrade() -> None:
    columns = _columns("racas")
    if "especie" not in columns:
        return

    if "ix_racas_especie" in _indexes("racas"):
        op.drop_index("ix_racas_especie", table_name="racas")

    op.drop_column("racas", "especie")
