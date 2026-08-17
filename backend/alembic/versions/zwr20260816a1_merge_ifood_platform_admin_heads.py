"""merge iFood and platform administrator migration heads

Revision ID: zwr20260816a1
Revises: ifd20260816a1, zwq20260816a1
Create Date: 2026-08-16
"""

revision = "zwr20260816a1"
down_revision = ("ifd20260816a1", "zwq20260816a1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Unifica as duas linhas sem executar alteração adicional."""


def downgrade() -> None:
    """Retorna às duas pontas anteriores sem desfazer seus esquemas."""
