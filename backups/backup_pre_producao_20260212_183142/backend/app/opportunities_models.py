"""
Modelo de Oportunidades - FASE 2: Métricas de Oportunidade

Este modelo armazena oportunidades identificadas para métricas, relatórios e aprendizado futuro.
NÃO integra com IA. NÃO gera sugestões automaticamente.

Apenas estrutura de dados para rastreamento de oportunidades de negócio.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.base_models import BaseTenantModel


class TipoOportunidade(str, enum.Enum):
    """
    Tipos de oportunidade de venda.
    
    - CROSS_SELL: Venda cruzada (produtos complementares)
    - UP_SELL: Venda de valor superior (upgrade)
    - RECORRENCIA: Oportunidade de recompra recorrente
    """
    CROSS_SELL = "cross_sell"
    UP_SELL = "up_sell"
    RECORRENCIA = "recorrencia"


class Opportunity(BaseTenantModel):
    """
    Oportunidade de negócio identificada.
    
    Armazena oportunidades para análise posterior, relatórios e aprendizado.
    Isolamento total por tenant garantido via BaseTenantModel.
    
    Campos:
    - tenant_id: Isolamento multi-tenant (herdado de BaseTenantModel)
    - cliente_id: Cliente relacionado à oportunidade (opcional)
    - contexto: Contexto onde a oportunidade foi identificada (padrão: "PDV")
    - tipo: Tipo de oportunidade (cross_sell, up_sell, recorrencia)
    - produto_origem_id: Produto que originou a oportunidade
    - produto_sugerido_id: Produto sugerido como oportunidade
    - extra_data: Dados adicionais em formato JSON (score, regras, etc)
    - created_at: Data de criação (herdado de BaseTenantModel)
    """
    __tablename__ = "opportunities"
    
    # cliente_id opcional - pode não estar associado a um cliente específico
    cliente_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Cliente relacionado à oportunidade (opcional)"
    )
    
    # contexto onde a oportunidade foi identificada
    contexto = Column(
        String(50),
        nullable=False,
        default="PDV",
        comment="Contexto de origem (PDV, ecommerce, etc)"
    )
    
    # tipo de oportunidade (enum)
    tipo = Column(
        SQLEnum(TipoOportunidade, name="tipo_oportunidade_enum", create_type=True),
        nullable=False,
        index=True,
        comment="Tipo de oportunidade (cross_sell, up_sell, recorrencia)"
    )
    
    # produtos relacionados
    produto_origem_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Produto que originou a oportunidade"
    )
    
    produto_sugerido_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Produto sugerido como oportunidade"
    )
    
    # dados adicionais (JSON flexível)
    extra_data = Column(
        JSONB,
        nullable=True,
        comment="Dados adicionais (score, regras aplicadas, contexto adicional)"
    )
    
    # Índices compostos para queries eficientes
    __table_args__ = (
        # Índice para filtrar por tenant + tipo
        Index('ix_opportunities_tenant_tipo', 'tenant_id', 'tipo'),
        
        # Índice para filtrar por tenant + data (relatórios temporais)
        Index('ix_opportunities_tenant_created', 'tenant_id', 'created_at'),
        
        # Índice para filtrar por tenant + cliente
        Index('ix_opportunities_tenant_cliente', 'tenant_id', 'cliente_id'),
        
        # Índice para filtrar por tenant + contexto
        Index('ix_opportunities_tenant_contexto', 'tenant_id', 'contexto'),
    )
    
    def __repr__(self):
        return f"<Opportunity(id={self.id}, tenant_id={self.tenant_id}, tipo={self.tipo}, contexto={self.contexto})>"
