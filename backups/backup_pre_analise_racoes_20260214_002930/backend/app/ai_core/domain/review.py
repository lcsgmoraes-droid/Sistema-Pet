"""
Review Domain - Human-in-the-Loop Framework

Modelo de domínio para revisão humana de decisões de IA.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class DecisionReviewStatus(str, Enum):
    """
    Status de revisão de uma decisão de IA.
    
    Fluxo:
    PENDING → (humano revisa) → APPROVED | CORRECTED | REJECTED
    """
    PENDING = "pending"          # Aguardando revisão
    APPROVED = "approved"        # Decisão confirmada como correta
    CORRECTED = "corrected"      # Decisão foi corrigida pelo humano
    REJECTED = "rejected"        # Decisão foi totalmente rejeitada


class ReviewPriority(str, Enum):
    """
    Prioridade de uma revisão baseada na confiança e impacto.
    """
    LOW = "low"              # Confiança MEDIUM alta (70-79), baixo impacto
    MEDIUM = "medium"        # Confiança MEDIUM baixa (60-69)
    HIGH = "high"            # Confiança LOW (40-59)
    URGENT = "urgent"        # Confiança VERY_LOW (0-39) mas IA sugeriu algo


class ReviewQueueEntry(BaseModel):
    """
    Entrada na fila de revisão humana (Read Model - CQRS).
    
    NÃO é uma entidade de negócio que altera estado.
    É uma VIEW de decisões que precisam de atenção humana.
    
    Decisões com confiança MEDIUM ou LOW entram automaticamente.
    """
    # Identificação
    id: Optional[int] = None
    request_id: str = Field(..., description="ID da decisão original")
    decision_log_id: int = Field(..., description="FK para DecisionLog")
    
    # Multi-tenant
    tenant_id: int = Field(..., description="ID do tenant/usuário")
    
    # Contexto da decisão
    decision_type: str = Field(..., description="Tipo de decisão")
    decision_summary: str = Field(..., description="Resumo legível da decisão")
    
    # Confiança original
    confidence_score: int = Field(..., ge=0, le=100)
    confidence_level: str = Field(..., description="MEDIUM ou LOW")
    
    # Prioridade
    priority: ReviewPriority = Field(...)
    
    # Dados necessários para revisão
    context_data: Dict[str, Any] = Field(
        ...,
        description="Dados contextuais para o revisor (histórico, input, etc)"
    )
    ai_decision: Dict[str, Any] = Field(
        ...,
        description="Decisão sugerida pela IA"
    )
    ai_explanation: str = Field(
        ...,
        description="Explicação da IA"
    )
    
    # Status
    status: DecisionReviewStatus = Field(default=DecisionReviewStatus.PENDING)
    
    # Resultado da revisão (preenchido após revisão)
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_action: Optional[str] = None  # "approve", "correct", "reject"
    corrected_data: Optional[Dict[str, Any]] = None
    review_comment: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class HumanReviewFeedback(BaseModel):
    """
    Feedback estruturado do humano sobre uma decisão.
    
    Input para o ReviewService.submit_review()
    """
    request_id: str = Field(..., description="ID da decisão sendo revisada")
    reviewer_id: int = Field(..., description="ID do usuário que revisou")
    
    action: DecisionReviewStatus = Field(
        ...,
        description="Ação tomada: APPROVED, CORRECTED, REJECTED"
    )
    
    # Dados corrigidos (apenas se action=CORRECTED)
    corrected_decision: Optional[Dict[str, Any]] = Field(
        None,
        description="Decisão correta (substitui a decisão da IA)"
    )
    
    # Comentário explicativo (opcional)
    comment: Optional[str] = Field(
        None,
        max_length=1000,
        description="Comentário do revisor sobre a decisão"
    )
    
    # Contexto adicional
    review_timestamp: datetime = Field(default_factory=datetime.utcnow)
