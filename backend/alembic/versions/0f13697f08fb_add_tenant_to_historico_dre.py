"""add_tenant_to_historico_dre

Revision ID: 0f13697f08fb
Revises: 5f3d34ae34b7
Create Date: 2026-01-27 14:41:29.765233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f13697f08fb'
down_revision: Union[str, Sequence[str], None] = '5f3d34ae34b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tenant_id e timestamps à tabela historico_atualizacao_dre"""
    from sqlalchemy.dialects.postgresql import UUID
    
    # Adicionar coluna tenant_id
    op.add_column('historico_atualizacao_dre', sa.Column(
        'tenant_id',
        UUID(as_uuid=True),
        nullable=False
    ))
    
    # Criar foreign key para tenants
    op.create_foreign_key(
        'fk_historico_dre_tenant',
        'historico_atualizacao_dre', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Criar índice
    op.create_index(
        'ix_historico_dre_tenant_id',
        'historico_atualizacao_dre',
        ['tenant_id']
    )
    
    # Adicionar created_at e updated_at
    op.add_column('historico_atualizacao_dre', sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    op.add_column('historico_atualizacao_dre', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    print("✅ historico_atualizacao_dre agora está isolado por tenant")


def downgrade() -> None:
    """Remove tenant_id e timestamps de historico_atualizacao_dre"""
    op.drop_index('ix_historico_dre_tenant_id')
    op.drop_constraint('fk_historico_dre_tenant', 'historico_atualizacao_dre', type_='foreignkey')
    op.drop_column('historico_atualizacao_dre', 'tenant_id')
    op.drop_column('historico_atualizacao_dre', 'updated_at')
    op.drop_column('historico_atualizacao_dre', 'created_at')
