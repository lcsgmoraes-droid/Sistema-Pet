"""Merge das duas pontas de migration que a branch documentacao trouxe da
main (NFC-e com CPF sem cliente cadastrado) e da propria documentacao
(onboarding_credencial_email_pendente em tenants) apos o merge de main
dentro de documentacao. Nao muda nenhum schema, so reconecta a cadeia de
migrations numa linha unica.

Revision ID: zzzj20261001a1
Revises: zzz20260930a1, zzzi20260925a1
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzj20261001a1"
down_revision = ("zzz20260930a1", "zzzi20260925a1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
