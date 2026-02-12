"""
AI Behavior Versioning - Domain Models
Modelos de versionamento de comportamento da IA
"""
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ComponentType(str, Enum):
    """Tipos de componentes versionáveis"""
    ANALYZER = "analyzer"
    CONFIDENCE_FORMULA = "confidence_formula"
    POLICY = "policy"
    GUARDRAIL = "guardrail"
    PROMPT_TEMPLATE = "prompt_template"


class RolloutStrategy(str, Enum):
    """Estratégias de rollout"""
    IMMEDIATE = "immediate"  # Deploy imediato em todos tenants
    CANARY = "canary"  # Deploy em subset pequeno primeiro
    GRADUAL = "gradual"  # Deploy incremental por percentual
    TENANT_SPECIFIC = "tenant_specific"  # Deploy apenas em tenants específicos
    BLUE_GREEN = "blue_green"  # Mantém versão anterior rodando


class RolloutStatus(str, Enum):
    """Status do rollout"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"


class VersionStatus(str, Enum):
    """Status de uma versão"""
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ComponentVersion(BaseModel):
    """Versão de um componente específico"""
    component_type: ComponentType
    version: str  # Semantic versioning: 1.2.3
    config: Dict[str, Any]  # Configuração específica do componente
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        frozen = True  # Imutável


class AIBehaviorVersion(BaseModel):
    """
    Snapshot completo de uma versão de comportamento da IA
    Representa uma combinação específica de versões de componentes
    """
    id: UUID = Field(default_factory=uuid4)
    version_name: str  # Ex: "v2.3.0", "canary-20260123"
    version_tag: str  # Ex: "stable", "canary", "experimental"
    
    # Versões dos componentes
    components: Dict[ComponentType, ComponentVersion]
    
    # Metadados
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    description: str
    changelog: str
    
    # Status
    status: VersionStatus = VersionStatus.DRAFT
    
    # Validações
    min_confidence_threshold: float = 0.7
    min_trust_score: float = 0.75
    
    class Config:
        frozen = True


class TenantVersionAssignment(BaseModel):
    """
    Atribuição de versão a um tenant específico
    """
    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    behavior_version_id: UUID
    
    # Controle de ativação
    activated_at: datetime
    activated_by: str
    
    # Versão anterior (para rollback)
    previous_version_id: Optional[UUID] = None
    
    # Observabilidade
    decision_count: int = 0
    success_count: int = 0
    fallback_count: int = 0
    avg_confidence: float = 0.0
    avg_trust_score: float = 0.0
    
    class Config:
        arbitrary_types_allowed = True


class RolloutConfig(BaseModel):
    """Configuração de rollout"""
    strategy: RolloutStrategy
    
    # Para CANARY
    canary_tenant_ids: List[str] = Field(default_factory=list)
    canary_percentage: float = 0.05  # 5% dos tenants
    
    # Para GRADUAL
    gradual_steps: List[int] = Field(default_factory=lambda: [10, 25, 50, 100])  # Percentuais
    gradual_step_duration_minutes: int = 60
    
    # Para TENANT_SPECIFIC
    target_tenant_ids: List[str] = Field(default_factory=list)
    
    # Condições de sucesso
    min_success_rate: float = 0.95
    max_fallback_rate: float = 0.05
    min_decisions_before_proceed: int = 100
    
    # Auto-rollback
    auto_rollback_enabled: bool = True
    auto_rollback_threshold: float = 0.90  # Se success rate < 90%, rollback


class RolloutPlan(BaseModel):
    """Plano de execução de rollout"""
    id: UUID = Field(default_factory=uuid4)
    behavior_version_id: UUID
    config: RolloutConfig
    
    # Estado
    status: RolloutStatus = RolloutStatus.PENDING
    current_step: int = 0
    current_tenant_ids: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Métricas agregadas
    total_decisions: int = 0
    total_success: int = 0
    total_fallbacks: int = 0
    
    # Decisões
    should_proceed: bool = True
    rollback_reason: Optional[str] = None


class VersionPerformanceSnapshot(BaseModel):
    """
    Snapshot de performance de uma versão em um tenant
    Usado para decisão de rollout
    """
    tenant_id: str
    behavior_version_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Métricas
    decision_count: int
    success_rate: float
    fallback_rate: float
    avg_confidence: float
    avg_trust_score: float
    avg_latency_ms: float
    
    # Comparação com baseline
    baseline_version_id: Optional[UUID] = None
    success_rate_delta: Optional[float] = None
    confidence_delta: Optional[float] = None


class VersionRegressionAlert(BaseModel):
    """Alerta de regressão de versão"""
    id: UUID = Field(default_factory=uuid4)
    behavior_version_id: UUID
    tenant_id: str
    
    # Métricas problemáticas
    metric_name: str  # "success_rate", "confidence", etc
    current_value: float
    baseline_value: float
    delta: float
    threshold_violated: float
    
    # Contexto
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    severity: str  # "warning", "critical"
    recommendation: str  # "pause_rollout", "rollback", "monitor"
