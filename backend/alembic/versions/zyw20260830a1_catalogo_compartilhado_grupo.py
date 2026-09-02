"""add full catalog access to selective shared stock

Revision ID: zyw20260830a1
Revises: zyv20260830a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zyw20260830a1"
down_revision = "zyv20260830a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "empresa_grupo_estoques_compartilhados" not in inspector.get_table_names():
        return
    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns("empresa_grupo_estoques_compartilhados")
    }
    if "acesso_catalogo_completo" not in colunas:
        with op.batch_alter_table("empresa_grupo_estoques_compartilhados") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acesso_catalogo_completo",
                    sa.Boolean(),
                    server_default=sa.false(),
                    nullable=False,
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "empresa_grupo_estoques_compartilhados" not in inspector.get_table_names():
        return
    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns("empresa_grupo_estoques_compartilhados")
    }
    if "acesso_catalogo_completo" in colunas:
        with op.batch_alter_table("empresa_grupo_estoques_compartilhados") as batch_op:
            batch_op.drop_column("acesso_catalogo_completo")
