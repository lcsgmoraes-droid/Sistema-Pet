from datetime import datetime, timezone
import json

from app.services import ops_continuity_service


NOW = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)


def _write_events(tmp_path, monkeypatch, events):
    event_path = tmp_path / "continuity_events.jsonl"
    event_path.write_text(
        "\n".join(json.dumps(event) for event in events), encoding="utf-8"
    )
    monkeypatch.setattr(
        ops_continuity_service, "CONTINUITY_EVENT_LOG_PATH", str(event_path)
    )


def test_continuity_is_healthy_with_recent_backup_and_restore(tmp_path, monkeypatch):
    _write_events(
        tmp_path,
        monkeypatch,
        [
            {
                "created_at": "2026-07-13T06:00:00Z",
                "operation": "backup",
                "status": "ok",
                "backup_file": "petshop.dump.gz",
                "backup_bytes": "1024",
                "backup_sha256": "a" * 64,
            },
            {
                "created_at": "2026-07-12T06:00:00Z",
                "operation": "restore",
                "status": "ok",
                "public_tables": "217",
                "alembic_rows": "1",
            },
            {
                "created_at": "2026-07-13T06:05:00Z",
                "operation": "external_copy",
                "status": "ok",
                "backup_file": "petshop.dump.gz",
            },
        ],
    )

    summary = ops_continuity_service.summarize_continuity(now=NOW)

    assert summary["status"] == "healthy"
    assert summary["backup"]["age_hours"] == 6
    assert summary["backup"]["backup_bytes"] == 1024
    assert summary["restore"]["public_tables"] == 217
    assert summary["objectives"]["rpo_met"] is True
    assert summary["objectives"]["rto_test_evidence"] is True
    assert summary["objectives"]["external_copy_verified"] is True


def test_latest_failed_backup_is_critical_even_with_previous_success(
    tmp_path, monkeypatch
):
    _write_events(
        tmp_path,
        monkeypatch,
        [
            {
                "created_at": "2026-07-13T06:00:00Z",
                "operation": "backup",
                "status": "ok",
            },
            {
                "created_at": "2026-07-13T11:00:00Z",
                "operation": "backup",
                "status": "failed",
            },
        ],
    )

    summary = ops_continuity_service.summarize_continuity(now=NOW)

    assert summary["status"] == "critical"
    assert summary["backup"]["status"] == "failed"
    assert summary["backup"]["last_success_at"] == "2026-07-13T06:00:00Z"


def test_missing_evidence_is_reported_without_exposing_source_path(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        ops_continuity_service,
        "CONTINUITY_EVENT_LOG_PATH",
        str(tmp_path / "missing.jsonl"),
    )

    summary = ops_continuity_service.summarize_continuity(now=NOW)

    assert summary["status"] == "critical"
    assert summary["backup"]["status"] == "missing"
    assert summary["restore"]["status"] == "missing"
    assert summary["external_copy"]["status"] == "missing"
    assert str(tmp_path) not in str(summary)
