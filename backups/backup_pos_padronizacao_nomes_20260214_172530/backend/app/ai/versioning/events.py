"""
AI Versioning Events - Domain Events
Eventos de domínio para versionamento de IA
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class AIVersionEvent(BaseModel):
    """Base para eventos de versionamento"""
    event_id: UUID
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    aggregate_id: UUID
    aggregate_type: str
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BehaviorVersionCreated(AIVersionEvent):
    """Nova versão de comportamento criada"""
    aggregate_type: str = "behavior_version"
    event_type: str = "behavior_version.created"
    
    version_name: str
    version_tag: str
    created_by: str
    component_versions: Dict[str, str]  # ComponentType -> version


class BehaviorVersionPromoted(AIVersionEvent):
    """Versão promovida (draft -> testing -> active)"""
    aggregate_type: str = "behavior_version"
    event_type: str = "behavior_version.promoted"
    
    from_status: str
    to_status: str
    promoted_by: str


class RolloutPlanCreated(AIVersionEvent):
    """Plano de rollout criado"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.plan_created"
    
    behavior_version_id: UUID
    strategy: str
    created_by: str


class RolloutStarted(AIVersionEvent):
    """Rollout iniciado"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.started"
    
    behavior_version_id: UUID
    strategy: str
    initial_tenant_ids: List[str]


class RolloutStepCompleted(AIVersionEvent):
    """Step de rollout completado"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.step_completed"
    
    step_number: int
    tenant_ids: List[str]
    success_rate: float
    fallback_rate: float


class RolloutPaused(AIVersionEvent):
    """Rollout pausado"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.paused"
    
    reason: str
    paused_by: str
    current_step: int


class RolloutResumed(AIVersionEvent):
    """Rollout resumido"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.resumed"
    
    resumed_by: str
    from_step: int


class RolloutCompleted(AIVersionEvent):
    """Rollout completado com sucesso"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.completed"
    
    behavior_version_id: UUID
    total_tenants: int
    total_decisions: int
    final_success_rate: float


class RolloutFailed(AIVersionEvent):
    """Rollout falhou"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.failed"
    
    reason: str
    failed_at_step: int
    affected_tenant_ids: List[str]


class TenantVersionActivated(AIVersionEvent):
    """Versão ativada para um tenant"""
    aggregate_type: str = "tenant_version"
    event_type: str = "tenant.version_activated"
    
    tenant_id: str
    behavior_version_id: UUID
    version_name: str
    activated_by: str
    previous_version_id: Optional[UUID] = None


class TenantVersionRolledBack(AIVersionEvent):
    """Rollback de versão em um tenant"""
    aggregate_type: str = "tenant_version"
    event_type: str = "tenant.version_rolled_back"
    
    tenant_id: str
    from_version_id: UUID
    to_version_id: UUID
    rolled_back_by: str
    reason: str


class VersionRegressionDetected(AIVersionEvent):
    """Regressão de performance detectada"""
    aggregate_type: str = "version_monitoring"
    event_type: str = "version.regression_detected"
    
    behavior_version_id: UUID
    tenant_id: str
    metric_name: str
    current_value: float
    baseline_value: float
    delta: float
    severity: str


class AutoRollbackTriggered(AIVersionEvent):
    """Rollback automático acionado"""
    aggregate_type: str = "rollout_plan"
    event_type: str = "rollout.auto_rollback_triggered"
    
    behavior_version_id: UUID
    trigger_reason: str
    trigger_metric: str
    trigger_value: float
    affected_tenant_ids: List[str]
