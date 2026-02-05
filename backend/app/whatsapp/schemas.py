"""
WhatsApp Schemas - Pydantic

Schemas de request/response para API WhatsApp
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, time
from enum import Enum
from uuid import UUID


# ============================================================================
# ENUMS
# ============================================================================

class SessionStatus(str, Enum):
    """Status de sessão"""
    BOT = "bot"
    HUMAN = "human"
    WAITING_HUMAN = "waiting_human"
    CLOSED = "closed"


class MessageTipo(str, Enum):
    """Tipo de mensagem"""
    RECEBIDA = "recebida"
    ENVIADA = "enviada"


class ToneType(str, Enum):
    """Tom da conversa"""
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CASUAL = "casual"


class ProviderType(str, Enum):
    """Provider WhatsApp"""
    DIALOG_360 = "360dialog"
    Z_API = "z-api"
    TWILIO = "twilio"


# ============================================================================
# CONFIG SCHEMAS
# ============================================================================

class TenantWhatsAppConfigBase(BaseModel):
    """Base config"""
    provider: ProviderType = ProviderType.DIALOG_360
    api_key: Optional[str] = None
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    openai_api_key: Optional[str] = None
    model_preference: str = "gpt-4o-mini"
    auto_response_enabled: bool = True
    human_handoff_keywords: Optional[str] = None
    working_hours_start: Optional[time] = None
    working_hours_end: Optional[time] = None
    notificacoes_entrega_enabled: bool = False
    bot_name: Optional[str] = None
    greeting_message: Optional[str] = None
    tone: ToneType = ToneType.FRIENDLY


class TenantWhatsAppConfigCreate(TenantWhatsAppConfigBase):
    """Schema para criar config"""
    tenant_id: str


class TenantWhatsAppConfigUpdate(BaseModel):
    """Schema para atualizar config (campos opcionais)"""
    provider: Optional[ProviderType] = None
    api_key: Optional[str] = None
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    openai_api_key: Optional[str] = None
    model_preference: Optional[str] = None
    auto_response_enabled: Optional[bool] = None
    human_handoff_keywords: Optional[str] = None
    working_hours_start: Optional[time] = None
    working_hours_end: Optional[time] = None
    notificacoes_entrega_enabled: Optional[bool] = None
    bot_name: Optional[str] = None
    greeting_message: Optional[str] = None
    tone: Optional[ToneType] = None


class TenantWhatsAppConfigResponse(TenantWhatsAppConfigBase):
    """Schema de resposta"""
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    
    @field_validator('id', 'tenant_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Converte UUID para string"""
        if isinstance(v, UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


# ============================================================================
# SESSION SCHEMAS
# ============================================================================

class WhatsAppSessionBase(BaseModel):
    """Base session"""
    phone_number: str
    status: SessionStatus = SessionStatus.BOT
    cliente_id: Optional[str] = None
    assigned_to: Optional[str] = None
    context: Optional[str] = None
    last_intent: Optional[str] = None


class WhatsAppSessionCreate(WhatsAppSessionBase):
    """Schema para criar sessão"""
    tenant_id: str


class WhatsAppSessionUpdate(BaseModel):
    """Schema para atualizar sessão"""
    status: Optional[SessionStatus] = None
    assigned_to: Optional[str] = None
    context: Optional[str] = None
    last_intent: Optional[str] = None
    closed_at: Optional[datetime] = None


class WhatsAppSessionResponse(WhatsAppSessionBase):
    """Schema de resposta"""
    id: str
    tenant_id: str
    message_count: int
    started_at: datetime
    last_message_at: datetime
    closed_at: Optional[datetime]
    
    @field_validator('id', 'tenant_id', 'cliente_id', 'assigned_to', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Converte UUID para string"""
        if isinstance(v, UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class WhatsAppSessionWithMessages(WhatsAppSessionResponse):
    """Sessão com mensagens"""
    messages: List["WhatsAppMessageResponse"] = []


# ============================================================================
# MESSAGE SCHEMAS
# ============================================================================

class WhatsAppMessageBase(BaseModel):
    """Base message"""
    tipo: MessageTipo
    conteudo: str
    whatsapp_message_id: Optional[str] = None
    intent_detected: Optional[str] = None
    model_used: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    processing_time_ms: Optional[int] = None
    metadata: Optional[str] = None
    sent_by_user_id: Optional[str] = None


class WhatsAppMessageCreate(WhatsAppMessageBase):
    """Schema para criar mensagem"""
    session_id: str
    tenant_id: str


class WhatsAppMessageResponse(WhatsAppMessageBase):
    """Schema de resposta"""
    id: str
    session_id: str
    tenant_id: str
    created_at: datetime
    
    @field_validator('id', 'session_id', 'tenant_id', 'sent_by_user_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Converte UUID para string"""
        if isinstance(v, UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


# ============================================================================
# WEBHOOK SCHEMAS (360dialog)
# ============================================================================

class WebhookMessage(BaseModel):
    """Mensagem recebida via webhook"""
    from_: str = Field(..., alias="from")
    id: str
    text: Optional[Dict[str, Any]] = None
    type: str
    timestamp: str


class WebhookContact(BaseModel):
    """Contato do webhook"""
    profile: Dict[str, str]
    wa_id: str


class WebhookEntry(BaseModel):
    """Entry do webhook"""
    id: str
    changes: List[Dict[str, Any]]


class Webhook360DialogPayload(BaseModel):
    """Payload completo do webhook 360dialog"""
    object: str
    entry: List[WebhookEntry]


# ============================================================================
# SEND MESSAGE SCHEMAS
# ============================================================================

class SendMessageRequest(BaseModel):
    """Request para enviar mensagem"""
    phone: str
    message: str
    tipo: str = "texto"  # texto, imagem, documento


class SendMessageResponse(BaseModel):
    """Response do envio"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# INBOX SCHEMAS
# ============================================================================

class InboxConversationSummary(BaseModel):
    """Resumo de conversa para inbox"""
    id: str
    cliente_nome: Optional[str] = None
    phone_number: str
    status: SessionStatus
    last_message_preview: str
    message_count: int
    last_message_at: datetime
    assigned_to_name: Optional[str] = None
    unread_count: int = 0
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Converte UUID para string"""
        if isinstance(v, UUID):
            return str(v)
        return v


class InboxFilterRequest(BaseModel):
    """Filtros para inbox"""
    status: Optional[SessionStatus] = None
    assigned_to: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


class TakeoverRequest(BaseModel):
    """Request para assumir conversa"""
    user_id: str


class SendManualMessageRequest(BaseModel):
    """Envio manual pelo atendente"""
    message: str
    user_id: str


# ============================================================================
# METRICS SCHEMAS
# ============================================================================

class WhatsAppMetricCreate(BaseModel):
    """Criar métrica"""
    tenant_id: str
    metric_type: str
    value: float
    metadata: Optional[str] = None


class WhatsAppMetricResponse(BaseModel):
    """Response de métrica"""
    id: str
    tenant_id: str
    metric_type: str
    value: float
    metadata: Optional[str]
    timestamp: datetime
    
    @field_validator('id', 'tenant_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Converte UUID para string"""
        if isinstance(v, UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class MetricsSummary(BaseModel):
    """Resumo de métricas"""
    total_messages: int
    bot_handled: int
    human_handled: int
    avg_response_time_seconds: float
    conversion_rate: float
    total_cost_usd: float


class WhatsAppStatsResponse(BaseModel):
    """Response de estatísticas do WhatsApp"""
    total_sessions: int
    active_sessions: int
    total_messages: int
    messages_sent: int
    messages_received: int
    avg_response_time_seconds: Optional[float] = None
    bot_handled_count: int = 0
    human_handled_count: int = 0


# Update forward refs
WhatsAppSessionWithMessages.model_rebuild()
