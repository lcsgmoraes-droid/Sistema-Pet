from app.base_models import BaseTenantModel
"""
Models de persistência do AI Core
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class DecisionLog(BaseTenantModel):
    """
    Log de decisões da IA (auditoria completa).
    
    Permite:
    - Rastreabilidade total
    - Replay de decisões
    - Análise de performance
    - Identificar decisões ruins
    """
    __tablename__ = "ai_decision_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Multi-tenant
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Tipo
    decision_type = Column(String(50), nullable=False, index=True)
    
    # Dados
    input_data = Column(JSON, nullable=False)  # DecisionContext serializado
    output_data = Column(JSON, nullable=False)  # DecisionResult serializado
    
    # Métricas
    confidence = Column(Float, nullable=False)
    engine_used = Column(String(50), nullable=False)
    processing_time_ms = Column(Float, nullable=False)
    
    # Controle
    requires_human_review = Column(Boolean, default=False, index=True)
    was_reviewed = Column(Boolean, default=False)
    was_applied = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    feedback = relationship("FeedbackLog", back_populates="decision", uselist=False)


class FeedbackLog(BaseTenantModel):
    """
    Feedback humano sobre decisões da IA.
    
    Fecha o loop de aprendizado.
    """
    __tablename__ = "ai_feedback_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Decisão original
    decision_id = Column(Integer, ForeignKey("ai_decision_logs.id"), nullable=False, unique=True)
    request_id = Column(String(50), index=True, nullable=False)
    
    # Multi-tenant
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Feedback
    feedback_type = Column(String(30), nullable=False)  # aprovado, rejeitado, corrigido
    
    ai_decision = Column(JSON, nullable=False)
    human_decision = Column(JSON, nullable=True)
    
    reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    decision = relationship("DecisionLog", back_populates="feedback")


class ReviewQueueModel(BaseTenantModel):
    """
    Fila de revisão humana (CQRS Read Model).
    
    Armazena decisões que exigem revisão humana antes de serem aplicadas.
    
    NÃO é uma entidade de negócio.
    É uma VIEW materializada para facilitar consultas de "decisões pendentes".
    
    Decisões com confiança MEDIUM ou LOW entram automaticamente aqui.
    """
    __tablename__ = "ai_review_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Referência à decisão original
    decision_log_id = Column(
        Integer, 
        ForeignKey("ai_decision_logs.id"), 
        nullable=False,
        index=True
    )
    
    # Multi-tenant
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Contexto
    decision_type = Column(String(50), nullable=False, index=True)
    decision_summary = Column(Text, nullable=False)  # Resumo legível
    
    # Confiança original
    confidence_score = Column(Integer, nullable=False)
    confidence_level = Column(String(20), nullable=False)
    
    # Prioridade (calculada)
    priority = Column(String(20), nullable=False, index=True)  # low, medium, high, urgent
    
    # Dados para revisão (JSON)
    context_data = Column(JSON, nullable=False)
    ai_decision = Column(JSON, nullable=False)
    ai_explanation = Column(Text, nullable=False)
    
    # Status
    status = Column(
        String(20), 
        nullable=False, 
        default="pending",
        index=True
    )  # pending, approved, corrected, rejected
    
    # Resultado da revisão
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_action = Column(String(20), nullable=True)
    corrected_data = Column(JSON, nullable=True)
    review_comment = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relacionamentos
    decision_log = relationship("DecisionLog", foreign_keys=[decision_log_id])


class AIMetricsSnapshotModel(BaseTenantModel):
    """
    Snapshot de métricas de performance da IA (CQRS Read Model).
    
    Agregações pré-calculadas para consultas rápidas de métricas.
    Atualizado incrementalmente quando DecisionReviewedEvent ocorre.
    
    Permite análise de:
    - Performance global da IA
    - Tendências ao longo do tempo
    - Comparação entre tenants/módulos
    - Identificação de problemas
    
    Granularidade: tenant + decision_type + período
    """
    __tablename__ = "ai_metrics_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identificação
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    decision_type = Column(String(50), nullable=True, index=True)  # NULL = todas
    
    # Período
    period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly, all_time
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Volumetria
    total_decisions = Column(Integer, default=0, nullable=False)
    decisions_reviewed = Column(Integer, default=0, nullable=False)
    decisions_auto_executed = Column(Integer, default=0, nullable=False)
    
    # Distribuição por confiança
    decisions_very_high = Column(Integer, default=0)  # 90-100
    decisions_high = Column(Integer, default=0)       # 80-89
    decisions_medium = Column(Integer, default=0)     # 60-79
    decisions_low = Column(Integer, default=0)        # 40-59
    decisions_very_low = Column(Integer, default=0)   # 0-39
    
    # Feedback humano
    reviews_approved = Column(Integer, default=0)
    reviews_corrected = Column(Integer, default=0)
    reviews_rejected = Column(Integer, default=0)
    
    # Confiança média (agregados)
    avg_confidence_all = Column(Float, default=0.0)
    avg_confidence_approved = Column(Float, default=0.0)
    avg_confidence_corrected = Column(Float, default=0.0)
    
    # Tempo médio
    avg_processing_time_ms = Column(Float, default=0.0)
    avg_review_time_minutes = Column(Float, default=0.0)
    
    # Métricas derivadas (cache)
    approval_rate = Column(Float, default=0.0)
    correction_rate = Column(Float, default=0.0)
    rejection_rate = Column(Float, default=0.0)
    automation_rate = Column(Float, default=0.0)
    confidence_accuracy_gap = Column(Float, default=0.0)
    review_pressure = Column(Float, default=0.0)
    
    # Metadata
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        # Um snapshot por tenant + decision_type + período
        sa.UniqueConstraint(
            'tenant_id', 
            'decision_type', 
            'period', 
            'period_start',
            name='uq_metrics_snapshot'
        ),
    )


class LearningPatternModel(BaseTenantModel):
    """
    Padrões aprendidos com feedback acumulado.
    
    Similar a PadraoCategoriacaoIA mas genérico para qualquer tipo de decisão.
    """
    __tablename__ = "ai_learning_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Multi-tenant
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Padrão
    pattern_type = Column(String(50), nullable=False, index=True)  # categoria_por_descricao, produto_por_contexto
    input_signature = Column(JSON, nullable=False)
    output_preference = Column(JSON, nullable=False)
    
    # Estatísticas
    confidence_boost = Column(Float, default=10.0)
    occurrences = Column(Integer, default=1)
    success_rate = Column(Float, default=100.0)
    
    # Temporalidade
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
