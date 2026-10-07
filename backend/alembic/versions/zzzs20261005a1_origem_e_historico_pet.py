"""origem do pet (loja que cadastrou) e historico dos dados diretos de pets

Revision ID: zzzs20261005a1
Revises: zzzr20261005a1
Create Date: 2026-10-05

Aditiva. Cada pet existente recebe como origem a propria loja. Campos de saude
do pet nao entram no historico (pendencia de decisao).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "zzzs20261005a1"
down_revision: Union[str, None] = "zzzr20261005a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pets", sa.Column("origem_tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_pets_origem_tenant_id", "pets", ["origem_tenant_id"])
    op.execute("UPDATE pets SET origem_tenant_id = tenant_id WHERE origem_tenant_id IS NULL")

    op.create_table(
        "pets_historico_alteracoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campo", sa.String(length=100), nullable=False),
        sa.Column("valor_anterior", sa.Text(), nullable=True),
        sa.Column("valor_novo", sa.Text(), nullable=True),
        sa.Column("alterado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pets_historico_alteracoes_tenant_id", "pets_historico_alteracoes", ["tenant_id"])
    op.create_index("ix_pets_historico_alteracoes_pet_id", "pets_historico_alteracoes", ["pet_id"])


def downgrade() -> None:
    op.drop_index("ix_pets_historico_alteracoes_pet_id", table_name="pets_historico_alteracoes")
    op.drop_index("ix_pets_historico_alteracoes_tenant_id", table_name="pets_historico_alteracoes")
    op.drop_table("pets_historico_alteracoes")
    op.drop_index("ix_pets_origem_tenant_id", table_name="pets")
    op.drop_column("pets", "origem_tenant_id")
