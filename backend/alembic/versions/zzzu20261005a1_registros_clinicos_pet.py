"""registros clinicos do pet por loja (historico e peso)

Revision ID: zzzu20261005a1
Revises: zzzt20261005a1
Create Date: 2026-10-05

Cria pets_registros_clinicos e copia os valores atuais de pets.historico_clinico
e pets.peso para registros da loja de origem. As colunas antigas ficam como legado
(ainda lidas por outros modulos) e serao removidas depois.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "zzzu20261005a1"
down_revision: Union[str, None] = "zzzt20261005a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pets_registros_clinicos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("valor", sa.Float(), nullable=True),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pets_registros_clinicos_tenant_id", "pets_registros_clinicos", ["tenant_id"])
    op.create_index("ix_pets_registros_clinicos_pet_id", "pets_registros_clinicos", ["pet_id"])
    op.execute(
        """
        INSERT INTO pets_registros_clinicos (tenant_id, pet_id, tipo, texto, registrado_em)
        SELECT COALESCE(origem_tenant_id, tenant_id), id, 'historico', historico_clinico,
               COALESCE(updated_at, created_at, now())
        FROM pets
        WHERE historico_clinico IS NOT NULL AND btrim(historico_clinico) <> ''
        """
    )
    op.execute(
        """
        INSERT INTO pets_registros_clinicos (tenant_id, pet_id, tipo, valor, registrado_em)
        SELECT COALESCE(origem_tenant_id, tenant_id), id, 'peso', peso,
               COALESCE(updated_at, created_at, now())
        FROM pets
        WHERE peso IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_pets_registros_clinicos_pet_id", table_name="pets_registros_clinicos")
    op.drop_index("ix_pets_registros_clinicos_tenant_id", table_name="pets_registros_clinicos")
    op.drop_table("pets_registros_clinicos")
