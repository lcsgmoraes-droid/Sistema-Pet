"""add vet consultation draft items

Revision ID: ou20260517a1
Revises: ot20260516a2
Create Date: 2026-05-17 18:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "ou20260517a1"
down_revision = "ot20260516a2"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("vet_consultas")

    if "prescricao_rascunho" not in columns:
        op.add_column("vet_consultas", sa.Column("prescricao_rascunho", sa.JSON(), nullable=True))

    if "procedimentos_rascunho" not in columns:
        op.add_column("vet_consultas", sa.Column("procedimentos_rascunho", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _columns("vet_consultas")

    if "procedimentos_rascunho" in columns:
        op.drop_column("vet_consultas", "procedimentos_rascunho")

    if "prescricao_rascunho" in columns:
        op.drop_column("vet_consultas", "prescricao_rascunho")
