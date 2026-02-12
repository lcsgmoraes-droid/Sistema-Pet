"""add_cascade_to_recebimentos_and_extrato_fkeys

Revision ID: a3d7e5569b20
Revises: c63c50f07608
Create Date: 2026-01-29 22:39:53.799494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d7e5569b20'
down_revision: Union[str, Sequence[str], None] = 'c63c50f07608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Atualizar recebimentos.conta_receber_id para CASCADE
    op.drop_constraint('recebimentos_conta_receber_id_fkey', 'recebimentos', type_='foreignkey')
    op.create_foreign_key(
        'recebimentos_conta_receber_id_fkey',
        'recebimentos', 'contas_receber',
        ['conta_receber_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # 2. Atualizar extrato_bancario_item.conta_receber_id para SET NULL (se tabela existir)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'extrato_bancario_item' in inspector.get_table_names():
        op.drop_constraint('extrato_bancario_item_conta_receber_id_fkey', 'extrato_bancario_item', type_='foreignkey')
        op.create_foreign_key(
            'extrato_bancario_item_conta_receber_id_fkey',
            'extrato_bancario_item', 'contas_receber',
            ['conta_receber_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Reverter recebimentos.conta_receber_id
    op.drop_constraint('recebimentos_conta_receber_id_fkey', 'recebimentos', type_='foreignkey')
    op.create_foreign_key(
        'recebimentos_conta_receber_id_fkey',
        'recebimentos', 'contas_receber',
        ['conta_receber_id'], ['id']
    )
    
    # 2. Reverter extrato_bancario_item.conta_receber_id (se tabela existir)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'extrato_bancario_item' in inspector.get_table_names():
        op.drop_constraint('extrato_bancario_item_conta_receber_id_fkey', 'extrato_bancario_item', type_='foreignkey')
        op.create_foreign_key(
            'extrato_bancario_item_conta_receber_id_fkey',
            'extrato_bancario_item', 'contas_receber',
            ['conta_receber_id'], ['id']
        )
