from datetime import datetime, timedelta, timezone
import json

from starlette.requests import Request

from app.services import journey_event_reporter


NOW = datetime(2026, 8, 26, 18, 0, tzinfo=timezone.utc)


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def test_matches_only_the_initial_sanitized_journey_routes():
    assert journey_event_reporter.match_http_journey(
        "POST", "/api/auth/login-multitenant"
    ) == {
        "journey": "auth.login",
        "path_template": "/auth/login-multitenant",
    }
    assert journey_event_reporter.match_http_journey(
        "POST", "/vendas/9182/finalizar"
    ) == {
        "journey": "sale.finalization",
        "path_template": "/vendas/{venda_id}/finalizar",
    }
    assert journey_event_reporter.match_http_journey(
        "POST", "/app/funcionario/pdv/vendas/finalizar"
    ) == {
        "journey": "sale.finalization",
        "path_template": "/app/funcionario/pdv/vendas/finalizar",
    }
    assert (
        journey_event_reporter.match_http_journey("GET", "/vendas/1/finalizar") is None
    )
    assert journey_event_reporter.match_http_journey("POST", "/clientes") is None


def test_records_only_allowlisted_fields_without_request_payload(tmp_path, monkeypatch):
    path = tmp_path / "journey_events.jsonl"
    monkeypatch.setattr(journey_event_reporter, "JOURNEY_EVENT_LOG_PATH", str(path))

    event = journey_event_reporter.record_journey_event(
        journey="sale.finalization",
        outcome="success",
        reason_code="completed",
        duration_ms=321.45,
        method="POST",
        path_template="/vendas/{venda_id}/finalizar",
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        request_id="req-sale-1",
        operation_id="req-sale-1",
        status_code=200,
        now=NOW,
    )

    assert event is not None
    assert set(event) == {
        "event_key",
        "created_at",
        "journey",
        "outcome",
        "reason_code",
        "duration_ms",
        "status_code",
        "tenant_id",
        "request_id",
        "operation_id",
        "method",
        "path_template",
        "provider",
        "source",
    }
    assert event["path_template"] == "/vendas/{venda_id}/finalizar"
    assert "9182" not in json.dumps(event)
    for forbidden in (
        "email",
        "password",
        "cliente",
        "documento",
        "valor",
        "body",
        "payload",
        "user_agent",
        "ip_address",
    ):
        assert forbidden not in event

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted == event


def test_http_outcomes_keep_expected_rejections_out_of_failures():
    assert journey_event_reporter.classify_http_outcome(200) == (
        "success",
        "completed",
    )
    assert journey_event_reporter.classify_http_outcome(200, replayed=True) == (
        "success",
        "idempotent_replay",
    )
    assert journey_event_reporter.classify_http_outcome(401) == (
        "expected_rejection",
        "http_401",
    )
    assert journey_event_reporter.classify_http_outcome(500) == (
        "failure",
        "http_500",
    )
    assert journey_event_reporter.classify_http_outcome(None, exception=True) == (
        "failure",
        "unhandled_exception",
    )


def test_http_recorder_ignores_unmapped_routes_and_does_not_store_body(
    tmp_path, monkeypatch
):
    path = tmp_path / "journey_events.jsonl"
    monkeypatch.setattr(journey_event_reporter, "JOURNEY_EVENT_LOG_PATH", str(path))

    assert (
        journey_event_reporter.record_http_journey_event(
            request=_request("/clientes"),
            request_id="req-ignore",
            method="POST",
            path="/clientes",
            duration_ms=5,
            status_code=200,
        )
        is None
    )
    event = journey_event_reporter.record_http_journey_event(
        request=_request("/auth/login-multitenant"),
        request_id="req-login",
        method="POST",
        path="/auth/login-multitenant",
        duration_ms=80,
        status_code=401,
    )

    assert event is not None
    assert event["journey"] == "auth.login"
    assert event["outcome"] == "expected_rejection"
    assert event["tenant_id"] is None
    assert path.read_text(encoding="utf-8").count("\n") == 1


def test_summary_exposes_denominator_percentiles_and_low_sample_state():
    events = [
        {
            "journey": "sale.finalization",
            "outcome": "success",
            "duration_ms": index,
            "tenant_id": "tenant-a",
        }
        for index in range(1, 100)
    ]
    events.append(
        {
            "journey": "sale.finalization",
            "outcome": "failure",
            "duration_ms": 5000,
            "tenant_id": "tenant-a",
        }
    )
    events.append(
        {
            "journey": "sale.finalization",
            "outcome": "expected_rejection",
            "duration_ms": 10,
            "tenant_id": "tenant-a",
        }
    )

    summary = journey_event_reporter.summarize_journey_events(
        events=events,
        since=NOW - timedelta(days=30),
        until=NOW,
    )
    sale = summary["by_journey"][0]

    assert sale["total_attempts"] == 101
    assert sale["eligible_attempts"] == 100
    assert sale["successes"] == 99
    assert sale["expected_rejections"] == 1
    assert sale["failures"] == 1
    assert sale["success_rate_percent"] == 99.0
    assert sale["latency_ms"]["p95"] == 95
    assert sale["sample_status"] == "measured"
    assert sale["objective_status"] == "breached"
    assert summary["source"]["contains_personal_payload"] is False


def test_recording_failure_never_raises_or_breaks_the_journey(tmp_path, monkeypatch):
    directory = tmp_path / "directory"
    directory.mkdir()
    monkeypatch.setattr(
        journey_event_reporter,
        "JOURNEY_EVENT_LOG_PATH",
        str(directory),
    )

    assert (
        journey_event_reporter.record_journey_event(
            journey="auth.login",
            outcome="success",
            reason_code="completed",
            duration_ms=10,
            method="POST",
            path_template="/auth/login-multitenant",
        )
        is None
    )
