"""add nota entrada processing actions

Revision ID: zz20260624a1
Revises: ub20260622a1
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "zz20260624a1"
down_revision = "ub20260622a1"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("notas_entrada")
    if "processamento_contexto" not in columns:
        op.add_column(
            "notas_entrada",
            sa.Column("processamento_contexto", sa.String(length=30), nullable=True),
        )
    if "processamento_acoes" not in columns:
        op.add_column(
            "notas_entrada",
            sa.Column("processamento_acoes", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    columns = _columns("notas_entrada")
    if "processamento_acoes" in columns:
        op.drop_column("notas_entrada", "processamento_acoes")
    if "processamento_contexto" in columns:
        op.drop_column("notas_entrada", "processamento_contexto")
