"""Remove grupo_comercial_gestores: feature de "gestor concedido pelo
master" foi eliminada em decisao de negocio anterior (21/09/2026, ver
comentario em app/grupo_comercial_service.py::tem_acesso_gestao) - so o
usuario master do grupo tem controle sobre ele. A tabela ficou orfa desde
entao (0 linhas em producao, nenhum codigo le/escreve nela). Removida
junto com o modelo `GrupoComercialGestor`.

Revision ID: zzzx20261007a1
Revises: zzzw20261006a1
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzx20261007a1"
down_revision = "zzzw20261006a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "ix_grupo_comercial_gestores_user_id", table_name="grupo_comercial_gestores"
    )
    op.drop_index(
        "ix_grupo_comercial_gestores_grupo_id", table_name="grupo_comercial_gestores"
    )
    op.drop_table("grupo_comercial_gestores")


def downgrade() -> None:
    # Remocao deliberada de feature sem uso (mesma decisao ja tomada em
    # zzzd20260920a1 para grupo_comercial_codigos/grupo_comercial_convites).
    # Recria só a estrutura (sempre vazia em producao); nao ha dado a
    # restaurar.
    op.create_table(
        "grupo_comercial_gestores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "concedido_por_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="ativo"
        ),
        sa.Column(
            "concedido_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "grupo_id", "user_id", name="uq_grupo_comercial_gestor_usuario"
        ),
    )
    op.create_index(
        "ix_grupo_comercial_gestores_grupo_id",
        "grupo_comercial_gestores",
        ["grupo_id"],
    )
    op.create_index(
        "ix_grupo_comercial_gestores_user_id",
        "grupo_comercial_gestores",
        ["user_id"],
    )
