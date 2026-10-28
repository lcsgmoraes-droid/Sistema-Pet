"""administrador da plataforma: permissao do painel e troca de senha provisoria

Revision ID: zzzzzf20261029a1
Revises: zzzzze20261028a1
Create Date: 2026-10-29
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzzzf20261029a1"
down_revision = "zzzzze20261028a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Quem ja era administrador do OPS NAO ganha acesso ao painel novo: a permissao nasce
    # desligada e so o script criar_admin_plataforma.py a liga.
    op.add_column(
        "platform_admins",
        sa.Column(
            "painel_adm_ativo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "platform_admins",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_admins", "must_change_password")
    op.drop_column("platform_admins", "painel_adm_ativo")
