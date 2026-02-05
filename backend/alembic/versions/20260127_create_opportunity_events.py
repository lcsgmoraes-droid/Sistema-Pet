"""create opportunity_events table

Revision ID: 20260127_opp_events
Revises: 20260127_create_opportunities
Create Date: 2026-01-27 03:00:00.000000

FASE 2 - Persistência de Eventos de Oportunidade

Cria tabela para armazenar APENAS eventos gerados por ações explícitas
do operador (cliques em botões do painel de oportunidades).

Silêncio/inatividade NUNCA gera evento.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '20260127_opp_events'
down_revision: Union[str, Sequence[str], None] = '20260127_create_opportunities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cria tabela opportunity_events com isolamento multi-tenant.
    
    Estrutura:
    - Herda campos de BaseTenantModel (id, tenant_id, created_at, updated_at)
    - Campos específicos de evento
    - Índices para performance e isolamento
    """
    
    # Criar enum para tipo de evento
    opportunity_event_type_enum = sa.Enum(
        'oportunidade_convertida',
        'oportunidade_refinada',
        'oportunidade_rejeitada',
        name='opportunity_event_type_enum',
        create_type=True
    )
    
    # Criar tabela opportunity_events
    op.create_table(
        'opportunity_events',
        
        # ID primário (Identity always)
        sa.Column('id', sa.Integer(), sa.Identity(always=True), primary_key=True),
        
        # tenant_id (obrigatório, indexado) - Isolamento multi-tenant
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False, index=True),
        
        # opportunity_id (referência lógica à oportunidade)
        sa.Column('opportunity_id', UUID(as_uuid=True), nullable=False),
        
        # event_type (enum - tipo de evento)
        sa.Column('event_type', opportunity_event_type_enum, nullable=False),
        
        # user_id (operador que disparou o evento)
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        
        # contexto (origem)
        sa.Column('contexto', sa.String(50), nullable=False, server_default='PDV'),
        
        # timestamps (herdados de BaseTenantModel)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # metadata (JSONB - dados adicionais do evento)
        sa.Column('metadata', JSONB, nullable=True),
    )
    
    # Criar índices compostos para queries eficientes
    
    # Índice: tenant_id + event_type
    op.create_index(
        'ix_opportunity_events_tenant_type',
        'opportunity_events',
        ['tenant_id', 'event_type']
    )
    
    # Índice: tenant_id + created_at
    op.create_index(
        'ix_opportunity_events_tenant_created',
        'opportunity_events',
        ['tenant_id', 'created_at']
    )
    
    # Índice: tenant_id + user_id
    op.create_index(
        'ix_opportunity_events_tenant_user',
        'opportunity_events',
        ['tenant_id', 'user_id']
    )
    
    # Índice: opportunity_id
    op.create_index(
        'ix_opportunity_events_opportunity_id',
        'opportunity_events',
        ['opportunity_id']
    )


def downgrade() -> None:
    """
    Remove tabela opportunity_events e enum.
    Rollback seguro.
    """
    
    # Remover índices
    op.drop_index('ix_opportunity_events_opportunity_id', table_name='opportunity_events')
    op.drop_index('ix_opportunity_events_tenant_user', table_name='opportunity_events')
    op.drop_index('ix_opportunity_events_tenant_created', table_name='opportunity_events')
    op.drop_index('ix_opportunity_events_tenant_type', table_name='opportunity_events')
    op.drop_index('ix_opportunity_events_tenant_id', table_name='opportunity_events')  # Índice padrão do BaseTenantModel
    
    # Remover tabela
    op.drop_table('opportunity_events')
    
    # Remover enum
    sa.Enum(name='opportunity_event_type_enum').drop(op.get_bind(), checkfirst=True)
