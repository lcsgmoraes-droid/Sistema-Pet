"""add_missing_columns_to_configuracoes_entrega

Revision ID: 20260216_fix_config_entrega
Revises: 20260216_comissoes_tenant
Create Date: 2026-02-16 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260216_fix_config_entrega'
down_revision: Union[str, Sequence[str], None] = '20260216_comissoes_tenant'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to configuracoes_entrega table."""
    
    # Add entregador_padrao_id
    op.add_column(
        'configuracoes_entrega',
        sa.Column('entregador_padrao_id', sa.Integer(), nullable=True)
    )
    
    # Add FK constraint for entregador_padrao_id
    op.create_foreign_key(
        'fk_configuracoes_entrega_entregador',
        'configuracoes_entrega', 'clientes',
        ['entregador_padrao_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add address fields
    op.add_column('configuracoes_entrega', sa.Column('logradouro', sa.String(300), nullable=True))
    op.add_column('configuracoes_entrega', sa.Column('cep', sa.String(9), nullable=True))
    op.add_column('configuracoes_entrega', sa.Column('numero', sa.String(20), nullable=True))
    op.add_column('configuracoes_entrega', sa.Column('complemento', sa.String(100), nullable=True))
    op.add_column('configuracoes_entrega', sa.Column('bairro', sa.String(100), nullable=True))
    op.add_column('configuracoes_entrega', sa.Column('cidade', sa.String(100), nullable=True))
    op.add_column('configuracoes_entrega', sa.Column('estado', sa.String(2), nullable=True))


def downgrade() -> None:
    """Remove added columns from configuracoes_entrega table."""
    op.drop_constraint('fk_configuracoes_entrega_entregador', 'configuracoes_entrega', type_='foreignkey')
    op.drop_column('configuracoes_entrega', 'estado')
    op.drop_column('configuracoes_entrega', 'cidade')
    op.drop_column('configuracoes_entrega', 'bairro')
    op.drop_column('configuracoes_entrega', 'complemento')
    op.drop_column('configuracoes_entrega', 'numero')
    op.drop_column('configuracoes_entrega', 'cep')
    op.drop_column('configuracoes_entrega', 'logradouro')
    op.drop_column('configuracoes_entrega', 'entregador_padrao_id')
