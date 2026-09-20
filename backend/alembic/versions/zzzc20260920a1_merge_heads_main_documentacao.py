"""Merge das duas pontas de migration que a branch documentacao trouxe da
main (aniversarios de contatos) e da propria documentacao (camada geral do
grupo comercial / pessoa mestre) apos o merge de main dentro de
documentacao. Nao muda nenhum schema, so reconecta a cadeia de migrations
numa linha unica.

Revision ID: zzzc20260920a1
Revises: zzx20260919a1, zzzb20260918a1
Create Date: 2026-09-20
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzc20260920a1"
down_revision = ("zzx20260919a1", "zzzb20260918a1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
