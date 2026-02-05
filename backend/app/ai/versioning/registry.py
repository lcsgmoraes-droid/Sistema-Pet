"""
AI Version Registry Service
Gerencia o registro e lifecycle de versões de comportamento
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from app.ai.versioning.models import (
    AIBehaviorVersion,
    ComponentType,
    ComponentVersion,
    VersionStatus,
    TenantVersionAssignment,
)
from app.ai.versioning.events import (
    BehaviorVersionCreated,
    BehaviorVersionPromoted,
    TenantVersionActivated,
    TenantVersionRolledBack,
)


class VersionRegistry:
    """
    Registry central de versões de comportamento
    Responsabilidade: Gerenciar ciclo de vida de versões
    """
    
    def __init__(self, event_store):
        self.event_store = event_store
        self._versions: Dict[UUID, AIBehaviorVersion] = {}
        self._tenant_assignments: Dict[str, TenantVersionAssignment] = {}
        self._version_history: Dict[str, List[UUID]] = {}  # tenant_id -> [version_ids]
    
    def create_version(
        self,
        version_name: str,
        version_tag: str,
        components: Dict[ComponentType, ComponentVersion],
        created_by: str,
        description: str,
        changelog: str,
    ) -> AIBehaviorVersion:
        """Cria nova versão de comportamento"""
        
        version = AIBehaviorVersion(
            version_name=version_name,
            version_tag=version_tag,
            components=components,
            created_by=created_by,
            description=description,
            changelog=changelog,
            status=VersionStatus.DRAFT,
        )
        
        self._versions[version.id] = version
        
        # Emitir evento
        event = BehaviorVersionCreated(
            event_id=UUID(),
            aggregate_id=version.id,
            version_name=version_name,
            version_tag=version_tag,
            created_by=created_by,
            component_versions={
                ct.value: cv.version for ct, cv in components.items()
            }
        )
        self.event_store.append(event)
        
        return version
    
    def promote_version(
        self,
        version_id: UUID,
        to_status: VersionStatus,
        promoted_by: str,
        change_request_id: Optional[UUID] = None,
    ) -> AIBehaviorVersion:
        """Promove versão no ciclo de vida"""
        
        version = self._versions.get(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        from_status = version.status
        
        # Se promovendo para ACTIVE, exige change request aprovado
        if to_status == VersionStatus.ACTIVE and not change_request_id:
            raise ValueError(
                "change_request_id is required when promoting to ACTIVE. "
                "All production deployments must go through change management."
            )
        
        # Validar transição
        valid_transitions = {
            VersionStatus.DRAFT: [VersionStatus.TESTING],
            VersionStatus.TESTING: [VersionStatus.ACTIVE, VersionStatus.DRAFT],
            VersionStatus.ACTIVE: [VersionStatus.DEPRECATED],
            VersionStatus.DEPRECATED: [VersionStatus.ARCHIVED],
        }
        
        if to_status not in valid_transitions.get(from_status, []):
            raise ValueError(
                f"Invalid transition: {from_status} -> {to_status}"
            )
        
        # Criar nova versão com status atualizado
        updated_version = version.model_copy(update={"status": to_status})
        self._versions[version_id] = updated_version
        
        # Emitir evento
        event = BehaviorVersionPromoted(
            event_id=UUID(),
            aggregate_id=version_id,
            from_status=from_status.value,
            to_status=to_status.value,
            promoted_by=promoted_by,
        )
        self.event_store.append(event)
        
        return updated_version
    
    def get_version(self, version_id: UUID) -> Optional[AIBehaviorVersion]:
        """Recupera versão por ID"""
        return self._versions.get(version_id)
    
    def get_version_by_name(self, version_name: str) -> Optional[AIBehaviorVersion]:
        """Recupera versão por nome"""
        for version in self._versions.values():
            if version.version_name == version_name:
                return version
        return None
    
    def list_versions(
        self,
        status: Optional[VersionStatus] = None,
        tag: Optional[str] = None,
    ) -> List[AIBehaviorVersion]:
        """Lista versões com filtros"""
        versions = list(self._versions.values())
        
        if status:
            versions = [v for v in versions if v.status == status]
        
        if tag:
            versions = [v for v in versions if v.version_tag == tag]
        
        return sorted(versions, key=lambda v: v.created_at, reverse=True)
    
    def assign_version_to_tenant(
        self,
        tenant_id: str,
        behavior_version_id: UUID,
        activated_by: str,
    ) -> TenantVersionAssignment:
        """Atribui versão a um tenant"""
        
        version = self.get_version(behavior_version_id)
        if not version:
            raise ValueError(f"Version {behavior_version_id} not found")
        
        if version.status != VersionStatus.ACTIVE:
            raise ValueError(
                f"Cannot assign version with status {version.status}. "
                "Only ACTIVE versions can be assigned."
            )
        
        # Recuperar versão anterior
        current_assignment = self._tenant_assignments.get(tenant_id)
        previous_version_id = (
            current_assignment.behavior_version_id if current_assignment else None
        )
        
        # Criar assignment
        assignment = TenantVersionAssignment(
            tenant_id=tenant_id,
            behavior_version_id=behavior_version_id,
            activated_at=datetime.utcnow(),
            activated_by=activated_by,
            previous_version_id=previous_version_id,
        )
        
        self._tenant_assignments[tenant_id] = assignment
        
        # Adicionar ao histórico
        if tenant_id not in self._version_history:
            self._version_history[tenant_id] = []
        self._version_history[tenant_id].append(behavior_version_id)
        
        # Emitir evento
        event = TenantVersionActivated(
            event_id=UUID(),
            aggregate_id=assignment.id,
            tenant_id=tenant_id,
            behavior_version_id=behavior_version_id,
            version_name=version.version_name,
            activated_by=activated_by,
            previous_version_id=previous_version_id,
        )
        self.event_store.append(event)
        
        return assignment
    
    def get_tenant_version(self, tenant_id: str) -> Optional[TenantVersionAssignment]:
        """Recupera versão ativa de um tenant"""
        return self._tenant_assignments.get(tenant_id)
    
    def rollback_tenant_version(
        self,
        tenant_id: str,
        rolled_back_by: str,
        reason: str,
    ) -> TenantVersionAssignment:
        """Faz rollback da versão de um tenant para a anterior"""
        
        current_assignment = self._tenant_assignments.get(tenant_id)
        if not current_assignment:
            raise ValueError(f"No version assigned to tenant {tenant_id}")
        
        if not current_assignment.previous_version_id:
            raise ValueError(f"No previous version available for tenant {tenant_id}")
        
        # Reativar versão anterior
        previous_version_id = current_assignment.previous_version_id
        from_version_id = current_assignment.behavior_version_id
        
        assignment = self.assign_version_to_tenant(
            tenant_id=tenant_id,
            behavior_version_id=previous_version_id,
            activated_by=rolled_back_by,
        )
        
        # Emitir evento específico de rollback
        event = TenantVersionRolledBack(
            event_id=UUID(),
            aggregate_id=assignment.id,
            tenant_id=tenant_id,
            from_version_id=from_version_id,
            to_version_id=previous_version_id,
            rolled_back_by=rolled_back_by,
            reason=reason,
        )
        self.event_store.append(event)
        
        return assignment
    
    def get_tenant_version_history(self, tenant_id: str) -> List[UUID]:
        """Recupera histórico de versões de um tenant"""
        return self._version_history.get(tenant_id, [])
    
    def update_tenant_metrics(
        self,
        tenant_id: str,
        decision_count: int,
        success_count: int,
        fallback_count: int,
        avg_confidence: float,
        avg_trust_score: float,
    ):
        """Atualiza métricas de um tenant assignment"""
        assignment = self._tenant_assignments.get(tenant_id)
        if not assignment:
            return
        
        # Criar assignment atualizado (imutável)
        updated = assignment.model_copy(update={
            "decision_count": decision_count,
            "success_count": success_count,
            "fallback_count": fallback_count,
            "avg_confidence": avg_confidence,
            "avg_trust_score": avg_trust_score,
        })
        
        self._tenant_assignments[tenant_id] = updated
