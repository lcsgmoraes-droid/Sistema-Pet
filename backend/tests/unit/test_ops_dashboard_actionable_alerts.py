from app.services.ops_dashboard_service import _build_actionable_alerts
from app.services.ops_dashboard_period_alerts import _build_alerts


class _FakeDb:
    def query(self, *args, **kwargs):
        raise AssertionError("Tenant lookup should not run for system-only alerts")


def test_build_actionable_alerts_flags_recurrent_watchdog_failures():
    alerts = _build_actionable_alerts(
        _FakeDb(),
        events=[],
        watchdog={"status": "healthy"},
        watchdog_summary={
            "recoveries": 0,
            "by_status": [("warning", 2), ("cooldown", 1)],
            "latest": [
                {
                    "status": "cooldown",
                    "message": "Falha persiste, mas restart em cooldown: worker_unhealthy",
                    "worker_health": "unhealthy",
                    "created_at": "2026-05-16T21:40:00Z",
                }
            ],
        },
        deploy_events=[],
    )

    recurrent = next(
        alert for alert in alerts if alert["id"] == "system:watchdog:recurrent_failures"
    )
    worker = next(
        alert for alert in alerts if alert["id"] == "system:job:worker_bling_unhealthy"
    )

    assert recurrent["severity"] == "warning"
    assert recurrent["kind"] == "watchdog_recurrent_failure"
    assert recurrent["total"] == 3
    assert recurrent["latest_at"] == "2026-05-16T21:40:00Z"
    assert "cooldown" in recurrent["detail"]
    assert worker["severity"] == "critical"
    assert worker["kind"] == "worker_bling_unhealthy"
    assert worker["latest_at"] == "2026-05-16T21:40:00Z"


def test_build_actionable_alerts_flags_recurrent_5xx_and_slow_routes():
    events = [
        {
            "request_id": "req-500-a",
            "tenant_id": None,
            "path": "/api/vendas",
            "status_code": 500,
            "duration_ms": 120,
            "created_at": "2026-05-16T21:41:00Z",
        },
        {
            "request_id": "req-500-b",
            "tenant_id": None,
            "path": "/api/vendas",
            "status_code": 502,
            "duration_ms": 130,
            "created_at": "2026-05-16T21:42:00Z",
        },
        {
            "request_id": "req-slow-a",
            "tenant_id": None,
            "path": "/api/relatorios",
            "status_code": 200,
            "duration_ms": 3500,
            "created_at": "2026-05-16T21:43:00Z",
        },
        {
            "request_id": "req-slow-b",
            "tenant_id": None,
            "path": "/api/relatorios",
            "status_code": 200,
            "duration_ms": 3600,
            "created_at": "2026-05-16T21:44:00Z",
        },
        {
            "request_id": "req-slow-c",
            "tenant_id": None,
            "path": "/api/relatorios",
            "status_code": 200,
            "duration_ms": 3700,
            "created_at": "2026-05-16T21:45:00Z",
        },
        {
            "request_id": "req-slow-d",
            "tenant_id": None,
            "path": "/api/relatorios",
            "status_code": 200,
            "duration_ms": 3800,
            "created_at": "2026-05-16T21:46:00Z",
        },
    ]

    alerts = _build_actionable_alerts(
        _FakeDb(),
        events=events,
        watchdog={"status": "healthy"},
        watchdog_summary={"recoveries": 0, "by_status": [], "latest": []},
        deploy_events=[],
    )

    route_5xx = next(
        alert
        for alert in alerts
        if alert["id"] == "route:/api/vendas:route_5xx_recurrent"
    )
    route_slow = next(
        alert
        for alert in alerts
        if alert["id"] == "route:/api/relatorios:route_slow_recurrent"
    )
    tenant_5xx = next(
        alert
        for alert in alerts
        if alert["id"] == "tenant:sem_tenant:tenant_5xx_recurrent"
    )

    assert route_5xx["severity"] == "critical"
    assert route_5xx["errors_5xx"] == 2
    assert route_5xx["request_id"] == "req-500-b"
    assert route_slow["severity"] == "warning"
    assert route_slow["slow_requests"] == 4
    assert route_slow["request_id"] == "req-slow-d"
    assert tenant_5xx["tenant_filter"] == "sem_tenant"


def test_period_alerts_flag_missing_backup_evidence():
    alerts = _build_alerts(
        db=_FakeDb(),
        watchdog={"status": "healthy"},
        error_summary={"errors_5xx": 0, "slow_requests": 0},
        deploy_events=[],
        watchdog_summary={"recoveries": 0},
        tenant_incidents=[],
        route_incidents=[],
        continuity={
            "status": "critical",
            "backup": {"status": "missing"},
            "external_copy": {"status": "missing"},
            "restore": {"status": "missing"},
        },
    )

    assert alerts == [
        {
            "severity": "critical",
            "tone": "red",
            "title": "Continuidade operacional exige atencao",
            "detail": "Backup: missing; copia externa: missing; restore: missing.",
            "action": "Validar a rotina de backup e executar restore controlado antes do proximo deploy.",
            "source": "continuity",
        }
    ]


def test_period_alerts_flag_tls_expiry_warning():
    alerts = _build_alerts(
        db=_FakeDb(),
        watchdog={"status": "healthy"},
        error_summary={"errors_5xx": 0, "slow_requests": 0},
        deploy_events=[],
        watchdog_summary={"recoveries": 0},
        tenant_incidents=[],
        route_incidents=[],
        tls={
            "status": "warning",
            "certificates": [
                {"domain": "corepet.com.br", "status": "warning"},
                {"domain": "img.corepet.com.br", "status": "healthy"},
            ],
        },
    )

    assert alerts[0] == {
        "severity": "warning",
        "tone": "amber",
        "title": "Validade TLS exige atencao",
        "detail": "Status: warning; dominios: corepet.com.br.",
        "action": "Validar renovacao e cadeia do certificado antes do vencimento.",
        "source": "tls",
    }


def test_actionable_alerts_notify_tls_expiry_warning():
    alerts = _build_actionable_alerts(
        _FakeDb(),
        [],
        {"status": "healthy"},
        {"recoveries": 0},
        [],
        tls={
            "status": "warning",
            "certificates": [
                {"domain": "corepet.com.br", "status": "warning"},
            ],
        },
    )

    assert alerts[0]["id"] == "system:tls:certificate_status"
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["score"] == 780
