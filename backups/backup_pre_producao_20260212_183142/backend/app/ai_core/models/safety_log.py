from app.base_models import BaseTenantModel
"""
Safety Log - Registro de violações e circuit breakers
======================================================

Logs de segurança para auditoria e rastreabilidade.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from app.models import Base


class AIGuardrailViolationLog(BaseTenantModel):
    """
    Log de violações de guardrails.
    
    Registra todas as vezes que métricas violam limites de segurança.
    """
    __tablename__ = "ai_guardrail_violations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Evento
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # warning, critical, emergency
    
    # Contexto
    tenant_id = Column(Integer, nullable=False, index=True)
    decision_type = Column(String(100), nullable=True, index=True)
    
    # Violação
    guardrail_type = Column(String(50), nullable=False, index=True)
    current_value = Column(Float, nullable=False)
    threshold_violated = Column(Float, nullable=False)
    
    # Métricas
    metrics_snapshot = Column(JSON, nullable=False)
    
    # Ação
    recommended_action = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    
    # Circuit breaker
    circuit_breaker_triggered = Column(Boolean, default=False, nullable=False)
    
    # Resolução
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AIGuardrailViolation {self.event_id} {self.severity} {self.guardrail_type}>"


class AICircuitBreakerLog(BaseTenantModel):
    """
    Log de circuit breakers acionados.
    
    Registra quando automação é bloqueada por segurança.
    """
    __tablename__ = "ai_circuit_breaker_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Contexto
    tenant_id = Column(Integer, nullable=False, index=True)
    decision_type = Column(String(100), nullable=True, index=True)
    
    # Estado
    state = Column(String(20), nullable=False)  # open, half_open, closed
    reason = Column(Text, nullable=False)
    
    # Violações que causaram abertura
    violation_event_ids = Column(JSON, nullable=True)
    
    # Thresholds ajustados
    previous_min_confidence = Column(Integer, nullable=True)
    new_min_confidence = Column(Integer, nullable=True)
    
    # Timestamps
    opened_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AICircuitBreaker tenant={self.tenant_id} state={self.state}>"
