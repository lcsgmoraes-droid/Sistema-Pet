"""
Governed Version Promotion Service
Integra versionamento com change management
"""
from typing import Optional
from uuid import UUID

from app.ai.versioning.registry import VersionRegistry
from app.ai.versioning.models import VersionStatus
from app.ai.governance.change_management import ChangeManagementService
from app.ai.governance.models import ChangeRequestStatus
from app.ai.governance.events import AIVersionPromotedToProduction


class GovernedVersionPromotion:
    """
    Wrapper que garante que versões só vão para ACTIVE
    se passarem por change management
    """
    
    def __init__(
        self,
        version_registry: VersionRegistry,
        change_management: ChangeManagementService,
        event_store,
    ):
        self.version_registry = version_registry
        self.change_management = change_management
        self.event_store = event_store
    
    def promote_to_production(
        self,
        version_id: UUID,
        change_request_id: UUID,
        promoted_by: str,
    ):
        """
        Promove versão para ACTIVE (produção)
        REQUER change request aprovado
        """
        
        # Validar change request
        change_request = self.change_management.get_change_request(change_request_id)
        if not change_request:
            raise ValueError(f"Change request {change_request_id} not found")
        
        if change_request.status != ChangeRequestStatus.APPROVED:
            raise ValueError(
                f"Change request must be APPROVED to promote to production. "
                f"Current status: {change_request.status.value}"
            )
        
        if change_request.behavior_version_id != version_id:
            raise ValueError(
                f"Change request is for version {change_request.behavior_version_id}, "
                f"but trying to promote {version_id}"
            )
        
        # Promover versão
        version = self.version_registry.promote_version(
            version_id=version_id,
            to_status=VersionStatus.ACTIVE,
            promoted_by=promoted_by,
            change_request_id=change_request_id,
        )
        
        # Emitir evento específico de produção
        event = AIVersionPromotedToProduction(
            event_id=UUID(),
            aggregate_id=version_id,
            behavior_version_id=version_id,
            version_name=version.version_name,
            change_request_id=change_request_id,
            promoted_by=promoted_by,
        )
        self.event_store.append(event)
        
        return version
    
    def can_promote_to_production(
        self,
        version_id: UUID,
    ) -> tuple[bool, Optional[str]]:
        """
        Verifica se versão pode ser promovida para produção
        Retorna (can_promote, reason_if_not)
        """
        
        version = self.version_registry.get_version(version_id)
        if not version:
            return False, "Version not found"
        
        if version.status != VersionStatus.TESTING:
            return False, f"Version must be in TESTING status. Current: {version.status.value}"
        
        # Verificar se existe change request aprovado
        change_requests = self.change_management.list_change_requests()
        approved_requests = [
            cr for cr in change_requests
            if cr.behavior_version_id == version_id
            and cr.status == ChangeRequestStatus.APPROVED
        ]
        
        if not approved_requests:
            return False, "No approved change request found for this version"
        
        return True, None
