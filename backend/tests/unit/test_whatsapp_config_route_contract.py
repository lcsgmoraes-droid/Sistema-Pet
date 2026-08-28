from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import whatsapp_config
from app.routes import whatsapp_routes
from app.whatsapp.schemas import TenantWhatsAppConfigResponse


SECRET_FIELDS = {"api_key", "webhook_secret", "openai_api_key"}


class _ConfigDb:
    def __init__(self, config):
        self.config = config

    def query(self, _model):
        return self

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.config


def _stored_config(**overrides):
    values = {
        "id": "whatsapp-config-1",
        "tenant_id": UUID("180d9cbf-5dcb-4676-bf11-dcbd91ed444b"),
        "provider": "360dialog",
        "api_key": "dialog-secret-value",
        "phone_number": "5511999999999",
        "webhook_url": "https://example.test/webhook",
        "webhook_secret": "webhook-secret-value",
        "openai_api_key": "openai-secret-value",
        "model_preference": "gpt-4o-mini",
        "auto_response_enabled": True,
        "human_handoff_keywords": None,
        "working_hours_start": None,
        "working_hours_end": None,
        "notificacoes_entrega_enabled": False,
        "bot_name": "CorePet",
        "greeting_message": None,
        "tone": "friendly",
        "created_at": datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _application_with_whatsapp_routes() -> FastAPI:
    app = FastAPI()
    app.include_router(whatsapp_config.router)
    app.include_router(whatsapp_routes.router)
    return app


def _iter_registered_routes(routes):
    """Suporta FastAPI que registra routers de forma imediata ou adiada."""
    for route in routes:
        included_router = getattr(route, "original_router", None)
        if included_router is not None:
            yield from _iter_registered_routes(included_router.routes)
        else:
            yield route


def _route_origins(app: FastAPI, method: str, path: str) -> list[str]:
    return [
        route.endpoint.__module__
        for route in _iter_registered_routes(app.routes)
        if getattr(route, "path", None) == path
        and method in (getattr(route, "methods", None) or set())
    ]


def test_whatsapp_config_routes_possuem_uma_unica_implementacao():
    app = _application_with_whatsapp_routes()

    for method in ("GET", "POST", "PUT", "DELETE"):
        assert _route_origins(app, method, "/whatsapp/config") == [
            "app.routers.whatsapp_config"
        ]

    assert _route_origins(app, "GET", "/whatsapp/config/stats") == [
        "app.routers.whatsapp_config"
    ]


def test_whatsapp_config_create_nao_exige_tenant_no_payload():
    create_route = next(
        route
        for route in whatsapp_config.router.routes
        if route.path == "/whatsapp/config" and "POST" in route.methods
    )

    body_model = create_route.body_field.field_info.annotation
    body_fields = body_model.model_fields
    assert "tenant_id" not in body_fields


def test_whatsapp_config_response_nao_declara_campos_secretos():
    response_fields = set(TenantWhatsAppConfigResponse.model_fields)

    assert SECRET_FIELDS.isdisjoint(response_fields)
    assert {
        "has_api_key",
        "has_webhook_secret",
        "has_openai_api_key",
    }.issubset(response_fields)


def test_whatsapp_config_http_informa_presenca_sem_expor_segredos():
    config = _stored_config()
    app = FastAPI()
    app.include_router(whatsapp_config.router)
    app.dependency_overrides[whatsapp_config.get_db] = lambda: _ConfigDb(config)
    app.dependency_overrides[whatsapp_config._tenant_whatsapp_config] = lambda: (
        config.tenant_id
    )

    response = TestClient(app).get("/whatsapp/config")

    assert response.status_code == 200
    payload = response.json()
    assert SECRET_FIELDS.isdisjoint(payload)
    assert payload["has_api_key"] is True
    assert payload["has_webhook_secret"] is True
    assert payload["has_openai_api_key"] is True
    assert "dialog-secret-value" not in response.text
    assert "webhook-secret-value" not in response.text
    assert "openai-secret-value" not in response.text


def test_whatsapp_config_indicadores_ignoram_valores_vazios():
    response = whatsapp_config._safe_config_response(
        _stored_config(api_key="", webhook_secret="   ", openai_api_key=None)
    )

    assert response.has_api_key is False
    assert response.has_webhook_secret is False
    assert response.has_openai_api_key is False
    assert SECRET_FIELDS.isdisjoint(response.model_dump())
