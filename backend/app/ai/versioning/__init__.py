"""
AI Versioning Package
Framework de versionamento e deployment de IA
"""
from app.ai.versioning.models import (
    AIBehaviorVersion,
    ComponentType,
    ComponentVersion,
    RolloutConfig,
    RolloutPlan,
    RolloutStrategy,
    RolloutStatus,
    TenantVersionAssignment,
    VersionStatus,
    VersionPerformanceSnapshot,
    VersionRegressionAlert,
)

from app.ai.versioning.events import (
    BehaviorVersionCreated,
    BehaviorVersionPromoted,
    RolloutPlanCreated,
    RolloutStarted,
    RolloutStepCompleted,
    RolloutCompleted,
    RolloutFailed,
    TenantVersionActivated,
    TenantVersionRolledBack,
    VersionRegressionDetected,
    AutoRollbackTriggered,
)

from app.ai.versioning.registry import VersionRegistry
from app.ai.versioning.orchestrator import RolloutOrchestrator
from app.ai.versioning.integration import (
    VersionedDecisionService,
    VersionAwareAuditService,
)


__all__ = [
    # Models
    "AIBehaviorVersion",
    "ComponentType",
    "ComponentVersion",
    "RolloutConfig",
    "RolloutPlan",
    "RolloutStrategy",
    "RolloutStatus",
    "TenantVersionAssignment",
    "VersionStatus",
    "VersionPerformanceSnapshot",
    "VersionRegressionAlert",
    # Events
    "BehaviorVersionCreated",
    "BehaviorVersionPromoted",
    "RolloutPlanCreated",
    "RolloutStarted",
    "RolloutStepCompleted",
    "RolloutCompleted",
    "RolloutFailed",
    "TenantVersionActivated",
    "TenantVersionRolledBack",
    "VersionRegressionDetected",
    "AutoRollbackTriggered",
    # Services
    "VersionRegistry",
    "RolloutOrchestrator",
    "VersionedDecisionService",
    "VersionAwareAuditService",
]
