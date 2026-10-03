"""Merge das duas pontas trazidas pelo reconcilio da branch documentacao com
a main: planos por segmento em billing_offers (documentacao) e o comprovante
de pagamento / bloqueio de credario / pagamento previsto de entrega (main).
Nao muda nenhum schema, so reconecta a cadeia de migrations numa linha unica.

Revision ID: zzzm20261002a1
Revises: zzzl20261001a1, zzzc20261002a1
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzm20261002a1"
down_revision = ("zzzl20261001a1", "zzzc20261002a1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
