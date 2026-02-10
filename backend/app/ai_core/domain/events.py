"""
Review Events - Eventos de domínio para Human-in-the-Loop

Eventos publicados quando humanos revisam decisões de IA.
"""
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class DecisionReviewedEvent(BaseModel):
    """
    Evento: Uma decisão de IA foi revisada por um humano.
    
    Este evento:
    - É publicado pelo ReviewService após revisão
    - É consumido pelo LearningService para feedback loop
    - É auditável e imutável
    - Nunca executa ações de negócio diretamente
    
    Handlers:
    - LearningService: Atualiza padrões de confiança
    - AuditService: Registra auditoria
    - AnalyticsService: Métricas de precisão da IA
    
    Exemplo de uso:
        event = DecisionReviewedEvent(
            decision_id="req_abc123",
            decision_log_id=456,
            tenant_id=1,
            reviewer_id=10,
            action_taken="corrected",
            original_decision={"categoria_id": 15},
            corrected_data={"categoria_id": 18},
            comment="Era energia, mas é água",
            confidence_score_original=65
        )
    """
    # Evento
    event_type: Literal["decision_reviewed"] = "decision_reviewed"
    event_id: str = Field(..., description="ID único do evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Decisão revisada
    decision_id: str = Field(..., description="request_id da decisão original")
    decision_log_id: int = Field(..., description="ID do log de decisão")
    decision_type: str = Field(..., description="Tipo de decisão (ex: categorizar_lancamento)")
    
    # Multi-tenant
    tenant_id: int = Field(..., description="ID do tenant/usuário")
    
    # Revisor
    reviewer_id: int = Field(..., description="ID do usuário que revisou")
    reviewer_name: Optional[str] = Field(None, description="Nome do revisor (para auditoria)")
    
    # Ação tomada
    action_taken: str = Field(
        ...,
        description="approved | corrected | rejected"
    )
    
    # Dados originais da IA
    original_decision: Dict[str, Any] = Field(
        ...,
        description="Decisão original da IA"
    )
    confidence_score_original: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confiança original da IA"
    )
    
    # Dados corrigidos (se action=corrected)
    corrected_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Decisão correta fornecida pelo humano"
    )
    
    # Comentário
    comment: Optional[str] = Field(
        None,
        description="Comentário do revisor"
    )
    
    # Contexto adicional
    processing_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Contexto adicional para o LearningService"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_20260123_abc123",
                "decision_id": "req_abc123",
                "decision_log_id": 456,
                "decision_type": "categorizar_lancamento",
                "tenant_id": 1,
                "reviewer_id": 10,
                "action_taken": "corrected",
                "original_decision": {
                    "categoria_id": 15,
                    "categoria_nome": "Energia Elétrica"
                },
                "confidence_score_original": 65,
                "corrected_data": {
                    "categoria_id": 18,
                    "categoria_nome": "Água e Esgoto"
                },
                "comment": "Era energia mas fornecedor é de água"
            }
        }


class DecisionAppliedEvent(BaseModel):
    """
    Evento: Uma decisão revisada foi aplicada no sistema.
    
    Publicado DEPOIS da revisão humana quando a decisão
    é efetivamente aplicada ao estado de negócio.
    
    Permite rastreabilidade completa:
    IA sugeriu → Humano revisou → Sistema aplicou
    """
    event_type: Literal["decision_applied"] = "decision_applied"
    event_id: str = Field(..., description="ID único do evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Referências
    decision_id: str = Field(...)
    decision_log_id: int = Field(...)
    review_event_id: Optional[str] = Field(
        None,
        description="ID do DecisionReviewedEvent relacionado"
    )
    
    # Tenant
    tenant_id: int = Field(...)
    
    # Decisão aplicada
    applied_decision: Dict[str, Any] = Field(
        ...,
        description="Decisão final que foi aplicada (IA ou corrigida)"
    )
    
    # Aplicação
    applied_by: int = Field(..., description="Quem aplicou (pode ser sistema ou humano)")
    applied_automatically: bool = Field(
        ...,
        description="True se aplicado automaticamente, False se manual"
    )
    
    # Resultado
    application_result: Dict[str, Any] = Field(
        ...,
        description="Resultado da aplicação (ex: ID do lançamento atualizado)"
    )


class AIAlertEvent(BaseModel):
    """
    Evento: Violação de guardrail de segurança detectada.
    
    Publicado quando métricas de IA violam limites de segurança,
    indicando possível regressão ou risco operacional.
    
    Handlers:
    - SafetyService: Aciona circuit breakers
    - AlertService: Notifica operadores (email, Slack, etc)
    - AuditService: Registra incidente
    - DecisionPolicy: Ajusta thresholds automaticamente
    
    Severidades:
    - WARNING: Alerta operadores, mas não bloqueia
    - CRITICAL: Bloqueia automação, força revisão
    - EMERGENCY: Bloqueia TODA IA para tenant/módulo
    """
    # Evento
    event_type: Literal["ai_alert"] = "ai_alert"
    event_id: str = Field(..., description="ID único do evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Severidade
    severity: str = Field(
        ...,
        description="warning | critical | emergency"
    )
    
    # Contexto
    tenant_id: int = Field(..., description="Tenant afetado")
    decision_type: Optional[str] = Field(
        None,
        description="Tipo de decisão (None = todos os tipos)"
    )
    
    # Violação
    guardrail_type: str = Field(
        ...,
        description="Tipo de guardrail violado"
    )
    current_value: float = Field(
        ...,
        description="Valor atual da métrica"
    )
    threshold_violated: float = Field(
        ...,
        description="Limite que foi violado"
    )
    
    # Métricas completas
    metrics_snapshot: Dict[str, Any] = Field(
        ...,
        description="Snapshot completo das métricas no momento do alerta"
    )
    
    # Ação recomendada
    recommended_action: str = Field(
        ...,
        description="Ação recomendada: reduce_automation | force_review | block_all | investigate"
    )
    
    # Contexto adicional
    message: str = Field(..., description="Mensagem legível do alerta")
    previous_trust_score: Optional[float] = Field(
        None,
        description="Trust score anterior (para alertas de queda)"
    )
    
    # Circuit breaker
    circuit_breaker_triggered: bool = Field(
        default=False,
        description="Se circuit breaker foi acionado"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "alert_20260123_abc",
                "severity": "critical",
                "tenant_id": 1,
                "decision_type": "categorizar_lancamento",
                "guardrail_type": "approval_rate_min",
                "current_value": 45.2,
                "threshold_violated": 50.0,
                "metrics_snapshot": {
                    "approval_rate": 45.2,
                    "rejection_rate": 12.5,
                    "trust_score": 42.0
                },
                "recommended_action": "force_review",
                "message": "Taxa de aprovação caiu para 45.2% (limite: 50%)",
                "circuit_breaker_triggered": True
            }
        }
