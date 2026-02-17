"""
Sprint 4 - Human Handoff Schemas
Pydantic models para validação de requests/responses
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# ==================== WHATSAPP AGENT SCHEMAS ====================

class WhatsAppAgentCreate(BaseModel):
    """Criar novo agente"""
    name: str = Field(..., min_length=3, max_length=200)
    email: str = Field(..., min_length=5, max_length=200)
    status: str = Field(default="offline", pattern="^(online|offline|busy|away)$")
    max_concurrent_chats: Optional[int] = Field(default=5, ge=1, le=20)


class WhatsAppAgentUpdate(BaseModel):
    """Atualizar agente existente"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    email: Optional[str] = Field(None, min_length=5, max_length=200)
    status: Optional[str] = Field(None, pattern="^(online|offline|busy|away)$")
    max_concurrent_chats: Optional[int] = Field(None, ge=1, le=20)
    auto_assign: Optional[bool] = None
    receive_notifications: Optional[bool] = None


class WhatsAppAgentResponse(BaseModel):
    """Response de agente"""
    id: str
    tenant_id: str
    user_id: int
    name: str
    email: Optional[str]
    status: str
    max_concurrent_chats: int
    current_chats: int
    auto_assign: bool
    receive_notifications: bool
    created_at: datetime
    updated_at: datetime
    
    @field_validator('id', 'tenant_id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


# ==================== WHATSAPP HANDOFF SCHEMAS ====================

class WhatsAppHandoffCreate(BaseModel):
    """Criar novo handoff"""
    session_id: str
    phone_number: str
    customer_name: Optional[str] = None
    reason: str = Field(..., description="Motivo: manual, sentiment, repeat, timeout")
    reason_details: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")


class WhatsAppHandoffResponse(BaseModel):
    """Response de handoff"""
    id: str
    tenant_id: str
    session_id: str
    phone_number: str
    customer_name: Optional[str]
    reason: str
    reason_details: Optional[str]
    priority: str
    status: str
    assigned_agent_id: Optional[str]
    assigned_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    rating: Optional[int]
    rating_feedback: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    @field_validator('id', 'tenant_id', 'session_id', 'assigned_agent_id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        if v is None:
            return None
        if isinstance(v, UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class WhatsAppHandoffAssign(BaseModel):
    """Atribuir handoff a um agente"""
    agent_id: str


# ==================== INTERNAL NOTES ====================

class WhatsAppInternalNoteCreate(BaseModel):
    """Criar nota interna"""
    author_id: str
    content: str = Field(..., min_length=1, max_length=2000)
    note_type: Optional[str] = Field(default="info", pattern="^(info|warning|follow_up)$")


class WhatsAppInternalNoteResponse(BaseModel):
    """Response de nota interna"""
    id: str
    handoff_id: str
    author_id: str
    content: str
    note_type: str
    created_at: datetime
    
    @field_validator('id', 'handoff_id', 'author_id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


# ==================== DASHBOARD SCHEMAS ====================

class HandoffDashboardResponse(BaseModel):
    """Dashboard de handoffs"""
    pending: List[WhatsAppHandoffResponse]
    active: List[WhatsAppHandoffResponse]
    stats: Dict[str, Any]


class HandoffStats(BaseModel):
    """Estatísticas de handoffs"""
    total_handoffs: int
    pending_count: int
    active_count: int
    resolved_count: int
    available_agents: int
    avg_response_time_seconds: int


# ==================== LEGACY SCHEMAS (manter compatibilidade) ====================

class AgentBase(BaseModel):
    name: str
    email: Optional[str] = None
    max_concurrent_chats: int = 5
    auto_assign: bool = True
    receive_notifications: bool = True


class AgentCreate(AgentBase):
    user_id: str


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None  # online, offline, busy, away
    max_concurrent_chats: Optional[int] = None
    auto_assign: Optional[bool] = None
    receive_notifications: Optional[bool] = None


class AgentResponse(AgentBase):
    id: str
    tenant_id: str
    user_id: str
    status: str
    current_chats: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AgentStats(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    current_chats: int
    max_chats: int
    total_handoffs_today: int
    avg_resolution_time_minutes: float
    rating_avg: Optional[float] = None


# ==================== HANDOFF SCHEMAS ====================

class HandoffBase(BaseModel):
    reason: str = Field(..., description="auto_sentiment, manual_request, auto_repeat, auto_timeout, auto_complex")
    reason_details: Optional[str] = None
    priority: str = "medium"  # low, medium, high, urgent


class HandoffCreate(HandoffBase):
    session_id: str
    phone_number: str
    customer_name: Optional[str] = None
    sentiment_score: Optional[Decimal] = None
    sentiment_label: Optional[str] = None


class HandoffUpdate(BaseModel):
    status: Optional[str] = None  # assigned, in_progress, resolved, cancelled
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    rating_feedback: Optional[str] = None


class HandoffResponse(HandoffBase):
    id: str
    tenant_id: str
    session_id: str
    phone_number: str
    customer_name: Optional[str]
    sentiment_score: Optional[Decimal]
    sentiment_label: Optional[str]
    status: str
    assigned_to: Optional[str]
    assigned_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    resolution_time_seconds: Optional[int]
    rating: Optional[int]
    rating_feedback: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Dados adicionais (computados)
    agent_name: Optional[str] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HandoffWithMessages(HandoffResponse):
    """Handoff com histórico de mensagens"""
    messages: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []


# ==================== INTERNAL NOTE SCHEMAS ====================

class InternalNoteCreate(BaseModel):
    note: str
    note_type: str = "general"  # general, important, follow_up, warning


class InternalNoteResponse(InternalNoteCreate):
    id: str
    handoff_id: str
    session_id: str
    agent_id: str
    agent_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== DASHBOARD SCHEMAS ====================

class ConversationListItem(BaseModel):
    """Item da lista de conversas no dashboard"""
    session_id: str
    phone_number: str
    customer_name: Optional[str]
    status: str  # bot, human, waiting_human, closed
    last_message: str
    last_message_at: datetime
    message_count: int
    unread_count: int = 0
    
    # Handoff info (se existir)
    handoff_id: Optional[str] = None
    handoff_status: Optional[str] = None
    handoff_priority: Optional[str] = None
    sentiment_label: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None


class DashboardStats(BaseModel):
    """Estatísticas do dashboard"""
    pending_handoffs: int
    active_conversations: int
    agents_online: int
    avg_wait_time_minutes: float
    today_handoffs: int
    today_resolved: int
    resolution_rate: float


class TakeConversationRequest(BaseModel):
    """Request para atendente pegar conversa"""
    agent_id: str


class SendAgentMessageRequest(BaseModel):
    """Request para atendente enviar mensagem"""
    message: str
    agent_id: str


class ResolveHandoffRequest(BaseModel):
    """Request para marcar handoff como resolvido"""
    resolution_notes: str
    send_rating_request: bool = True


class RateConversationRequest(BaseModel):
    """Request para cliente avaliar atendimento"""
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


# ==================== BOT ASSIST SCHEMAS ====================

class BotAssistSuggestion(BaseModel):
    """Sugestão do bot assist para atendente"""
    type: str  # quick_reply, product_info, customer_history, similar_question
    title: str
    content: str
    action: Optional[str] = None  # Ação que pode ser executada
    metadata: Optional[Dict[str, Any]] = None


class BotAssistRequest(BaseModel):
    """Request para buscar sugestões do bot assist"""
    session_id: str
    context: Optional[str] = None
    query: Optional[str] = None


class BotAssistResponse(BaseModel):
    """Response com sugestões do bot assist"""
    suggestions: List[BotAssistSuggestion]
    customer_summary: Optional[Dict[str, Any]] = None
    recent_products: List[Dict[str, Any]] = []
    quick_actions: List[Dict[str, str]] = []


# ==================== SENTIMENT ANALYSIS SCHEMAS ====================

class SentimentAnalysisResult(BaseModel):
    """Resultado de análise de sentimento"""
    score: Decimal = Field(..., ge=-1.0, le=1.0)
    label: str  # very_negative, negative, neutral, positive, very_positive
    confidence: float = Field(..., ge=0.0, le=1.0)
    emotions: Dict[str, float] = {}
    triggers: List[str] = []  # Keywords que triggeram sentimento negativo
    should_handoff: bool = False
    handoff_reason: Optional[str] = None
