from fastapi import FastAPI

from app.routers import whatsapp_config
from app.routes import whatsapp_routes


def _application_with_whatsapp_routes() -> FastAPI:
    app = FastAPI()
    app.include_router(whatsapp_config.router)
    app.include_router(whatsapp_routes.router)
    return app


def _route_origins(app: FastAPI, method: str, path: str) -> list[str]:
    return [
        route.endpoint.__module__
        for route in app.routes
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
