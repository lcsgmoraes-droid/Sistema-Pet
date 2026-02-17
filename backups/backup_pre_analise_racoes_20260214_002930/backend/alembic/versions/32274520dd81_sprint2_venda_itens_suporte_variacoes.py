"""sprint2_venda_itens_suporte_variacoes

Revision ID: 32274520dd81
Revises: 20260126_vpag_upd
Create Date: 2026-01-26 16:58:08.433135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32274520dd81'
down_revision: Union[str, Sequence[str], None] = '20260126_vpag_upd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
