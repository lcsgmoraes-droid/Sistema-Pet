"""
Approval Service
Gerencia fluxo de aprovações multi-role
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.ai.governance.models import (
    ApprovalFlow,
    ApprovalRecord,
    ApprovalRole,
    ApprovalDecision,
    AIChangeRequest,
    ChangeRequestStatus,
    ChangeApprovalPolicy,
    DEFAULT_APPROVAL_POLICY,
)
from app.ai.governance.events import (
    AIChangeApprovalGiven,
)


class ApprovalService:
    """
    Gerencia aprovações de mudanças
    Responsabilidade: Coordenar aprovações multi-role e verificar quorum
    """
    
    def __init__(
        self,
        event_store,
        change_management_service,
    ):
        self.event_store = event_store
        self.change_management = change_management_service
        self._approval_flows: Dict[UUID, ApprovalFlow] = {}
        self.active_policy = DEFAULT_APPROVAL_POLICY
    
    def create_approval_flow(
        self,
        change_request_id: UUID,
    ) -> ApprovalFlow:
        """Cria fluxo de aprovação para uma mudança"""
        
        change_request = self.change_management.get_change_request(change_request_id)
        if not change_request:
            raise ValueError(f"Change request {change_request_id} not found")
        
        if change_request.status != ChangeRequestStatus.UNDER_REVIEW:
            raise ValueError("Change must be UNDER_REVIEW to create approval flow")
        
        # Determinar regra aplicável
        rule = self.active_policy.rules.get(change_request.impact_level)
        if not rule:
            raise ValueError(f"No approval rule for impact level {change_request.impact_level}")
        
        # Criar flow
        flow = ApprovalFlow(
            change_request_id=change_request_id,
            applicable_rule=rule,
            pending_roles=list(rule.required_roles),
        )
        
        self._approval_flows[flow.id] = flow
        
        return flow
    
    def submit_approval(
        self,
        change_request_id: UUID,
        approver_id: str,
        approver_name: str,
        approver_role: ApprovalRole,
        decision: ApprovalDecision,
        comments: str,
        conditions: Optional[List[str]] = None,
        review_notes: str = "",
        metrics_reviewed: Optional[Dict] = None,
    ) -> ApprovalRecord:
        """Submete aprovação individual"""
        
        # Encontrar flow ativo
        flow = self._get_active_flow(change_request_id)
        if not flow:
            raise ValueError(f"No active approval flow for change {change_request_id}")
        
        if flow.is_complete:
            raise ValueError("Approval flow is already complete")
        
        # Verificar se role já aprovou
        existing_approval = next(
            (a for a in flow.approvals if a.approver_role == approver_role),
            None
        )
        if existing_approval:
            raise ValueError(f"Role {approver_role.value} already provided approval")
        
        # Criar approval record
        approval = ApprovalRecord(
            change_request_id=change_request_id,
            approver_id=approver_id,
            approver_name=approver_name,
            approver_role=approver_role,
            decision=decision,
            comments=comments,
            conditions=conditions or [],
            review_notes=review_notes,
            metrics_reviewed=metrics_reviewed or {},
        )
        
        # Adicionar ao flow
        flow.add_approval(approval)
        self._approval_flows[flow.id] = flow
        
        # Emitir evento
        event = AIChangeApprovalGiven(
            event_id=uuid4(),
            aggregate_id=flow.id,
            change_request_id=change_request_id,
            approver_id=approver_id,
            approver_role=approver_role.value,
            decision=decision.value,
            comments=comments,
        )
        self.event_store.append(event)
        
        # Se flow completou, atualizar change request
        if flow.is_complete:
            if flow.is_approved:
                self.change_management.approve_change(change_request_id)
            else:
                # Pegar razão da rejeição
                rejection = next(
                    (a for a in flow.approvals if a.decision == ApprovalDecision.REJECTED),
                    None
                )
                reason = rejection.comments if rejection else "Rejected during approval flow"
                self.change_management.reject_change(
                    change_request_id,
                    rejected_by=rejection.approver_id if rejection else "system",
                    rejection_reason=reason,
                )
        
        return approval
    
    def get_approval_flow(
        self,
        change_request_id: UUID,
    ) -> Optional[ApprovalFlow]:
        """Recupera approval flow ativo"""
        return self._get_active_flow(change_request_id)
    
    def _get_active_flow(self, change_request_id: UUID) -> Optional[ApprovalFlow]:
        """Recupera flow ativo de um change request"""
        for flow in self._approval_flows.values():
            if flow.change_request_id == change_request_id:
                return flow
        return None
    
    def get_pending_approvals_for_role(
        self,
        role: ApprovalRole,
    ) -> List[Dict]:
        """Lista aprovações pendentes para um role"""
        
        pending = []
        
        for flow in self._approval_flows.values():
            if flow.is_complete:
                continue
            
            if role not in flow.pending_roles:
                continue
            
            # Pegar change request
            change_request = self.change_management.get_change_request(
                flow.change_request_id
            )
            if not change_request:
                continue
            
            pending.append({
                "change_request_id": flow.change_request_id,
                "change_request_title": change_request.title,
                "impact_level": change_request.impact_level.value,
                "requested_by": change_request.requested_by,
                "submitted_at": change_request.submitted_at,
                "approval_flow_id": flow.id,
                "pending_roles": [r.value for r in flow.pending_roles],
                "approved_count": flow.approved_count,
            })
        
        return pending
    
    def get_approval_history(
        self,
        change_request_id: UUID,
    ) -> List[ApprovalRecord]:
        """Recupera histórico de aprovações"""
        
        flow = self._get_active_flow(change_request_id)
        if not flow:
            return []
        
        return flow.approvals
    
    def get_approval_status_summary(
        self,
        change_request_id: UUID,
    ) -> Dict:
        """Resumo do status de aprovação"""
        
        flow = self._get_active_flow(change_request_id)
        if not flow:
            return {
                "exists": False,
            }
        
        change_request = self.change_management.get_change_request(change_request_id)
        
        return {
            "exists": True,
            "is_complete": flow.is_complete,
            "is_approved": flow.is_approved,
            "approved_count": flow.approved_count,
            "rejected_count": flow.rejected_count,
            "pending_roles": [r.value for r in flow.pending_roles],
            "required_roles": [r.value for r in flow.applicable_rule.required_roles],
            "min_approvals": flow.applicable_rule.min_approvals,
            "require_all_roles": flow.applicable_rule.require_all_roles,
            "change_status": change_request.status.value if change_request else None,
            "approvals": [
                {
                    "approver_name": a.approver_name,
                    "approver_role": a.approver_role.value,
                    "decision": a.decision.value,
                    "approved_at": a.approved_at.isoformat(),
                    "comments": a.comments,
                }
                for a in flow.approvals
            ],
        }
