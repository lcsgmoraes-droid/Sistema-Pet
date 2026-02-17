"""add_tenant_to_ia_fluxo_tables

Revision ID: 20260216_ia_fluxo_tenant
Revises: 20260216_chat_tenant
Create Date: 2026-02-16 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_ia_fluxo_tenant'
down_revision = '20260216_chat_tenant'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas em projecao_fluxo_caixa
    op.add_column('projecao_fluxo_caixa', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projecao_fluxo_caixa', sa.Column('created_at', sa.DateTime(timezone=True), 
                                                     server_default=sa.text('now()'), nullable=True))
    op.add_column('projecao_fluxo_caixa', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                                     server_default=sa.text('now()'), nullable=True))
    
    # Preencher tenant_id
    op.execute("""
        UPDATE projecao_fluxo_caixa 
        SET tenant_id = (SELECT tenant_id FROM clientes LIMIT 1)
        WHERE tenant_id IS NULL
    """)
    
    # Criar índice
    op.create_index('ix_projecao_fluxo_caixa_tenant_id', 'projecao_fluxo_caixa', ['tenant_id'])
    
    # Adicionar colunas em indices_saude_caixa
    op.add_column('indices_saude_caixa', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('indices_saude_caixa', sa.Column('created_at', sa.DateTime(timezone=True), 
                                                    server_default=sa.text('now()'), nullable=True))
    op.add_column('indices_saude_caixa', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                                    server_default=sa.text('now()'), nullable=True))
    
    # Preencher tenant_id
    op.execute("""
        UPDATE indices_saude_caixa 
        SET tenant_id = (SELECT tenant_id FROM clientes LIMIT 1)
        WHERE tenant_id IS NULL
    """)
    
    # Criar índice
    op.create_index('ix_indices_saude_caixa_tenant_id', 'indices_saude_caixa', ['tenant_id'])


def downgrade():
    # Remover de indices_saude_caixa
    op.drop_index('ix_indices_saude_caixa_tenant_id', table_name='indices_saude_caixa')
    op.drop_column('indices_saude_caixa', 'updated_at')
    op.drop_column('indices_saude_caixa', 'created_at')
    op.drop_column('indices_saude_caixa', 'tenant_id')
    
    # Remover de projecao_fluxo_caixa
    op.drop_index('ix_projecao_fluxo_caixa_tenant_id', table_name='projecao_fluxo_caixa')
    op.drop_column('projecao_fluxo_caixa', 'updated_at')
    op.drop_column('projecao_fluxo_caixa', 'created_at')
    op.drop_column('projecao_fluxo_caixa', 'tenant_id')
