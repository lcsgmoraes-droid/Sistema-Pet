"""
AI Trust & Performance Metrics - Domain Models

Métricas de confiança e qualidade para governança de IA.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, computed_field


class MetricPeriod(str, Enum):
    """Período de agregação de métricas."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class AIMaturityLevel(str, Enum):
    """
    Nível de maturidade da IA baseado em métricas históricas.
    
    - LEARNING: < 50% approval, aprendendo, precisa revisão constante
    - DEVELOPING: 50-70% approval, em desenvolvimento
    - RELIABLE: 70-85% approval, confiável para MEDIUM
    - MATURE: 85-95% approval, pode aumentar automação
    - EXPERT: > 95% approval, quase perfeita
    """
    LEARNING = "learning"           # < 50% approval
    DEVELOPING = "developing"       # 50-70% approval
    RELIABLE = "reliable"           # 70-85% approval
    MATURE = "mature"               # 85-95% approval
    EXPERT = "expert"               # > 95% approval


class AIPerformanceMetrics(BaseModel):
    """
    Métricas de performance da IA para um tenant/módulo/período.
    
    Calculado a partir de DecisionLog + ReviewQueue + FeedbackLog.
    """
    # Identificação
    tenant_id: int = Field(..., description="ID do tenant")
    decision_type: Optional[str] = Field(None, description="Tipo de decisão (ou None=todos)")
    period: MetricPeriod = Field(..., description="Período de agregação")
    period_start: date = Field(..., description="Início do período")
    period_end: date = Field(..., description="Fim do período")
    
    # Volumetria
    total_decisions: int = Field(0, description="Total de decisões no período")
    decisions_reviewed: int = Field(0, description="Decisões revisadas por humanos")
    decisions_auto_executed: int = Field(0, description="Decisões executadas automaticamente")
    
    # Distribuição por confiança (%)
    decisions_very_high: int = Field(0, description="90-100%")
    decisions_high: int = Field(0, description="80-89%")
    decisions_medium: int = Field(0, description="60-79%")
    decisions_low: int = Field(0, description="40-59%")
    decisions_very_low: int = Field(0, description="0-39%")
    
    # Feedback humano
    reviews_approved: int = Field(0, description="Revisões aprovadas (IA acertou)")
    reviews_corrected: int = Field(0, description="Revisões corrigidas (IA errou)")
    reviews_rejected: int = Field(0, description="Revisões rejeitadas")
    
    # Confiança média
    avg_confidence_all: float = Field(0.0, description="Confiança média geral")
    avg_confidence_approved: float = Field(0.0, description="Confiança média das aprovadas")
    avg_confidence_corrected: float = Field(0.0, description="Confiança média das corrigidas")
    
    # Tempo de processamento
    avg_processing_time_ms: float = Field(0.0, description="Tempo médio de processamento")
    avg_review_time_minutes: float = Field(0.0, description="Tempo médio de revisão humana")
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # ==================== MÉTRICAS DERIVADAS ====================
    
    @computed_field
    @property
    def approval_rate(self) -> float:
        """
        Taxa de aprovação: % de decisões aprovadas pelo humano.
        
        Formula: reviews_approved / decisions_reviewed
        
        Indica o quão correta a IA está.
        - > 90%: IA muito precisa
        - 70-90%: IA confiável
        - 50-70%: IA em desenvolvimento
        - < 50%: IA precisa melhorar
        """
        if self.decisions_reviewed == 0:
            return 0.0
        return round((self.reviews_approved / self.decisions_reviewed) * 100, 2)
    
    @computed_field
    @property
    def correction_rate(self) -> float:
        """
        Taxa de correção: % de decisões corrigidas.
        
        Formula: reviews_corrected / decisions_reviewed
        
        Indica onde a IA erra.
        - > 30%: IA errando muito
        - 10-30%: IA precisa ajustes
        - < 10%: IA com poucos erros
        """
        if self.decisions_reviewed == 0:
            return 0.0
        return round((self.reviews_corrected / self.decisions_reviewed) * 100, 2)
    
    @computed_field
    @property
    def rejection_rate(self) -> float:
        """
        Taxa de rejeição: % de decisões completamente inadequadas.
        
        Formula: reviews_rejected / decisions_reviewed
        
        - > 10%: IA fazendo sugestões ruins
        - 5-10%: IA com problemas ocasionais
        - < 5%: IA raramente erra gravemente
        """
        if self.decisions_reviewed == 0:
            return 0.0
        return round((self.reviews_rejected / self.decisions_reviewed) * 100, 2)
    
    @computed_field
    @property
    def automation_rate(self) -> float:
        """
        Taxa de automação: % de decisões executadas automaticamente.
        
        Formula: decisions_auto_executed / total_decisions
        
        Indica o nível de autonomia da IA.
        - > 80%: Alta automação
        - 50-80%: Automação moderada
        - < 50%: Precisa muita revisão
        """
        if self.total_decisions == 0:
            return 0.0
        return round((self.decisions_auto_executed / self.total_decisions) * 100, 2)
    
    @computed_field
    @property
    def confidence_accuracy_gap(self) -> float:
        """
        Gap entre confiança e acurácia: diferença entre avg_confidence e approval_rate.
        
        Formula: |avg_confidence_all - approval_rate|
        
        Indica se a IA é:
        - < 5: Bem calibrada (confiança reflete realidade)
        - 5-15: Moderadamente calibrada
        - > 15: Mal calibrada (overconfident ou underconfident)
        
        Exemplo:
        - IA média 80% confiança, 82% approval → gap 2 (bem calibrada)
        - IA média 75% confiança, 55% approval → gap 20 (overconfident)
        """
        return round(abs(self.avg_confidence_all - self.approval_rate), 2)
    
    @computed_field
    @property
    def review_pressure(self) -> float:
        """
        Pressão de revisão: % de decisões que exigiram revisão humana.
        
        Formula: decisions_reviewed / total_decisions
        
        - > 50%: Alta pressão (muitas revisões)
        - 20-50%: Pressão moderada
        - < 20%: Baixa pressão (IA autônoma)
        """
        if self.total_decisions == 0:
            return 0.0
        return round((self.decisions_reviewed / self.total_decisions) * 100, 2)


class AITrustReport(BaseModel):
    """
    Relatório de confiança da IA com recomendações automáticas.
    
    Gerado pelo TrustService baseado em métricas históricas.
    """
    # Contexto
    tenant_id: int = Field(..., description="ID do tenant")
    decision_type: Optional[str] = Field(None, description="Tipo de decisão analisada")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Período analisado
    period: MetricPeriod = Field(...)
    metrics: AIPerformanceMetrics = Field(..., description="Métricas do período")
    
    # Avaliação
    maturity_level: AIMaturityLevel = Field(..., description="Nível de maturidade")
    trust_score: int = Field(..., ge=0, le=100, description="Score de confiança geral (0-100)")
    
    # Análise
    strengths: List[str] = Field(default_factory=list, description="Pontos fortes")
    weaknesses: List[str] = Field(default_factory=list, description="Pontos fracos")
    risks: List[str] = Field(default_factory=list, description="Riscos identificados")
    
    # Recomendações
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recomendações para melhorar"
    )
    
    suggested_min_confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confiança mínima sugerida para automação"
    )
    
    suggested_review_threshold: int = Field(
        ...,
        ge=0,
        le=100,
        description="Threshold sugerido para revisão obrigatória"
    )
    
    can_increase_automation: bool = Field(
        ...,
        description="Se pode aumentar automação com segurança"
    )
    
    # Contexto adicional
    sample_size: int = Field(..., description="Número de decisões analisadas")
    confidence_level: str = Field(
        ...,
        description="Nível de confiança estatística (low/medium/high)"
    )


class MetricTrend(BaseModel):
    """
    Tendência de uma métrica ao longo do tempo.
    """
    metric_name: str = Field(..., description="Nome da métrica")
    current_value: float = Field(..., description="Valor atual")
    previous_value: float = Field(..., description="Valor no período anterior")
    change_percent: float = Field(..., description="Mudança percentual")
    trend: str = Field(..., description="improving | stable | declining")
    
    @computed_field
    @property
    def is_improving(self) -> bool:
        """Se a métrica está melhorando."""
        # Para approval_rate, automation_rate: maior é melhor
        # Para correction_rate, rejection_rate: menor é melhor
        improving_metrics = ["approval_rate", "automation_rate", "trust_score"]
        declining_metrics = ["correction_rate", "rejection_rate", "review_pressure"]
        
        if self.metric_name in improving_metrics:
            return self.change_percent > 0
        elif self.metric_name in declining_metrics:
            return self.change_percent < 0
        else:
            return abs(self.change_percent) < 5  # stable
