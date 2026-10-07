"""remove pet_mestre: o cadastro do animal passa a ser unico, sem copia no grupo

Revision ID: zzzt20261005a1
Revises: zzzs20261005a1
Create Date: 2026-10-05

Apaga a ligacao pets.pet_mestre_id e a tabela pet_mestre. Antes de aplicar em
producao, conferir a contagem da tabela (ensaio com copia do banco).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "zzzt20261005a1"
down_revision: Union[str, None] = "zzzs20261005a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("pets", "pet_mestre_id")
    op.drop_table("pet_mestre")


def downgrade() -> None:
    op.create_table(
        "pet_mestre",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("grupo_id", sa.Integer(), sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("especie", sa.String(50), nullable=False),
        sa.Column("raca", sa.String(100), nullable=True),
        sa.Column("sexo", sa.String(10), nullable=True),
        sa.Column("porte", sa.String(20), nullable=True),
        sa.Column("cor", sa.String(100), nullable=True),
        sa.Column("cor_pelagem", sa.String(100), nullable=True),
        sa.Column("data_nascimento", sa.DateTime(), nullable=True),
        sa.Column("castrado", sa.Boolean(), nullable=True),
        sa.Column("castrado_data", sa.Date(), nullable=True),
        sa.Column("foto_url", sa.String(500), nullable=True),
        sa.Column("microchip", sa.String(50), nullable=True),
        sa.Column("tipo_sanguineo", sa.String(20), nullable=True),
        sa.Column("pedigree_registro", sa.String(100), nullable=True),
        sa.Column("alergias", sa.Text(), nullable=True),
        sa.Column("alergias_lista", postgresql.JSON(), nullable=True),
        sa.Column("doencas_cronicas", sa.Text(), nullable=True),
        sa.Column("condicoes_cronicas_lista", postgresql.JSON(), nullable=True),
        sa.Column("medicamentos_continuos", sa.Text(), nullable=True),
        sa.Column("medicamentos_continuos_lista", postgresql.JSON(), nullable=True),
        sa.Column("restricoes_alimentares_lista", postgresql.JSON(), nullable=True),
        sa.Column("historico_clinico", sa.Text(), nullable=True),
        sa.Column("temperamento", sa.String(50), nullable=True),
        sa.Column("reacao_animais", sa.String(50), nullable=True),
        sa.Column("reacao_pessoas", sa.String(50), nullable=True),
        sa.Column("medo_secador", sa.String(50), nullable=True),
        sa.Column("medo_tesoura", sa.String(50), nullable=True),
        sa.Column("aceita_focinheira", sa.String(50), nullable=True),
        sa.Column("comportamento_carro", sa.String(50), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pet_mestre_grupo_id", "pet_mestre", ["grupo_id"])
    op.create_index("ix_pet_mestre_microchip", "pet_mestre", ["microchip"])
    op.add_column("pets", sa.Column("pet_mestre_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "pets_pet_mestre_id_fkey", "pets", "pet_mestre", ["pet_mestre_id"], ["id"], ondelete="SET NULL"
    )
