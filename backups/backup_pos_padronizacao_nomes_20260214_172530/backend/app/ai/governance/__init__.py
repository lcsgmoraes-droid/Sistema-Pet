"""
AI Governance Package
Framework de change management e aprovação de mudanças de IA
"""
from app.ai.governance.models import (
    AIChangeRequest,
    ChangeRequestStatus,
    ChangeCategory,
    ChangeImpactLevel,
    RiskLevel,
    ApprovalFlow,
    ApprovalRecord,
    ApprovalRole,
    ApprovalDecision,
    ApprovalRule,
    QualityGate,
    QualityReport,
    ChangeApprovalPolicy,
    DEFAULT_APPROVAL_POLICY,
)

from app.ai.governance.events import (
    AIChangeRequested,
    AIChangeSubmittedForReview,
    QualityGatesEvaluated,
    AIChangeApprovalGiven,
    AIChangeRejected,
    AIChangeFullyApproved,
    AIChangeCancelled,
    AIVersionPromotedToProduction,
)

from app.ai.governance.change_management import ChangeManagementService
from app.ai.governance.approval_service import ApprovalService
from app.ai.governance.governed_promotion import GovernedVersionPromotion


__all__ = [
    # Models
    "AIChangeRequest",
    "ChangeRequestStatus",
    "ChangeCategory",
    "ChangeImpactLevel",
    "RiskLevel",
    "ApprovalFlow",
    "ApprovalRecord",
    "ApprovalRole",
    "ApprovalDecision",
    "ApprovalRule",
    "QualityGate",
    "QualityReport",
    "ChangeApprovalPolicy",
    "DEFAULT_APPROVAL_POLICY",
    # Events
    "AIChangeRequested",
    "AIChangeSubmittedForReview",
    "QualityGatesEvaluated",
    "AIChangeApprovalGiven",
    "AIChangeRejected",
    "AIChangeFullyApproved",
    "AIChangeCancelled",
    "AIVersionPromotedToProduction",
    # Services
    "ChangeManagementService",
    "ApprovalService",
    "GovernedVersionPromotion",
]
