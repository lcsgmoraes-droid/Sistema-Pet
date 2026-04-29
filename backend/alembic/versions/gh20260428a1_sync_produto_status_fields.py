"""sync produto status fields

Revision ID: gh20260428a1
Revises: fg20260427a1
Create Date: 2026-04-28 22:15:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "gh20260428a1"
down_revision: Union[str, Sequence[str], None] = "fg20260427a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # "ativo" virou o status operacional principal. "situacao" permanece para
    # compatibilidade com rotas legadas e deve acompanhar o mesmo valor.
    op.execute(
        """
        UPDATE produtos
        SET
            situacao = COALESCE(ativo, TRUE),
            updated_at = NOW()
        WHERE situacao IS DISTINCT FROM COALESCE(ativo, TRUE)
        """
    )


def downgrade() -> None:
    # Data cleanup intentionally irreversible.
    pass
