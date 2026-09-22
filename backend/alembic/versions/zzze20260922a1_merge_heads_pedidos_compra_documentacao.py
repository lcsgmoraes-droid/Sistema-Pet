"""Merge das duas pontas de migration que a branch documentacao trouxe da
main (pedido de compra por fornecedor opcional) e da propria documentacao
(usuario MASTER do grupo comercial) apos o merge de main dentro de
documentacao. Nao muda nenhum schema, so reconecta a cadeia de migrations
numa linha unica.

Revision ID: zzze20260922a1
Revises: zzy20260921a1, zzzd20260920a1
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa


revision = "zzze20260922a1"
down_revision = ("zzy20260921a1", "zzzd20260920a1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
