"""add_tenant_id_to_produto_bling_sync_and_padroes_categorizacao_ia

Revision ID: 908f232111a4
Revises: 7b41c090e7bf
Create Date: 2026-01-27 14:29:33.125501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '908f232111a4'
down_revision: Union[str, Sequence[str], None] = '7b41c090e7bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    🔒 CORREÇÃO CRÍTICA DE SEGURANÇA MULTI-TENANT
    
    Adiciona tenant_id em tabelas de negócio que estavam sem isolamento:
    - produto_bling_sync (integração Bling por cliente)
    - padroes_categorizacao_ia (IA financeira por empresa)
    
    Estas tabelas DEVEM ter tenant_id para garantir:
    ✅ Isolamento de dados entre clientes
    ✅ Conformidade LGPD
    ✅ Segurança de integrações
    ✅ IA contextual por tenant
    """
    
    # ========================================
    # 1️⃣ PRODUTO_BLING_SYNC
    # ========================================
    print("🔧 Adicionando tenant_id em produto_bling_sync...")
    
    # Adicionar coluna tenant_id
    op.add_column('produto_bling_sync', 
        sa.Column('tenant_id', sa.UUID(), nullable=False)
    )
    
    # Foreign key para tenants
    op.create_foreign_key(
        'fk_produto_bling_sync_tenant',
        'produto_bling_sync', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Índice para performance de filtros por tenant
    op.create_index(
        'ix_produto_bling_sync_tenant_id',
        'produto_bling_sync',
        ['tenant_id']
    )
    
    print("✅ produto_bling_sync agora está isolado por tenant")
    
    # ========================================
    # 2️⃣ PADROES_CATEGORIZACAO_IA
    # ========================================
    print("🔧 Adicionando tenant_id em padroes_categorizacao_ia...")
    
    # Adicionar coluna tenant_id
    op.add_column('padroes_categorizacao_ia',
        sa.Column('tenant_id', sa.UUID(), nullable=False)
    )
    
    # Foreign key para tenants
    op.create_foreign_key(
        'fk_padroes_categorizacao_ia_tenant',
        'padroes_categorizacao_ia', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Índice para performance
    op.create_index(
        'ix_padroes_categorizacao_ia_tenant_id',
        'padroes_categorizacao_ia',
        ['tenant_id']
    )
    
    print("✅ padroes_categorizacao_ia agora está isolado por tenant")
    print("🔒 Sistema multi-tenant corrigido e seguro!")


def downgrade() -> None:
    """
    ⚠️ DOWNGRADE NÃO RECOMENDADO
    
    Remove isolamento multi-tenant (uso apenas em desenvolvimento)
    """
    
    # Remover índices
    op.drop_index('ix_padroes_categorizacao_ia_tenant_id', 'padroes_categorizacao_ia')
    op.drop_index('ix_produto_bling_sync_tenant_id', 'produto_bling_sync')
    
    # Remover foreign keys
    op.drop_constraint('fk_padroes_categorizacao_ia_tenant', 'padroes_categorizacao_ia', type_='foreignkey')
    op.drop_constraint('fk_produto_bling_sync_tenant', 'produto_bling_sync', type_='foreignkey')
    
    # Remover colunas
    op.drop_column('padroes_categorizacao_ia', 'tenant_id')
    op.drop_column('produto_bling_sync', 'tenant_id')
