from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middlewares import request_logging as request_logging_module
from app.middlewares.request_context import RequestContextMiddleware, get_request_id
from app.utils.logger import get_trace_id


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/probe")
    def probe():
        return {
            "request_id": get_request_id(),
            "trace_id": get_trace_id(),
        }

    return TestClient(app)


def test_preserves_safe_client_request_id_and_uses_it_as_trace_id():
    client_request_id = "front-pdv-20260516_abc.123"

    response = _client().get("/probe", headers={"X-Request-ID": client_request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == client_request_id
    assert response.json() == {
        "request_id": client_request_id,
        "trace_id": client_request_id,
    }


def test_replaces_unsafe_client_request_id_with_generated_uuid():
    unsafe_request_id = "x" * 200

    response = _client().get("/probe", headers={"X-Request-ID": unsafe_request_id})

    assert response.status_code == 200
    generated_request_id = response.headers["X-Request-ID"]
    assert generated_request_id != unsafe_request_id
    assert str(UUID(generated_request_id)) == generated_request_id
    assert response.json() == {
        "request_id": generated_request_id,
        "trace_id": generated_request_id,
    }


def test_http_request_log_includes_request_id(monkeypatch):
    captured: list[dict] = []

    class CaptureLogger:
        def debug(self, **kwargs):
            captured.append(kwargs)

        def warning(self, **kwargs):
            captured.append(kwargs)

        def error(self, **kwargs):
            captured.append(kwargs)

    app = FastAPI()

    @app.get("/probe")
    def probe():
        return {"ok": True}

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(request_logging_module.RequestLoggingMiddleware)
    monkeypatch.setattr(request_logging_module, "logger", CaptureLogger())

    client_request_id = "front-pdv-20260516-log"
    response = TestClient(app).get(
        "/probe",
        headers={"X-Request-ID": client_request_id},
    )

    assert response.status_code == 200
    assert captured
    assert captured[-1]["event"] == "http_request"
    assert captured[-1]["request_id"] == client_request_id
    assert captured[-1]["method"] == "GET"
    assert captured[-1]["path"] == "/probe"
