"""
Modelo de Segmentação de Clientes
Sistema de classificação e análise de clientes (RFM, LTV, etc.)

Schema baseado em RELATORIO_SCHEMA_TABELAS_ORFAS.md - Fase 5.4
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime

from app.db import Base


class ClienteSegmento(Base):
    """
    Segmentação de clientes com métricas JSONB flexíveis.
    Permite classificação (VIP, Ouro, Prata, etc.) com análise RFM e LTV.
    
    Estrutura JSONB em metricas:
    {
        "rfm_recencia": 30,
        "rfm_frequencia": 12,
        "rfm_valor": 5000.00,
        "ltv": 15000.00,
        "ticket_medio": 416.67,
        "ultima_compra": "2026-01-15"
    }
    
    ⚠️ NOTA: Um cliente só pode ter um segmento por tenant (constraint UNIQUE)
    """
    __tablename__ = "cliente_segmentos"
    __table_args__ = (
        Index('idx_cliente_segmentos_cliente_id', 'cliente_id'),
        Index('idx_cliente_segmentos_user_id', 'user_id'),
        Index('idx_cliente_segmentos_segmento', 'segmento'),
        Index('idx_cliente_segmentos_updated_at', 'updated_at'),
        Index('idx_cliente_segmentos_tenant', 'tenant_id'),
        Index('idx_cliente_segmentos_tenant_cliente', 'tenant_id', 'cliente_id'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Segmentação
    segmento = Column(String(50), nullable=False)  # Ex: 'VIP', 'Ouro', 'Prata', 'Bronze', 'Inativo'
    
    # Métricas flexíveis (JSONB)
    metricas = Column(JSONB, nullable=False)  # RFM, LTV, ticket médio, etc.
    tags = Column(JSONB, nullable=True)  # Tags adicionais: ['pet_lover', 'premium', 'fidelizado']
    
    observacoes = Column(Text, nullable=True)
    
    # Auditoria
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
