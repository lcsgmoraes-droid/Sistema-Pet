import inspect
from pathlib import Path

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.auth.dependencies import get_current_user_and_tenant
from app.base_models import TenantScoped
from app.routes import whatsapp_routes
from app.routers import whatsapp_config
from app.whatsapp.models import (
    TenantWhatsAppConfig,
    WhatsAppMessage,
    WhatsAppMetric,
    WhatsAppSession,
)
from app.whatsapp.models_handoff import WhatsAppHandoff, WhatsAppInternalNote


ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _depends_on_dependency(func, dependency, param_name: str = "tenant_id") -> bool:
    default = inspect.signature(func).parameters[param_name].default
    return getattr(default, "dependency", None) is dependency


def test_whatsapp_core_models_are_tenant_scoped_with_uuid_tenant_id():
    for model in (
        TenantWhatsAppConfig,
        WhatsAppSession,
        WhatsAppMessage,
        WhatsAppMetric,
    ):
        assert issubclass(model, TenantScoped), model.__name__
        assert isinstance(model.__table__.c.tenant_id.type, PG_UUID), model.__name__
        assert model.__table__.c.tenant_id.nullable is False


def test_handoff_session_ids_match_legacy_whatsapp_session_text_ids():
    assert str(WhatsAppSession.__table__.c.id.type).upper() in {"VARCHAR", "TEXT"}
    assert str(WhatsAppHandoff.__table__.c.session_id.type).upper() in {"VARCHAR", "TEXT"}
    assert str(WhatsAppInternalNote.__table__.c.session_id.type).upper() in {"VARCHAR", "TEXT"}


def test_whatsapp_config_routes_use_selected_tenant_dependency():
    assert _depends_on_dependency(
        whatsapp_config._tenant_whatsapp_config,
        get_current_user_and_tenant,
        "user_and_tenant",
    )

    for func in (
        whatsapp_config.get_whatsapp_config,
        whatsapp_config.create_whatsapp_config,
        whatsapp_config.update_whatsapp_config,
        whatsapp_config.delete_whatsapp_config,
        whatsapp_config.test_webhook_connection,
        whatsapp_config.get_whatsapp_stats,
    ):
        assert _depends_on_dependency(func, whatsapp_config._tenant_whatsapp_config)

    source = _source("backend/app/routers/whatsapp_config.py")
    assert "Depends(get_current_user)" not in source
    assert "current_user.tenant_id" not in source


def test_legacy_whatsapp_routes_use_selected_tenant_dependency():
    assert _depends_on_dependency(
        whatsapp_routes._tenant_whatsapp,
        get_current_user_and_tenant,
        "user_and_tenant",
    )

    for func in (
        whatsapp_routes.get_config,
        whatsapp_routes.create_config,
        whatsapp_routes.update_config,
        whatsapp_routes.delete_config,
        whatsapp_routes.get_stats,
        whatsapp_routes.test_tool,
        whatsapp_routes.test_message,
        whatsapp_routes.test_conversation,
    ):
        assert _depends_on_dependency(func, whatsapp_routes._tenant_whatsapp)

    source = _source("backend/app/routes/whatsapp_routes.py")
    assert "current_user: User = Depends(get_current_user_and_tenant)" not in source
    assert "current_user.tenant_id" not in source


def test_whatsapp_public_and_background_paths_manage_tenant_context():
    webhook_source = _source("backend/app/whatsapp/webhook.py")
    sender_source = _source("backend/app/whatsapp/sender.py")
    processor_source = _source("backend/app/whatsapp/processor.py")
    context_builder_source = _source("backend/app/ai/context_builder.py")
    context_manager_source = _source("backend/app/whatsapp/context_manager.py")
    function_handlers_source = _source("backend/app/whatsapp/function_handlers.py")
    tools_source = _source("backend/app/whatsapp/tools.py")
    vet_exam_files_source = _source("backend/app/veterinario_exames_arquivos.py")

    assert "from app.whatsapp.tenant_context import whatsapp_tenant_context" in webhook_source
    assert webhook_source.count("with whatsapp_tenant_context(tenant_id)") >= 4
    assert "from app.whatsapp.tenant_context import whatsapp_tenant_context" in sender_source
    assert "with whatsapp_tenant_context(tenant_id)" in sender_source
    assert "from app.whatsapp.tenant_context import whatsapp_tenant_context" in processor_source
    assert processor_source.count("with whatsapp_tenant_context(self.tenant_id)") >= 2
    assert "from app.whatsapp.tenant_context import whatsapp_tenant_context" in context_builder_source
    assert "with whatsapp_tenant_context(tenant_id)" in context_builder_source
    assert "from app.whatsapp.tenant_context import whatsapp_tenant_context" in context_manager_source
    assert "with whatsapp_tenant_context(tenant_id)" in context_manager_source
    assert "from app.whatsapp.tenant_context import whatsapp_tenant_context" in function_handlers_source
    assert "with whatsapp_tenant_context(tenant_id)" in function_handlers_source
    assert "from app.whatsapp.tenant_context import whatsapp_tenant_context" in tools_source
    assert "with whatsapp_tenant_context(self.tenant_id)" in tools_source
    assert "from .whatsapp.tenant_context import whatsapp_tenant_context" in vet_exam_files_source
    assert "with whatsapp_tenant_context(tenant_id)" in vet_exam_files_source


def test_health_router_uses_raw_counts_for_global_whatsapp_metrics():
    source = _source("backend/app/health_router.py")
    assert "db.query(WhatsAppSession)" not in source
    assert "db.query(WhatsAppMessage)" not in source
    assert "SELECT count(*) FROM whatsapp_ia_sessions" in source
    assert "SELECT count(*) FROM whatsapp_ia_messages" in source
