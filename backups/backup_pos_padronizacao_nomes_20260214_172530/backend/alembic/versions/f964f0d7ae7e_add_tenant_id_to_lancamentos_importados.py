"""add_tenant_id_to_lancamentos_importados

Revision ID: f964f0d7ae7e
Revises: 1b6d197509be
Create Date: 2026-01-27 14:36:17.472402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f964f0d7ae7e'
down_revision: Union[str, Sequence[str], None] = '1b6d197509be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tenant_id à tabela lancamentos_importados"""
    from sqlalchemy.dialects.postgresql import UUID
    
    # Adicionar coluna tenant_id
    op.add_column('lancamentos_importados', sa.Column(
        'tenant_id',
        UUID(as_uuid=True),
        nullable=False
    ))
    
    # Criar foreign key para tenants
    op.create_foreign_key(
        'fk_lancamentos_importados_tenant',
        'lancamentos_importados', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Criar índice
    op.create_index(
        'ix_lancamentos_importados_tenant_id',
        'lancamentos_importados',
        ['tenant_id']
    )
    
    # Adicionar created_at e updated_at (compatibilidade com BaseTenantModel)
    op.add_column('lancamentos_importados', sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    op.add_column('lancamentos_importados', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    print("✅ lancamentos_importados agora está isolado por tenant")


def downgrade() -> None:
    """Remove tenant_id de lancamentos_importados"""
    op.drop_index('ix_lancamentos_importados_tenant_id')
    op.drop_constraint('fk_lancamentos_importados_tenant', 'lancamentos_importados', type_='foreignkey')
    op.drop_column('lancamentos_importados', 'tenant_id')
    op.drop_column('lancamentos_importados', 'updated_at')
    op.drop_column('lancamentos_importados', 'created_at')
