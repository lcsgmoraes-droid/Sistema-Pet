"""create opportunities table

Revision ID: 20260127_create_opportunities
Revises: 20260127_create_feature_flags
Create Date: 2026-01-27 02:00:00.000000

FASE 2 - Métricas de Oportunidade

Cria tabela de oportunidades para rastreamento e análise.
NÃO integra com IA. NÃO gera eventos automaticamente.
Apenas estrutura de dados persistente para métricas futuras.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '20260127_create_opportunities'
down_revision: Union[str, Sequence[str], None] = '20260127_create_feature_flags'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cria tabela opportunities com isolamento multi-tenant.
    
    Estrutura:
    - Herda campos de BaseTenantModel (id, tenant_id, created_at, updated_at)
    - Campos específicos de oportunidade
    - Índices para performance e isolamento
    """
    
    # Criar enum para tipo de oportunidade
    tipo_oportunidade_enum = sa.Enum(
        'cross_sell',
        'up_sell',
        'recorrencia',
        name='tipo_oportunidade_enum',
        create_type=True
    )
    
    # Criar tabela opportunities
    op.create_table(
        'opportunities',
        
        # ID primário (Identity always)
        sa.Column('id', sa.Integer(), sa.Identity(always=True), primary_key=True),
        
        # tenant_id (obrigatório, indexado) - Isolamento multi-tenant
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False, index=True),
        
        # cliente_id (opcional)
        sa.Column('cliente_id', UUID(as_uuid=True), nullable=True),
        
        # contexto (padrão: "PDV")
        sa.Column('contexto', sa.String(50), nullable=False, server_default='PDV'),
        
        # tipo (enum)
        sa.Column('tipo', tipo_oportunidade_enum, nullable=False),
        
        # produtos relacionados
        sa.Column('produto_origem_id', UUID(as_uuid=True), nullable=False),
        sa.Column('produto_sugerido_id', UUID(as_uuid=True), nullable=False),
        
        # timestamps (herdados de BaseTenantModel)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # extra_data (JSONB)
        sa.Column('extra_data', JSONB, nullable=True),
    )
    
    # Criar índices compostos para queries eficientes
    
    # Índice: tenant_id + tipo (filtrar oportunidades por tipo dentro do tenant)
    op.create_index(
        'ix_opportunities_tenant_tipo',
        'opportunities',
        ['tenant_id', 'tipo']
    )
    
    # Índice: tenant_id + created_at (relatórios temporais)
    op.create_index(
        'ix_opportunities_tenant_created',
        'opportunities',
        ['tenant_id', 'created_at']
    )
    
    # Índice: tenant_id + cliente_id (oportunidades por cliente)
    op.create_index(
        'ix_opportunities_tenant_cliente',
        'opportunities',
        ['tenant_id', 'cliente_id']
    )
    
    # Índice: tenant_id + contexto (oportunidades por contexto)
    op.create_index(
        'ix_opportunities_tenant_contexto',
        'opportunities',
        ['tenant_id', 'contexto']
    )
    
    # Índice adicional em cliente_id para FK (mesmo sendo nullable)
    op.create_index(
        'ix_opportunities_cliente_id',
        'opportunities',
        ['cliente_id']
    )


def downgrade() -> None:
    """
    Remove tabela opportunities e enum.
    Rollback seguro.
    """
    
    # Remover índices
    op.drop_index('ix_opportunities_cliente_id', table_name='opportunities')
    op.drop_index('ix_opportunities_tenant_contexto', table_name='opportunities')
    op.drop_index('ix_opportunities_tenant_cliente', table_name='opportunities')
    op.drop_index('ix_opportunities_tenant_created', table_name='opportunities')
    op.drop_index('ix_opportunities_tenant_tipo', table_name='opportunities')
    op.drop_index('ix_opportunities_tenant_id', table_name='opportunities')  # Índice padrão do BaseTenantModel
    
    # Remover tabela
    op.drop_table('opportunities')
    
    # Remover enum
    sa.Enum(name='tipo_oportunidade_enum').drop(op.get_bind(), checkfirst=True)
