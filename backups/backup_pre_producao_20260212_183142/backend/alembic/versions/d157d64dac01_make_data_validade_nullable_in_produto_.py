"""make_data_validade_nullable_in_produto_lotes

Revision ID: d157d64dac01
Revises: 4819578f7f40
Create Date: 2026-02-10 17:37:57.784872

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd157d64dac01'
down_revision: Union[str, Sequence[str], None] = '4819578f7f40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alterar a coluna data_validade para aceitar NULL
    op.alter_column('produto_lotes', 'data_validade',
                    existing_type=sa.DateTime(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Reverter: tornar a coluna data_validade NOT NULL novamente
    # Nota: se houver valores NULL no banco, isso falhará
    op.alter_column('produto_lotes', 'data_validade',
                    existing_type=sa.DateTime(),
                    nullable=False)
