from datetime import datetime, timedelta, timezone

from app.services.ops_dashboard_health import _current_health_status
from app.services.ops_dashboard_incidents import (
    _build_route_incidents,
    _build_tenant_incidents,
)
from app.services.ops_dashboard_period_alerts import _build_alerts


def test_recent_unclassified_exception_prevents_false_healthy_status():
    now = datetime.now(timezone.utc)
    result = _current_health_status(
        watchdog={"status": "healthy", "database": "connected", "latency_ms": 1},
        error_summary={"errors_5xx": 0, "unknown_status_failures": 28},
        since=now - timedelta(minutes=5),
        until=now,
    )

    assert result["status"] == "degraded"
    assert result["unknown_status_failures"] == 28
    assert result["errors_5xx"] == 0
    assert "sem status HTTP confirmado" in result["detail"]


def test_old_unknown_events_raise_period_warning_without_claiming_5xx():
    alerts = _build_alerts(
        db=None,
        watchdog={"status": "healthy"},
        error_summary={"errors_5xx": 0, "unknown_status_failures": 741},
        deploy_events=[],
        watchdog_summary={},
        tenant_incidents=[],
        route_incidents=[],
    )

    assert len(alerts) == 1
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["source"] == "unknown_status_failures"
    assert "741" in alerts[0]["title"]


def test_partial_response_with_200_is_not_reported_as_healthy():
    now = datetime.now(timezone.utc)
    summary = {"errors_5xx": 0, "response_failures": 1}
    result = _current_health_status(
        watchdog={"status": "healthy"},
        error_summary=summary,
        since=now - timedelta(minutes=5),
        until=now,
    )
    alerts = _build_alerts(
        db=None,
        watchdog={"status": "healthy"},
        error_summary=summary,
        deploy_events=[],
        watchdog_summary={},
        tenant_incidents=[],
        route_incidents=[],
    )
    assert result["status"] == "degraded"
    assert result["errors_5xx"] == 0
    assert result["response_failures"] == 1
    assert alerts[0]["source"] == "response_failures"


def test_unknown_failures_remain_visible_in_tenant_and_route_rankings(monkeypatch):
    monkeypatch.setattr(
        "app.services.ops_dashboard_incidents._tenant_names",
        lambda _db, _ids: {"tenant-james": "Loja teste"},
    )
    events = [
        {
            "tenant_id": "tenant-james",
            "path": "/caixas/aberto",
            "status_code": None,
            "exception_type": "RuntimeError",
            "duration_ms": 20,
            "created_at": "2026-10-13T14:33:00Z",
        },
        {
            "tenant_id": "tenant-james",
            "path": "/caixas/aberto",
            "status_code": None,
            "exception_type": "RuntimeError",
            "diagnostic_code": "client_disconnected",
            "duration_ms": 25,
            "created_at": "2026-10-13T14:34:00Z",
        },
        {
            "tenant_id": "tenant-james",
            "path": "/produtos/",
            "status_code": 500,
            "exception_type": "RuntimeError",
            "duration_ms": 30,
            "created_at": "2026-10-13T14:35:00Z",
        },
        {
            "tenant_id": "tenant-james",
            "path": "/stream",
            "status_code": 200,
            "exception_type": "RuntimeError",
            "diagnostic_code": "response_stream_failure",
            "response_incomplete": True,
            "duration_ms": 20,
            "created_at": "2026-10-13T14:36:00Z",
        },
    ]

    tenant = _build_tenant_incidents(None, events)[0]
    routes = {item["path"]: item for item in _build_route_incidents(events)}

    assert tenant["errors_5xx"] == 1
    assert tenant["unknown_status_failures"] == 1
    assert tenant["response_failures"] == 1
    assert routes["/caixas/aberto"]["severity"] == "warning"
    assert routes["/caixas/aberto"]["unknown_status_failures"] == 1
    assert routes["/caixas/aberto"]["errors_5xx"] == 0
    assert routes["/produtos/"]["errors_5xx"] == 1
    assert routes["/produtos/"]["unknown_status_failures"] == 0
    assert routes["/stream"]["severity"] == "warning"
    assert routes["/stream"]["response_failures"] == 1
