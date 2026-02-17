"""merge_multiple_heads

Revision ID: e8c8810a6193
Revises: 20260212_add_adquirente_conciliacao_recebimentos, add_status_conciliacao_vpag, add_unique_nsu_operadora
Create Date: 2026-02-12 21:09:53.113965

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8c8810a6193'
down_revision: Union[str, Sequence[str], None] = ('20260212_add_adquirente_conciliacao_recebimentos', 'add_status_conciliacao_vpag', 'add_unique_nsu_operadora')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
