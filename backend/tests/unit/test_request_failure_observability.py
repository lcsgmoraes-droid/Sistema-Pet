import asyncio
import json
import os
import threading
import anyio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import InvalidRequestError

from app import config as app_config
from app.main_http import configure_middlewares, register_exception_handlers
from app.middlewares.request_context import (
    RequestContextMiddleware,
    get_request_id,
    get_request_metadata,
)
from app.middlewares.security_headers import SecurityHeadersMiddleware
from app.services import error_event_reporter
from app.services.ops_persistence_service import _row_to_error_event
from app.services.request_failure_diagnostics import exception_diagnostics


@pytest.fixture
def captured(monkeypatch):
    events = []
    journeys = []
    monkeypatch.setattr(app_config, "ENVIRONMENT", "production")
    monkeypatch.setattr(
        "app.middlewares.request_context.record_request_event",
        lambda **event: events.append(event),
    )
    monkeypatch.setattr(
        "app.middlewares.request_context.record_http_journey_event",
        lambda **event: journeys.append(event),
    )
    return events, journeys


def test_unhandled_error_records_the_sent_500_once_with_safe_origin(captured, caplog):
    events, _journeys = captured
    app = FastAPI()
    configure_middlewares(app, SimpleNamespace())
    register_exception_handlers(app)

    @app.get("/probe")
    async def fail():
        raise RuntimeError("password=secret-query-value")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/probe", headers={"X-Request-ID": "diagnostic-probe"})

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "diagnostic-probe"
    assert response.json()["request_id"] == "diagnostic-probe"
    assert len(events) == 1
    event = events[0]
    assert event["status_code"] == 500
    assert event["status_source"] == "asgi_response_start"
    assert event["exception_type"] == "RuntimeError"
    assert event["exception_message"] is None
    assert event["diagnostic_code"] == "unhandled_exception"
    assert any(":fail:" in origin for origin in event["exception_origin"])
    assert len(event["exception_origin"]) <= 8
    assert all(
        "/" not in origin and "\\" not in origin for origin in event["exception_origin"]
    )
    assert "secret-query-value" not in str(event)
    assert "secret-query-value" not in response.text + caplog.text


def test_http_exception_503_retains_the_actual_response_status(captured):
    events, _journeys = captured
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    @app.get("/probe")
    async def fail():
        raise HTTPException(503, "secret")

    response = TestClient(app).get("/probe")
    assert response.status_code == 503
    assert len(events) == 1
    assert events[0]["status_code"] == 503
    assert events[0]["exception_type"] is None


def test_complete_response_through_all_middleware_is_not_a_cancellation(captured):
    events, journeys = captured
    app = FastAPI()
    configure_middlewares(app, SimpleNamespace())
    register_exception_handlers(app)

    @app.post("/auth/login-multitenant")
    async def probe():
        return {"request_id": get_request_id()}

    response = TestClient(app).post(
        "/auth/login-multitenant", headers={"X-Request-ID": "full-stack"}
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "full-stack"
    assert response.json()["request_id"] == "full-stack"
    assert len(events) == 1
    assert events[0]["status_code"] == 200
    assert not events[0].get("diagnostic_code")
    assert len(journeys) == 1


def _scope(path="/probe", request_id="asgi-probe"):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [(b"x-request-id", request_id.encode())],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }


def test_handled_no_response_disconnect_is_204_without_a_500(captured):
    events, journeys = captured

    async def fail(_scope, _receive, _send):
        raise RuntimeError("No response returned.")

    async def receive():
        return {"type": "http.disconnect"}

    sent = []

    async def send(message):
        sent.append(message)

    app = RequestContextMiddleware(SecurityHeadersMiddleware(fail))
    asyncio.run(app(_scope(), receive, send))
    assert sent[0]["status"] == 204
    assert len(events) == 1
    assert events[0]["status_code"] == 204
    assert events[0]["diagnostic_code"] == "client_disconnected"
    assert events[0]["exception_type"] is None
    assert journeys == []


def test_cancellation_has_unknown_http_status_and_is_not_a_500(captured):
    events, journeys = captured

    async def cancelled(_scope, _receive, _send):
        raise asyncio.CancelledError()

    async def receive():
        return {"type": "http.disconnect"}

    async def send(_message):
        pytest.fail("Cancellation must not manufacture a response")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(RequestContextMiddleware(cancelled)(_scope(), receive, send))
    assert len(events) == 1
    assert events[0]["status_code"] is None
    assert events[0]["diagnostic_code"] == "request_cancelled"
    assert journeys == []


def test_failed_send_does_not_claim_the_500_was_sent(captured):
    events, _journeys = captured
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    @app.get("/probe")
    async def fail():
        raise RuntimeError("route failure")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message):
        raise OSError("socket closed")

    with pytest.raises(OSError):
        asyncio.run(app(_scope(), receive, send))
    assert len(events) == 1
    assert events[0]["status_code"] is None
    assert events[0]["status_source"] == "not_sent"


def test_exception_during_response_stream_keeps_200_and_counts_incomplete_failure(
    captured, monkeypatch
):
    events, _journeys = captured
    sent = []

    async def stream(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send(
            {"type": "http.response.body", "body": b"partial", "more_body": True}
        )
        raise RuntimeError("stream failed")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    with pytest.raises(RuntimeError, match="stream failed"):
        asyncio.run(RequestContextMiddleware(stream)(_scope(), receive, send))
    assert sent[0]["status"] == 200
    assert len(events) == 1
    assert events[0]["status_code"] == 200
    assert events[0]["response_incomplete"] is True
    assert events[0]["diagnostic_code"] == "response_stream_failure"
    monkeypatch.setattr(
        error_event_reporter, "get_error_events", lambda **_kwargs: events
    )
    summary = error_event_reporter.summarize_error_events()
    assert summary["errors_5xx"] == 0
    assert summary["unknown_status_failures"] == 0
    assert summary["response_failures"] == 1
    assert summary["failed_requests"] == 1


def test_cancelled_anyio_scope_still_writes_diagnostic_and_preserves_cancellation(
    captured,
):
    events, _journeys = captured
    returned_normally = False

    async def wait(_scope, _receive, _send):
        await anyio.sleep(10)

    async def receive():
        return {"type": "http.disconnect"}

    async def send(_message):
        pytest.fail("Cancelled request must not manufacture a response")

    async def run():
        nonlocal returned_normally
        with anyio.CancelScope() as cancellation:
            cancellation.cancel()
            await RequestContextMiddleware(wait)(_scope(), receive, send)
            returned_normally = True
        assert cancellation.cancelled_caught is True

    asyncio.run(run())
    assert returned_normally is False
    assert len(events) == 1
    assert events[0]["diagnostic_code"] == "request_cancelled"
    assert events[0]["status_code"] is None


def test_concurrent_disconnects_preserve_other_request_ids_and_thread_context(
    captured, monkeypatch
):
    events, _journeys = captured
    caller_thread = threading.get_ident()
    thread_context = []

    def capture(**event):
        events.append(event)
        thread_context.append(
            (threading.get_ident(), get_request_id(), event["request_id"])
        )

    monkeypatch.setattr("app.middlewares.request_context.record_request_event", capture)

    async def inner(scope, receive, send):
        await asyncio.sleep(0)
        if scope["path"] == "/abort":
            assert (await receive())["type"] == "http.disconnect"
            return
        assert get_request_id() == scope["expected_request_id"]
        assert get_request_metadata()["path"] == "/probe"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    app = RequestContextMiddleware(inner)

    async def one(index):
        scope = _scope("/abort" if index % 2 else "/probe", f"req-{index}")
        scope["expected_request_id"] = f"req-{index}"
        sent = []

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        await app(scope, receive, send)
        assert get_request_id() is None
        if sent:
            assert (b"x-request-id", f"req-{index}".encode()) in sent[0]["headers"]

    async def run():
        await asyncio.gather(*(one(index) for index in range(40)))

    asyncio.run(run())
    assert len(events) == 40
    assert len({event["request_id"] for event in events}) == 40
    assert (
        sum(event.get("diagnostic_code") == "client_disconnected" for event in events)
        == 20
    )
    assert all(event["status_code"] != 500 for event in events)
    assert all(
        thread_id != caller_thread and context_id == event_id
        for thread_id, context_id, event_id in thread_context
    )


def test_summary_separates_legacy_unknown_failures_from_5xx_and_cancellations(
    monkeypatch,
):
    monkeypatch.setattr(
        error_event_reporter,
        "get_error_events",
        lambda **_kwargs: [
            {"status_code": None, "exception_type": "RuntimeError"},
            {"status_code": None, "exception_type": "InvalidRequestError"},
            {"status_code": 500, "exception_type": "RuntimeError"},
            {
                "status_code": None,
                "exception_type": "CancelledError",
                "diagnostic_code": "request_cancelled",
            },
            {"status_code": 204, "diagnostic_code": "client_disconnected"},
            {"status_code": 200, "duration_ms": 4000},
        ],
    )
    summary = error_event_reporter.summarize_error_events()
    assert summary["errors_5xx"] == 1
    assert summary["unknown_status_failures"] == 2
    assert summary["cancellations"] == 2
    assert dict(summary["by_diagnostic_code"])["legacy_unknown_status"] == 2
    assert summary["slow_requests"] == 1


def test_safe_diagnostics_distinguish_shared_collection_failure_without_its_data():
    try:
        raise RuntimeError("dictionary changed size during iteration")
    except RuntimeError as exc:
        details = exception_diagnostics(exc)
    assert details["diagnostic_code"] == "shared_collection_changed"
    assert details["exception_origin"]

    details = exception_diagnostics(
        InvalidRequestError("One or more mappers failed to initialize; secret")
    )
    assert details["diagnostic_code"] == "orm_mapper_initialization"
    assert "secret" not in str(details)


def test_persistence_returns_safe_diagnostics_from_existing_json_payload():
    row = SimpleNamespace(
        created_at=None,
        request_id="probe",
        tenant_id=None,
        user_id=None,
        user_email=None,
        method="GET",
        path="/probe",
        status_code=None,
        duration_ms=10,
        exception_type="RuntimeError",
        exception_message=None,
        client_ip=None,
        user_agent=None,
        source="request_context",
        payload={
            "diagnostic_code": "tenant_context_missing",
            "exception_origin": ["filters.py:query:42"],
            "pid": 123,
            "status_source": "not_sent",
        },
    )
    event = _row_to_error_event(row)
    assert event["status_code"] is None
    assert event["diagnostic_code"] == "tenant_context_missing"
    assert event["exception_origin"] == ["filters.py:query:42"]
    assert event["pid"] == 123


def test_reporter_writes_pid_and_safe_origin_without_using_request_db(
    monkeypatch, tmp_path
):
    log_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(error_event_reporter, "ERROR_EVENT_LOG_PATH", str(log_path))

    def no_database():
        raise OSError("Database telemetry disabled for this test")

    monkeypatch.setattr("app.db.SessionLocal", no_database)
    from starlette.requests import Request

    try:
        raise RuntimeError("[ORM FAIL-FAST] secret-data")
    except RuntimeError as exc:
        diagnostics = exception_diagnostics(exc)
    error_event_reporter.record_request_event(
        request=Request(_scope()),
        request_id="safe-diagnostic",
        method="GET",
        path="/probe",
        duration_ms=15,
        status_code=500,
        exception_type="RuntimeError",
        status_source="asgi_response_start",
        **diagnostics,
    )
    event = json.loads(log_path.read_text(encoding="utf-8"))
    assert event["pid"] == os.getpid()
    assert event["diagnostic_code"] == "tenant_context_missing"
    assert event["exception_origin"]
    assert "secret-data" not in str(event)
