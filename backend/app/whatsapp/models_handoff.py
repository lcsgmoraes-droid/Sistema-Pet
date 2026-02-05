"""
Sprint 4 - Human Handoff Models
Tabelas para gerenciamento de transferência para atendentes humanos
"""
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db import Base


class WhatsAppAgent(Base):
    """Atendentes humanos disponíveis para WhatsApp"""
    __tablename__ = "whatsapp_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    email = Column(String(200))
    status = Column(String(50), default="offline")  # online, offline, busy, away
    max_concurrent_chats = Column(Integer, default=5)
    current_chats = Column(Integer, default=0)
    
    # Configurações
    auto_assign = Column(Boolean, default=True)
    receive_notifications = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # TODO: Descomentar quando relationship no Tenant estiver configurado
    # tenant = relationship("Tenant", back_populates="whatsapp_agents")
    tenant = relationship("Tenant")  # Sem back_populates por enquanto
    user = relationship("User")
    handoffs = relationship("WhatsAppHandoff", back_populates="agent")


class WhatsAppHandoff(Base):
    """Transferências de conversa para atendente humano"""
    __tablename__ = "whatsapp_handoffs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_ia_sessions.id"), nullable=False)
    
    phone_number = Column(String(20), nullable=False)
    customer_name = Column(String(200))
    
    # Motivo da transferência
    reason = Column(String(50), nullable=False)  
    # auto_sentiment (raiva/frustração detectada)
    # manual_request (cliente pediu atendente)
    # auto_repeat (mensagem repetida 3x)
    # auto_timeout (bot não conseguiu resolver)
    # auto_complex (pergunta muito complexa)
    
    reason_details = Column(Text)  # Detalhes do motivo
    
    # Análise de sentimento
    sentiment_score = Column(Numeric(3, 2))  # -1.0 (muito negativo) a 1.0 (muito positivo)
    sentiment_label = Column(String(20))  # positive, neutral, negative, very_negative
    
    # Prioridade
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    
    # Status
    status = Column(String(50), default="pending")  
    # pending (aguardando atendente)
    # assigned (atribuído mas não iniciado)
    # in_progress (atendente respondendo)
    # resolved (resolvido)
    # cancelled (cliente saiu)
    
    # Atendente
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("whatsapp_agents.id"))
    assigned_at = Column(DateTime)
    
    # Resolução
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    resolution_time_seconds = Column(Integer)  # Tempo até resolver
    
    # Avaliação (opcional)
    rating = Column(Integer)  # 1 a 5
    rating_feedback = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    session = relationship("WhatsAppSession", back_populates="handoffs")
    agent = relationship("WhatsAppAgent", back_populates="handoffs")
    notes = relationship("WhatsAppInternalNote", back_populates="handoff", cascade="all, delete-orphan")


class WhatsAppInternalNote(Base):
    """Notas internas dos atendentes sobre conversas"""
    __tablename__ = "whatsapp_internal_notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    handoff_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_handoffs.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_ia_sessions.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_agents.id"), nullable=False)
    
    note = Column(Text, nullable=False)
    note_type = Column(String(50), default="general")  # general, important, follow_up, warning
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    handoff = relationship("WhatsAppHandoff", back_populates="notes")
    session = relationship("WhatsAppSession")
    agent = relationship("WhatsAppAgent")


# Adicionar relationships nos models existentes
# Nota: Adicionar estas linhas nos models WhatsAppSession e Tenant

# Em WhatsAppSession:
# handoffs = relationship("WhatsAppHandoff", back_populates="session")

# Em Tenant:
# whatsapp_agents = relationship("WhatsAppAgent", back_populates="tenant")
