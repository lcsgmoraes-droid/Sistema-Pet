import inspect
from pathlib import Path

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.auth.dependencies import get_current_user_and_tenant
from app.base_models import TenantScoped
from app.whatsapp import security_router
from app.whatsapp.security import (
    DataAccessLog,
    DataDeletionRequest,
    DataPrivacyConsent,
    SecurityAuditLog,
)


ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _depends_on_dependency(func, dependency, param_name: str = "tenant_id") -> bool:
    default = inspect.signature(func).parameters[param_name].default
    return getattr(default, "dependency", None) is dependency


def test_whatsapp_security_models_are_tenant_scoped_with_uuid_tenant_id():
    for model in (
        DataPrivacyConsent,
        DataAccessLog,
        DataDeletionRequest,
        SecurityAuditLog,
    ):
        assert issubclass(model, TenantScoped), model.__name__
        assert isinstance(model.__table__.c.tenant_id.type, PG_UUID), model.__name__
        assert model.__table__.c.tenant_id.nullable is False


def test_whatsapp_security_routes_use_selected_tenant_dependency():
    assert _depends_on_dependency(
        security_router._tenant_whatsapp_security,
        get_current_user_and_tenant,
        "user_and_tenant",
    )

    for func in (
        security_router.record_consent,
        security_router.check_consent,
        security_router.revoke_consent,
        security_router.request_data_deletion,
        security_router.list_deletion_requests,
        security_router.approve_deletion_request,
        security_router.export_user_data,
        security_router.get_security_logs,
        security_router.generate_webhook_secret,
    ):
        assert _depends_on_dependency(func, security_router._tenant_whatsapp_security)

    source = _source("backend/app/whatsapp/security_router.py")
    assert "Depends(get_current_user)" not in source
    assert "current_user.tenant_id" not in source


def test_whatsapp_security_background_callers_manage_tenant_context():
    security_source = _source("backend/app/whatsapp/security.py")
    privacy_ops_source = _source("backend/app/services/lgpd_consents.py")
    notification_source = _source("backend/app/campaigns/notification_service.py")

    assert (
        "from app.whatsapp.tenant_context import whatsapp_tenant_context"
        in security_source
    )
    assert "with whatsapp_tenant_context(self.tenant_id)" in security_source
    assert (
        "from app.whatsapp.tenant_context import whatsapp_tenant_context"
        in privacy_ops_source
    )
    assert "with whatsapp_tenant_context(self.tenant_id)" in privacy_ops_source
    assert (
        "from app.whatsapp.tenant_context import whatsapp_tenant_context"
        in notification_source
    )
    assert "with whatsapp_tenant_context(tenant_id)" in notification_source


def test_whatsapp_security_tenant_uuid_migration_exists():
    source = _source(
        "backend/alembic/versions/pp20260611a1_whatsapp_security_tenant_uuid.py"
    )

    for table_name in (
        "data_privacy_consents",
        "data_access_logs",
        "data_deletion_requests",
        "security_audit_logs",
    ):
        assert table_name in source

    assert 'postgresql_using="tenant_id::uuid"' in source
    assert "type_=postgresql.UUID(as_uuid=True)" in source
