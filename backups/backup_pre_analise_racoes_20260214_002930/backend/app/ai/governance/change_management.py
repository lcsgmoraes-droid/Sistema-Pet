"""
Change Management Service
Gerencia o ciclo de vida de mudanças de IA
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.ai.governance.models import (
    AIChangeRequest,
    ChangeRequestStatus,
    ChangeImpactLevel,
    QualityReport,
    QualityGate,
    ChangeApprovalPolicy,
    DEFAULT_APPROVAL_POLICY,
)
from app.ai.governance.events import (
    AIChangeRequested,
    AIChangeSubmittedForReview,
    QualityGatesEvaluated,
    AIChangeFullyApproved,
    AIChangeRejected,
    AIChangeCancelled,
)


class ChangeManagementService:
    """
    Gerencia solicitações de mudança de IA
    Responsabilidade: Coordenar o fluxo de mudança completo
    """
    
    def __init__(self, event_store, version_registry):
        self.event_store = event_store
        self.version_registry = version_registry
        self._change_requests: Dict[UUID, AIChangeRequest] = {}
        self._quality_reports: Dict[UUID, QualityReport] = {}
        self.active_policy = DEFAULT_APPROVAL_POLICY
    
    def create_change_request(
        self,
        title: str,
        description: str,
        category: str,
        impact_level: ChangeImpactLevel,
        behavior_version_id: UUID,
        business_justification: str,
        technical_justification: str,
        expected_benefits: List[str],
        known_risks: List[str],
        risk_level: str,
        mitigation_plan: str,
        rollback_plan: str,
        requested_by: str,
        affected_tenants: Optional[List[str]] = None,
    ) -> AIChangeRequest:
        """Cria nova solicitação de mudança"""
        
        # Validar que a versão existe
        version = self.version_registry.get_version(behavior_version_id)
        if not version:
            raise ValueError(f"Version {behavior_version_id} not found")
        
        # Criar change request
        change_request = AIChangeRequest(
            title=title,
            description=description,
            category=category,
            impact_level=impact_level,
            behavior_version_id=behavior_version_id,
            version_name=version.version_name,
            business_justification=business_justification,
            technical_justification=technical_justification,
            expected_benefits=expected_benefits,
            known_risks=known_risks,
            risk_level=risk_level,
            mitigation_plan=mitigation_plan,
            rollback_plan=rollback_plan,
            requested_by=requested_by,
            affected_tenants=affected_tenants,
        )
        
        self._change_requests[change_request.id] = change_request
        
        # Emitir evento
        event = AIChangeRequested(
            event_id=uuid4(),
            aggregate_id=change_request.id,
            title=title,
            category=category,
            impact_level=impact_level.value,
            risk_level=risk_level,
            behavior_version_id=behavior_version_id,
            requested_by=requested_by,
        )
        self.event_store.append(event)
        
        return change_request
    
    def submit_for_review(
        self,
        change_request_id: UUID,
        submitted_by: str,
    ) -> AIChangeRequest:
        """Submete mudança para revisão"""
        
        change_request = self._change_requests.get(change_request_id)
        if not change_request:
            raise ValueError(f"Change request {change_request_id} not found")
        
        if change_request.status != ChangeRequestStatus.DRAFT:
            raise ValueError(
                f"Can only submit DRAFT changes. Current status: {change_request.status}"
            )
        
        # Validar requisitos da policy
        policy = self.active_policy
        
        if policy.require_testing and not change_request.testing_completed:
            raise ValueError("Testing must be completed before submission")
        
        if policy.require_quality_report and not change_request.quality_gates_passed:
            raise ValueError("Quality gates must pass before submission")
        
        if policy.require_rollback_plan and not change_request.rollback_plan:
            raise ValueError("Rollback plan is required")
        
        # Atualizar status
        updated_request = change_request.model_copy(update={
            "status": ChangeRequestStatus.UNDER_REVIEW,
            "submitted_at": datetime.utcnow(),
        })
        self._change_requests[change_request_id] = updated_request
        
        # Determinar aprovadores necessários
        rule = policy.rules.get(change_request.impact_level)
        required_roles = [role.value for role in rule.required_roles]
        
        # Emitir evento
        event = AIChangeSubmittedForReview(
            event_id=uuid4(),
            aggregate_id=change_request_id,
            change_request_id=change_request_id,
            submitted_by=submitted_by,
            required_approvers=required_roles,
        )
        self.event_store.append(event)
        
        return updated_request
    
    def evaluate_quality_gates(
        self,
        change_request_id: UUID,
        test_metrics: Dict[str, float],
        test_decisions_count: int,
        evaluation_period_start: datetime,
        evaluation_period_end: datetime,
    ) -> QualityReport:
        """Avalia quality gates de uma versão"""
        
        change_request = self._change_requests.get(change_request_id)
        if not change_request:
            raise ValueError(f"Change request {change_request_id} not found")
        
        # Pegar gates da policy
        gates = self.active_policy.mandatory_quality_gates
        
        # Avaliar cada gate
        gates_passed = {}
        gates_values = {}
        
        for gate in gates:
            metric_value = test_metrics.get(gate.metric, 0.0)
            gates_values[gate.name] = metric_value
            gates_passed[gate.name] = gate.evaluate(metric_value)
        
        # Calcular resultados
        mandatory_gates = [g for g in gates if g.is_mandatory]
        all_mandatory_passed = all(
            gates_passed.get(g.name, False) for g in mandatory_gates
        )
        
        total_passed = sum(1 for passed in gates_passed.values() if passed)
        total_failed = len(gates_passed) - total_passed
        
        # Criar report
        report = QualityReport(
            behavior_version_id=change_request.behavior_version_id,
            change_request_id=change_request_id,
            gates_evaluated=gates,
            gates_passed=gates_passed,
            gates_values=gates_values,
            all_mandatory_gates_passed=all_mandatory_passed,
            total_gates_passed=total_passed,
            total_gates_failed=total_failed,
            test_decisions_count=test_decisions_count,
            test_success_rate=test_metrics.get("success_rate", 0.0),
            test_avg_confidence=test_metrics.get("avg_confidence", 0.0),
            test_avg_trust_score=test_metrics.get("avg_trust_score", 0.0),
            test_avg_latency_ms=test_metrics.get("avg_latency_ms", 0.0),
            evaluation_period_start=evaluation_period_start,
            evaluation_period_end=evaluation_period_end,
        )
        
        self._quality_reports[report.id] = report
        
        # Atualizar change request
        updated_request = change_request.model_copy(update={
            "quality_gates_passed": all_mandatory_passed,
            "quality_gate_results": gates_passed,
        })
        self._change_requests[change_request_id] = updated_request
        
        # Emitir evento
        event = QualityGatesEvaluated(
            event_id=uuid4(),
            aggregate_id=report.id,
            change_request_id=change_request_id,
            behavior_version_id=change_request.behavior_version_id,
            gates_passed=total_passed,
            gates_failed=total_failed,
            all_mandatory_passed=all_mandatory_passed,
        )
        self.event_store.append(event)
        
        return report
    
    def approve_change(
        self,
        change_request_id: UUID,
    ) -> AIChangeRequest:
        """Marca mudança como aprovada (após todas aprovações)"""
        
        change_request = self._change_requests.get(change_request_id)
        if not change_request:
            raise ValueError(f"Change request {change_request_id} not found")
        
        if change_request.status != ChangeRequestStatus.UNDER_REVIEW:
            raise ValueError("Change must be UNDER_REVIEW to approve")
        
        # Atualizar status
        updated_request = change_request.model_copy(update={
            "status": ChangeRequestStatus.APPROVED,
            "approved_at": datetime.utcnow(),
        })
        self._change_requests[change_request_id] = updated_request
        
        # Emitir evento
        event = AIChangeFullyApproved(
            event_id=uuid4(),
            aggregate_id=change_request_id,
            change_request_id=change_request_id,
            behavior_version_id=change_request.behavior_version_id,
            total_approvals=0,  # Será preenchido pelo approval service
            approved_at=datetime.utcnow(),
        )
        self.event_store.append(event)
        
        return updated_request
    
    def reject_change(
        self,
        change_request_id: UUID,
        rejected_by: str,
        rejection_reason: str,
    ) -> AIChangeRequest:
        """Rejeita mudança"""
        
        change_request = self._change_requests.get(change_request_id)
        if not change_request:
            raise ValueError(f"Change request {change_request_id} not found")
        
        # Atualizar status
        updated_request = change_request.model_copy(update={
            "status": ChangeRequestStatus.REJECTED,
            "rejected_at": datetime.utcnow(),
        })
        self._change_requests[change_request_id] = updated_request
        
        # Emitir evento
        event = AIChangeRejected(
            event_id=uuid4(),
            aggregate_id=change_request_id,
            change_request_id=change_request_id,
            rejected_by=rejected_by,
            rejection_reason=rejection_reason,
        )
        self.event_store.append(event)
        
        return updated_request
    
    def cancel_change(
        self,
        change_request_id: UUID,
        cancelled_by: str,
        reason: str,
    ) -> AIChangeRequest:
        """Cancela mudança"""
        
        change_request = self._change_requests.get(change_request_id)
        if not change_request:
            raise ValueError(f"Change request {change_request_id} not found")
        
        if change_request.status in [
            ChangeRequestStatus.APPROVED,
            ChangeRequestStatus.REJECTED,
        ]:
            raise ValueError(
                f"Cannot cancel change with status {change_request.status}"
            )
        
        # Atualizar status
        updated_request = change_request.model_copy(update={
            "status": ChangeRequestStatus.CANCELLED,
        })
        self._change_requests[change_request_id] = updated_request
        
        # Emitir evento
        event = AIChangeCancelled(
            event_id=uuid4(),
            aggregate_id=change_request_id,
            change_request_id=change_request_id,
            cancelled_by=cancelled_by,
            cancellation_reason=reason,
        )
        self.event_store.append(event)
        
        return updated_request
    
    def get_change_request(self, change_request_id: UUID) -> Optional[AIChangeRequest]:
        """Recupera change request"""
        return self._change_requests.get(change_request_id)
    
    def list_change_requests(
        self,
        status: Optional[ChangeRequestStatus] = None,
        requested_by: Optional[str] = None,
    ) -> List[AIChangeRequest]:
        """Lista change requests"""
        requests = list(self._change_requests.values())
        
        if status:
            requests = [r for r in requests if r.status == status]
        
        if requested_by:
            requests = [r for r in requests if r.requested_by == requested_by]
        
        return sorted(requests, key=lambda r: r.requested_at, reverse=True)
    
    def get_quality_report(
        self,
        change_request_id: UUID,
    ) -> Optional[QualityReport]:
        """Recupera quality report de uma mudança"""
        for report in self._quality_reports.values():
            if report.change_request_id == change_request_id:
                return report
        return None
