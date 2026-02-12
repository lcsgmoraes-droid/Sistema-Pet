"""
Modelo de Eventos de Oportunidade - Persistência de Ações do Operador

FASE 2 - Registro Persistente de Eventos de Oportunidade

Este modelo armazena todos os eventos gerados por ações explícitas do operador.
Um evento é registrado APENAS quando há interação consciente (clique em botão).

Silêncio/inatividade NUNCA gera evento.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Enum as SQLEnum, UUID
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.sql import func
import enum
from app.base_models import BaseTenantModel


class OpportunityEventTypeEnum(str, enum.Enum):
    """
    Tipos de eventos de oportunidade persistidos.
    
    - CONVERTIDA: Operador clicou em "Adicionar" (aceita sugestão)
    - REFINADA: Operador clicou em "Alternativa" (rejeita, quer outra)
    - REJEITADA: Operador clicou em "Ignorar" (rejeita sem alternativa)
    """
    CONVERTIDA = "oportunidade_convertida"
    REFINADA = "oportunidade_refinada"
    REJEITADA = "oportunidade_rejeitada"


class OpportunityEvent(BaseTenantModel):
    """
    Evento de oportunidade gerado por ação explícita do operador.
    
    Armazena APENAS ações conscientes do operador do caixa:
    - Clique no botão "Adicionar"
    - Clique no botão "Alternativa"
    - Clique no botão "Ignorar"
    
    NUNCA armazena:
    - Silêncio/inatividade
    - Visualização de painel
    - Timeout
    - Ações automáticas
    
    Campos:
    - tenant_id: Isolamento multi-tenant (herdado de BaseTenantModel)
    - opportunity_id: ID da oportunidade relacionada (referência lógica)
    - event_type: Tipo de evento (enum)
    - user_id: ID do operador que disparou o evento
    - contexto: Contexto da origem (padrão: "PDV")
    - extra_data: Dados adicionais do evento em JSON
    - created_at: Data de criação (herdado de BaseTenantModel)
    """
    __tablename__ = "opportunity_events"
    
    # Referência lógica à oportunidade (não FK estrita para flexibilidade)
    opportunity_id = Column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="ID da oportunidade relacionada"
    )
    
    # Tipo de evento disparado
    event_type = Column(
        SQLEnum(OpportunityEventTypeEnum, name="opportunity_event_type_enum", create_type=True),
        nullable=False,
        index=True,
        comment="Tipo de evento (convertida, refinada, rejeitada)"
    )
    
    # Operador que disparou o evento
    user_id = Column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        comment="ID do operador que disparou o evento"
    )
    
    # Contexto de origem
    contexto = Column(
        String(50),
        nullable=False,
        default="PDV",
        comment="Contexto de origem (PDV, ecommerce, etc)"
    )
    
    # Metadados adicionais do evento
    extra_data = Column(
        JSONB,
        nullable=True,
        comment="Dados adicionais do evento"
    )
    
    # Índices compostos para queries eficientes
    __table_args__ = (
        # Índice: tenant_id + event_type (filtrar eventos por tipo dentro do tenant)
        Index('ix_opportunity_events_tenant_type', 'tenant_id', 'event_type'),
        
        # Índice: tenant_id + created_at (eventos por período dentro do tenant)
        Index('ix_opportunity_events_tenant_created', 'tenant_id', 'created_at'),
        
        # Índice: tenant_id + user_id (eventos por operador dentro do tenant)
        Index('ix_opportunity_events_tenant_user', 'tenant_id', 'user_id'),
        
        # Índice: opportunity_id (correlacionar com oportunidade)
        Index('ix_opportunity_events_opportunity_id', 'opportunity_id'),
    )
    
    def __repr__(self):
        return f"<OpportunityEvent(id={self.id}, tenant_id={self.tenant_id}, event_type={self.event_type}, opportunity_id={self.opportunity_id})>"
