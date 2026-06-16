"""add missing dre subcategoria fields

Revision ID: oo20260515a6
Revises: on20260515a5
Create Date: 2026-05-15 17:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "oo20260515a6"
down_revision = "on20260515a5"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {constraint["name"] for constraint in inspector.get_foreign_keys(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("dre_subcategorias"):
        return

    columns = _column_names(inspector, "dre_subcategorias")
    if "custo_pe" not in columns:
        op.add_column(
            "dre_subcategorias",
            sa.Column("custo_pe", sa.String(length=10), nullable=True),
        )
    if "categoria_financeira_id" not in columns:
        op.add_column(
            "dre_subcategorias",
            sa.Column("categoria_financeira_id", sa.Integer(), nullable=True),
        )

    inspector = sa.inspect(bind)
    constraints = _constraint_names(inspector, "dre_subcategorias")
    if (
        inspector.has_table("categorias_financeiras")
        and "fk_dre_subcategorias_categoria_financeira_id" not in constraints
    ):
        op.create_foreign_key(
            "fk_dre_subcategorias_categoria_financeira_id",
            "dre_subcategorias",
            "categorias_financeiras",
            ["categoria_financeira_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("dre_subcategorias"):
        return

    constraints = _constraint_names(inspector, "dre_subcategorias")
    if "fk_dre_subcategorias_categoria_financeira_id" in constraints:
        op.drop_constraint(
            "fk_dre_subcategorias_categoria_financeira_id",
            "dre_subcategorias",
            type_="foreignkey",
        )

    columns = _column_names(inspector, "dre_subcategorias")
    if "categoria_financeira_id" in columns:
        op.drop_column("dre_subcategorias", "categoria_financeira_id")
    if "custo_pe" in columns:
        op.drop_column("dre_subcategorias", "custo_pe")
