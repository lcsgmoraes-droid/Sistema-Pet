"""store installment interval for store credit

Revision ID: zxa20260824a1
Revises: zwz20260824a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zxa20260824a1"
down_revision = "zwz20260824a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "venda_pagamentos" not in inspector.get_table_names():
        return
    colunas = {coluna["name"] for coluna in inspector.get_columns("venda_pagamentos")}
    if "intervalo_crediario" not in colunas:
        op.add_column(
            "venda_pagamentos",
            sa.Column("intervalo_crediario", sa.String(length=20), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "venda_pagamentos" not in inspector.get_table_names():
        return
    colunas = {coluna["name"] for coluna in inspector.get_columns("venda_pagamentos")}
    if "intervalo_crediario" in colunas:
        op.drop_column("venda_pagamentos", "intervalo_crediario")
