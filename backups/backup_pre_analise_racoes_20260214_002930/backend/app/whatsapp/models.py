"""
WhatsApp Models - SQLAlchemy

Models para integração WhatsApp + IA:
- TenantWhatsAppConfig: Configuração por tenant
- WhatsAppSession: Sessões de conversa
- WhatsAppMessage: Histórico de mensagens
- WhatsAppMetric: Métricas de uso
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey, Time
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db import Base


def generate_uuid():
    """Gera UUID como string"""
    return str(uuid.uuid4())


class TenantWhatsAppConfig(Base):
    """Configuração WhatsApp por Tenant"""
    __tablename__ = "tenant_whatsapp_config"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    # Provider Config
    provider = Column(String(50), default="360dialog")  # 360dialog, z-api, twilio
    api_key = Column(Text)
    phone_number = Column(String(20))
    webhook_url = Column(Text)
    webhook_secret = Column(Text)
    
    # IA Config
    openai_api_key = Column(Text)
    model_preference = Column(String(50), default="gpt-4o-mini")  # gpt-4o-mini, gpt-4.1
    
    # Business Rules
    auto_response_enabled = Column(Boolean, default=True)
    human_handoff_keywords = Column(Text)  # JSON array como texto
    working_hours_start = Column(Time)
    working_hours_end = Column(Time)
    
    # Notificações
    notificacoes_entrega_enabled = Column(Boolean, default=False)
    
    # Style & Tone
    bot_name = Column(String(100))
    greeting_message = Column(Text)
    tone = Column(String(50), default="friendly")  # friendly, formal, casual
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TenantWhatsAppConfig(tenant_id={self.tenant_id}, provider={self.provider})>"


class WhatsAppSession(Base):
    """Sessão de conversa WhatsApp"""
    __tablename__ = "whatsapp_ia_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    phone_number = Column(String(20), nullable=False)
    
    # Status
    status = Column(String(20), default="bot")  # bot, human, waiting_human, closed
    assigned_to = Column(Integer, ForeignKey("users.id"))  # User ID do atendente
    
    # Context
    context = Column(Text)  # JSON como texto (histórico de produtos mencionados, etc)
    last_intent = Column(String(100))  # Última intenção detectada
    message_count = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    # Relationships
    messages = relationship("WhatsAppMessage", back_populates="session", cascade="all, delete-orphan")
    handoffs = relationship("WhatsAppHandoff", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WhatsAppSession(id={self.id}, phone={self.phone_number}, status={self.status})>"


class WhatsAppMessage(Base):
    """Mensagem individual"""
    __tablename__ = "whatsapp_ia_messages"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("whatsapp_ia_sessions.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    # Message Info
    tipo = Column(String(10), nullable=False)  # recebida, enviada
    conteudo = Column(Text, nullable=False)
    
    # WhatsApp IDs
    whatsapp_message_id = Column(String(255))  # ID retornado pela API
    
    # IA Info (quando aplicável)
    intent_detected = Column(String(100))  # consulta_produto, criar_pedido, suporte, etc
    model_used = Column(String(50))  # gpt-4o-mini, gpt-4.1
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    processing_time_ms = Column(Integer)
    
    # Metadata (renomeado para evitar conflito com SQLAlchemy)
    message_metadata = Column(Text)  # JSON como texto
    
    # User (se enviada por humano)
    sent_by_user_id = Column(Integer, ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("WhatsAppSession", back_populates="messages")
    
    def __repr__(self):
        return f"<WhatsAppMessage(id={self.id}, tipo={self.tipo}, intent={self.intent_detected})>"


class WhatsAppMetric(Base):
    """Métricas de uso"""
    __tablename__ = "whatsapp_ia_metrics"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    # Metric Type
    metric_type = Column(String(50), nullable=False)  # message_count, ai_call, conversion, etc
    
    # Values
    value = Column(Float, nullable=False)
    metric_metadata = Column(Text)  # JSON como texto (renomeado para evitar conflito)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WhatsAppMetric(tenant_id={self.tenant_id}, type={self.metric_type}, value={self.value})>"
