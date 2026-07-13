from datetime import datetime, timezone
import json

from app.services import ops_tls_status_service


NOW = datetime(2026, 7, 13, 20, 0, tzinfo=timezone.utc)


def _write_status(tmp_path, monkeypatch, payload):
    status_path = tmp_path / "tls_status.json"
    status_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(ops_tls_status_service, "TLS_STATUS_PATH", str(status_path))


def test_tls_status_returns_safe_certificate_summary(tmp_path, monkeypatch):
    _write_status(
        tmp_path,
        monkeypatch,
        {
            "generated_at": "2026-07-13T19:30:00Z",
            "status": "healthy",
            "warning_days": 30,
            "critical_days": 7,
            "certificates": [
                {
                    "domain": "corepet.com.br",
                    "status": "healthy",
                    "expires_at": "2026-09-01T00:00:00Z",
                    "days_remaining": 49,
                }
            ],
            "private_key": "must-not-leak",
        },
    )

    summary = ops_tls_status_service.summarize_tls_status(now=NOW)

    assert summary["status"] == "healthy"
    assert summary["age_hours"] == 0.5
    assert summary["certificates"][0]["days_remaining"] == 49
    assert "private_key" not in str(summary)


def test_tls_status_marks_old_snapshot_as_stale(tmp_path, monkeypatch):
    _write_status(
        tmp_path,
        monkeypatch,
        {
            "generated_at": "2026-07-13T17:00:00Z",
            "status": "healthy",
            "certificates": [],
        },
    )
    monkeypatch.setattr(ops_tls_status_service, "TLS_STATUS_MAX_AGE_HOURS", 2)

    summary = ops_tls_status_service.summarize_tls_status(now=NOW)

    assert summary["status"] == "stale"
    assert summary["age_hours"] == 3


def test_tls_status_reports_missing_file_without_exposing_path(tmp_path, monkeypatch):
    missing_path = tmp_path / "missing.json"
    monkeypatch.setattr(ops_tls_status_service, "TLS_STATUS_PATH", str(missing_path))

    summary = ops_tls_status_service.summarize_tls_status(now=NOW)

    assert summary == {
        "status": "unavailable",
        "certificates": [],
        "age_hours": None,
    }
    assert str(tmp_path) not in str(summary)


def test_tls_status_rejects_non_object_payload(tmp_path, monkeypatch):
    _write_status(tmp_path, monkeypatch, ["invalid"])

    summary = ops_tls_status_service.summarize_tls_status(now=NOW)

    assert summary["status"] == "unavailable"
