"""add_tenant_id_to_arquivos_extrato

Revision ID: b8a7669f8249
Revises: f964f0d7ae7e
Create Date: 2026-01-27 14:39:04.572571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8a7669f8249'
down_revision: Union[str, Sequence[str], None] = 'f964f0d7ae7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tenant_id à tabela arquivos_extrato_importados"""
    from sqlalchemy.dialects.postgresql import UUID
    
    # Adicionar coluna tenant_id
    op.add_column('arquivos_extrato_importados', sa.Column(
        'tenant_id',
        UUID(as_uuid=True),
        nullable=False
    ))
    
    # Criar foreign key para tenants
    op.create_foreign_key(
        'fk_arquivos_extrato_importados_tenant',
        'arquivos_extrato_importados', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Criar índice
    op.create_index(
        'ix_arquivos_extrato_importados_tenant_id',
        'arquivos_extrato_importados',
        ['tenant_id']
    )
    
    # Adicionar created_at e updated_at (compatibilidade com BaseTenantModel)
    op.add_column('arquivos_extrato_importados', sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    op.add_column('arquivos_extrato_importados', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    print("✅ arquivos_extrato_importados agora está isolado por tenant")


def downgrade() -> None:
    """Remove tenant_id de arquivos_extrato_importados"""
    op.drop_index('ix_arquivos_extrato_importados_tenant_id')
    op.drop_constraint('fk_arquivos_extrato_importados_tenant', 'arquivos_extrato_importados', type_='foreignkey')
    op.drop_column('arquivos_extrato_importados', 'tenant_id')
    op.drop_column('arquivos_extrato_importados', 'updated_at')
    op.drop_column('arquivos_extrato_importados', 'created_at')
