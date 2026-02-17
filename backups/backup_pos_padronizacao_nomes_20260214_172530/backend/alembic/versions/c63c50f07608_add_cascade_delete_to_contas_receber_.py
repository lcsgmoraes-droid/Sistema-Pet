"""add_cascade_delete_to_contas_receber_venda_fkey

Revision ID: c63c50f07608
Revises: bb1be66338a4
Create Date: 2026-01-29 22:25:49.221794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c63c50f07608'
down_revision: Union[str, Sequence[str], None] = 'bb1be66338a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove a constraint antiga
    op.drop_constraint('contas_receber_venda_id_fkey', 'contas_receber', type_='foreignkey')
    
    # Adiciona a constraint com CASCADE
    op.create_foreign_key(
        'contas_receber_venda_id_fkey',
        'contas_receber', 'vendas',
        ['venda_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove a constraint com CASCADE
    op.drop_constraint('contas_receber_venda_id_fkey', 'contas_receber', type_='foreignkey')
    
    # Restaura a constraint sem CASCADE
    op.create_foreign_key(
        'contas_receber_venda_id_fkey',
        'contas_receber', 'vendas',
        ['venda_id'], ['id']
    )
