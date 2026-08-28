import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import health_router
from app.main_basic_routes import register_basic_routes
from app.routes.health_routes import router as infrastructure_health_router


def _health_application() -> FastAPI:
    app = FastAPI()
    app.include_router(infrastructure_health_router)
    app.include_router(health_router.router)
    register_basic_routes(app)
    return app


def _get_route_origins(app: FastAPI, path: str) -> list[str]:
    return [
        route.endpoint.__module__
        for route in app.routes
        if getattr(route, "path", None) == path
        and "GET" in (getattr(route, "methods", None) or set())
    ]


def _response_payload(response: JSONResponse) -> dict:
    return json.loads(response.body.decode("utf-8"))


def test_health_e_readiness_possuem_uma_unica_fonte_oficial():
    app = _health_application()

    assert _get_route_origins(app, "/health") == ["app.routes.health_routes"]
    assert _get_route_origins(app, "/ready") == ["app.routes.health_routes"]
    assert _get_route_origins(app, "/health/watchdog") == ["app.health_router"]


def test_watchdog_publico_nao_expoe_detalhes_internos(monkeypatch):
    class FailingEngine:
        class Pool:
            @staticmethod
            def status():
                raise RuntimeError("estado-do-pool-indisponivel")

        pool = Pool()

        @staticmethod
        def connect():
            raise RuntimeError("senha-interna-nao-pode-vazar")

    monkeypatch.setattr(health_router, "engine", FailingEngine())

    response = asyncio.run(health_router.watchdog_health())
    payload = _response_payload(response)

    assert response.status_code == 503
    assert payload["status"] == "unhealthy"
    assert payload["database"] == "error"
    assert "pool" not in payload
    assert "error_type" not in payload
    assert "senha-interna-nao-pode-vazar" not in response.body.decode("utf-8")


def test_watchdog_usa_limite_seguro_quando_configuracao_e_invalida(monkeypatch):
    for invalid_value in ("valor-invalido", "0", "-1", "nan", "inf"):
        monkeypatch.setenv("WATCHDOG_DB_MAX_LATENCY_MS", invalid_value)
        assert (
            health_router._watchdog_max_latency_ms()
            == health_router.DEFAULT_WATCHDOG_DB_MAX_LATENCY_MS
        )


def test_watchdog_saudavel_preserva_contrato_necessario(monkeypatch):
    class Connection:
        @staticmethod
        def execute(_statement):
            return None

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _traceback):
            return False

    class HealthyEngine:
        class Pool:
            @staticmethod
            def status():
                return "pool-interno"

        pool = Pool()

        @staticmethod
        def connect():
            return Connection()

    monkeypatch.setattr(health_router, "engine", HealthyEngine())

    payload = asyncio.run(health_router.watchdog_health())

    assert payload["status"] == "healthy"
    assert payload["database"] == "connected"
    assert payload["latency_ms"] >= 0
    assert "pool" not in payload
