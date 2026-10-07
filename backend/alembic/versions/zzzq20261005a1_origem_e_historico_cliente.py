"""origem da pessoa (loja que introduziu) e historico de alteracoes de clientes

Revision ID: zzzq20261005a1
Revises: zzzp20261005a1
Create Date: 2026-10-05

Aditiva: nao altera o isolamento entre lojas. Cada cadastro existente recebe
como origem a propria loja. Historico comeca vazio e passa a ser gravado a
partir das alteracoes feitas pela tela.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "zzzq20261005a1"
down_revision: Union[str, None] = "zzzp20261005a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column("origem_tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_clientes_origem_tenant_id", "clientes", ["origem_tenant_id"])
    op.execute("UPDATE clientes SET origem_tenant_id = tenant_id WHERE origem_tenant_id IS NULL")

    op.create_table(
        "clientes_historico_alteracoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "cliente_id",
            sa.Integer(),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campo", sa.String(length=100), nullable=False),
        sa.Column("valor_anterior", sa.Text(), nullable=True),
        sa.Column("valor_novo", sa.Text(), nullable=True),
        sa.Column(
            "alterado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_clientes_historico_alteracoes_tenant_id",
        "clientes_historico_alteracoes",
        ["tenant_id"],
    )
    op.create_index(
        "ix_clientes_historico_alteracoes_cliente_id",
        "clientes_historico_alteracoes",
        ["cliente_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_clientes_historico_alteracoes_cliente_id", table_name="clientes_historico_alteracoes")
    op.drop_index("ix_clientes_historico_alteracoes_tenant_id", table_name="clientes_historico_alteracoes")
    op.drop_table("clientes_historico_alteracoes")
    op.drop_index("ix_clientes_origem_tenant_id", table_name="clientes")
    op.drop_column("clientes", "origem_tenant_id")
