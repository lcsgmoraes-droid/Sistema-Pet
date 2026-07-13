import logging
from unittest.mock import Mock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app import config as app_config
from app.main_http import register_exception_handlers
from app.middlewares.request_context import RequestContextMiddleware
from app.security.error_sanitization import sanitize_validation_errors


SENSITIVE_VALUE = "password=super-secret-value"


def _test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    class LoginPayload(BaseModel):
        password: int

    @app.post("/validate")
    async def validate_payload(_payload: LoginPayload):
        return {"ok": True}

    @app.get("/http-500")
    async def http_500():
        raise HTTPException(status_code=500, detail=SENSITIVE_VALUE)

    @app.get("/http-400")
    async def http_400():
        raise HTTPException(status_code=400, detail="Regra de negocio invalida")

    @app.get("/unhandled")
    async def unhandled():
        raise RuntimeError(SENSITIVE_VALUE)

    return app


def test_validation_error_does_not_echo_submitted_secret(caplog):
    caplog.set_level(logging.WARNING, logger="app.main_http")
    with TestClient(_test_app(), raise_server_exceptions=False) as client:
        response = client.post("/validate", json={"password": SENSITIVE_VALUE})

    assert response.status_code == 422
    assert SENSITIVE_VALUE not in response.text
    assert SENSITIVE_VALUE not in caplog.text
    assert response.json()["details"] == [
        {
            "type": "int_parsing",
            "loc": ["body", "password"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
        }
    ]


def test_custom_validation_context_is_removed():
    errors = [
        {
            "type": "value_error",
            "loc": ("body", "password"),
            "msg": f"Value error, {SENSITIVE_VALUE}",
            "input": SENSITIVE_VALUE,
            "ctx": {"error": ValueError(SENSITIVE_VALUE)},
        }
    ]

    assert sanitize_validation_errors(errors) == [
        {
            "type": "value_error",
            "loc": ["body", "password"],
            "msg": "Valor invalido",
        }
    ]


def test_http_500_is_sanitized_in_production(monkeypatch, caplog):
    monkeypatch.setattr(app_config, "ENVIRONMENT", "production")
    caplog.set_level(logging.WARNING, logger="app.main_http")
    with TestClient(_test_app(), raise_server_exceptions=False) as client:
        response = client.get("/http-500")

    assert response.status_code == 500
    assert response.json() == {
        "error": "internal_server_error",
        "message": "Erro interno no servidor. Nossa equipe foi notificada.",
    }
    assert SENSITIVE_VALUE not in response.text
    assert SENSITIVE_VALUE not in caplog.text


def test_http_400_keeps_business_detail_in_production(monkeypatch):
    monkeypatch.setattr(app_config, "ENVIRONMENT", "production")
    with TestClient(_test_app(), raise_server_exceptions=False) as client:
        response = client.get("/http-400")

    assert response.status_code == 400
    assert response.json() == {"detail": "Regra de negocio invalida"}


def test_unhandled_error_is_sanitized_in_staging(monkeypatch, caplog):
    monkeypatch.setattr(app_config, "ENVIRONMENT", "staging")
    caplog.set_level(logging.ERROR)
    with TestClient(_test_app(), raise_server_exceptions=False) as client:
        response = client.get("/unhandled")

    assert response.status_code == 500
    assert response.json()["error"] == "internal_server_error"
    assert SENSITIVE_VALUE not in response.text
    assert SENSITIVE_VALUE not in caplog.text


def test_request_context_does_not_persist_exception_message_in_production(
    monkeypatch,
):
    monkeypatch.setattr(app_config, "ENVIRONMENT", "production")
    record_event = Mock()
    monkeypatch.setattr(
        "app.middlewares.request_context.record_request_event", record_event
    )

    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/middleware-error")
    async def middleware_error():
        raise RuntimeError(SENSITIVE_VALUE)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/middleware-error")

    assert response.status_code == 500
    assert record_event.call_args.kwargs["exception_message"] is None
