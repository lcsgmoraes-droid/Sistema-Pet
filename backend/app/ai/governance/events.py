"""
AI Change Management Events - Domain Events
Eventos de aprovação e governança de mudanças
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class GovernanceEvent(BaseModel):
    """Base para eventos de governança"""
    event_id: UUID
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    aggregate_id: UUID
    aggregate_type: str
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIChangeRequested(GovernanceEvent):
    """Mudança de IA solicitada"""
    aggregate_type: str = "change_request"
    event_type: str = "ai_change.requested"
    
    title: str
    category: str
    impact_level: str
    risk_level: str
    behavior_version_id: UUID
    requested_by: str


class AIChangeSubmittedForReview(GovernanceEvent):
    """Mudança submetida para revisão"""
    aggregate_type: str = "change_request"
    event_type: str = "ai_change.submitted_for_review"
    
    change_request_id: UUID
    submitted_by: str
    required_approvers: List[str]


class QualityGatesEvaluated(GovernanceEvent):
    """Quality gates avaliados"""
    aggregate_type: str = "quality_report"
    event_type: str = "quality.gates_evaluated"
    
    change_request_id: UUID
    behavior_version_id: UUID
    gates_passed: int
    gates_failed: int
    all_mandatory_passed: bool


class AIChangeApprovalGiven(GovernanceEvent):
    """Aprovação individual concedida"""
    aggregate_type: str = "approval_flow"
    event_type: str = "ai_change.approval_given"
    
    change_request_id: UUID
    approver_id: str
    approver_role: str
    decision: str  # approved, rejected, approved_with_conditions
    comments: str


class AIChangeRejected(GovernanceEvent):
    """Mudança rejeitada"""
    aggregate_type: str = "change_request"
    event_type: str = "ai_change.rejected"
    
    change_request_id: UUID
    rejected_by: str
    rejection_reason: str


class AIChangeFullyApproved(GovernanceEvent):
    """Mudança completamente aprovada (todas aprovações)"""
    aggregate_type: str = "change_request"
    event_type: str = "ai_change.fully_approved"
    
    change_request_id: UUID
    behavior_version_id: UUID
    total_approvals: int
    approved_at: datetime


class AIChangeCancelled(GovernanceEvent):
    """Mudança cancelada"""
    aggregate_type: str = "change_request"
    event_type: str = "ai_change.cancelled"
    
    change_request_id: UUID
    cancelled_by: str
    cancellation_reason: str


class AIVersionPromotedToProduction(GovernanceEvent):
    """Versão promovida para produção após aprovação"""
    aggregate_type: str = "behavior_version"
    event_type: str = "ai_version.promoted_to_production"
    
    behavior_version_id: UUID
    version_name: str
    change_request_id: UUID
    promoted_by: str


class ApprovalPolicyCreated(GovernanceEvent):
    """Nova política de aprovação criada"""
    aggregate_type: str = "approval_policy"
    event_type: str = "approval_policy.created"
    
    policy_name: str
    created_by: str


class ApprovalPolicyActivated(GovernanceEvent):
    """Política de aprovação ativada"""
    aggregate_type: str = "approval_policy"
    event_type: str = "approval_policy.activated"
    
    policy_name: str
    activated_by: str


class ComplianceCheckPerformed(GovernanceEvent):
    """Verificação de compliance realizada"""
    aggregate_type: str = "compliance"
    event_type: str = "compliance.check_performed"
    
    change_request_id: UUID
    check_type: str
    passed: bool
    findings: List[str]
