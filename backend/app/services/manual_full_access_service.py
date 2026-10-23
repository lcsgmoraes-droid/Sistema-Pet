"""Concessao FULL operacional auditada, independente da situacao financeira."""

from sqlalchemy.orm import Session

from app.models import Tenant
from app.platform_auth_models import PlatformAdmin
from app.services.billing_access import manual_full_access_allowed
from app.services.business_audit_service import log_business_event
from app.tenancy.context import tenant_context


class ManualFullAccessError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def grant_manual_full_access(
    db: Session,
    *,
    tenant: Tenant,
    actor_platform_admin_id: int,
    motivo: str,
    commit: bool = True,
) -> dict:
    """Registra uma concessao permanente sem alterar cobrancas, plano ou trial."""
    administrator = (
        db.query(PlatformAdmin)
        .filter(
            PlatformAdmin.id == actor_platform_admin_id,
            PlatformAdmin.is_active.is_(True),
        )
        .first()
    )
    if administrator is None:
        raise ManualFullAccessError(403, "Acesso negado")
    reason = str(motivo or "").strip()
    if not 10 <= len(reason) <= 1000:
        raise ManualFullAccessError(
            400, "Informe o motivo da concessao com 10 a 1000 caracteres."
        )

    previous = bool(tenant.manual_full_access)
    tenant.manual_full_access = True
    with tenant_context(tenant.id):
        audit = log_business_event(
            db=db,
            tenant_id=tenant.id,
            user_id=None,
            event="config.manual_full_access_granted",
            entity_type="tenant_access",
            entity_id=None,
            old_value={"manual_full_access": previous},
            metadata={
                "manual_full_access": True,
                "reason": reason,
                "actor_platform_admin_id": administrator.id,
            },
            details="Concessao manual de acesso FULL operacional, sem alteracao financeira.",
            commit=False,
        )
        if audit is None:
            raise ManualFullAccessError(500, "Nao foi possivel auditar a concessao.")
    if commit:
        db.commit()
    return {
        "ok": True,
        "tenant_id": str(tenant.id),
        "manual_full_access": True,
        "acesso_completo_manual": manual_full_access_allowed(tenant),
    }
