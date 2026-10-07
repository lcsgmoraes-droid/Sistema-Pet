"""origem do produto (loja que cadastrou) e historico de alteracoes de produtos

Revision ID: zzzr20261005a1
Revises: zzzq20261005a1
Create Date: 2026-10-05

Aditiva. Cada produto existente recebe como origem a propria loja. O historico
comeca vazio e passa a ser gravado a partir das alteracoes do cadastro base.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "zzzr20261005a1"
down_revision: Union[str, None] = "zzzq20261005a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "produtos",
        sa.Column("origem_tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_produtos_origem_tenant_id", "produtos", ["origem_tenant_id"])
    op.execute("UPDATE produtos SET origem_tenant_id = tenant_id WHERE origem_tenant_id IS NULL")

    op.create_table(
        "produtos_historico_alteracoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "produto_id",
            sa.Integer(),
            sa.ForeignKey("produtos.id", ondelete="CASCADE"),
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
    op.create_index("ix_produtos_historico_alteracoes_tenant_id", "produtos_historico_alteracoes", ["tenant_id"])
    op.create_index("ix_produtos_historico_alteracoes_produto_id", "produtos_historico_alteracoes", ["produto_id"])


def downgrade() -> None:
    op.drop_index("ix_produtos_historico_alteracoes_produto_id", table_name="produtos_historico_alteracoes")
    op.drop_index("ix_produtos_historico_alteracoes_tenant_id", table_name="produtos_historico_alteracoes")
    op.drop_table("produtos_historico_alteracoes")
    op.drop_index("ix_produtos_origem_tenant_id", table_name="produtos")
    op.drop_column("produtos", "origem_tenant_id")
