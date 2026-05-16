from __future__ import annotations

import json
from pathlib import Path

from ops_api_mcp.services.audit_report_service import AuditReportService


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries),
        encoding="utf-8",
    )


def test_audit_report_summarizes_multiple_mcp_logs(tmp_path: Path):
    frontend_log = tmp_path / "frontend.jsonl"
    ops_log = tmp_path / "ops.jsonl"
    _write_jsonl(
        frontend_log,
        [
            {"timestamp": "2026-05-16T10:00:00+00:00", "tool": "front_status", "ok": True},
            {"timestamp": "2026-05-16T10:01:00+00:00", "tool": "front_http_check", "ok": False},
        ],
    )
    _write_jsonl(
        ops_log,
        [
            {"timestamp": "2026-05-16T10:02:00+00:00", "tool": "fluxo_prod_up", "ok": False},
            {"timestamp": "2026-05-16T10:03:00+00:00", "tool": "api_health_check", "ok": True},
        ],
    )

    report = AuditReportService({"frontend": frontend_log, "ops": ops_log}).build(limit=3)

    assert report["ok"] is True
    assert report["total_events"] == 4
    assert report["totals_by_mcp"] == {"frontend": 2, "ops": 2}
    assert report["failures_by_tool"] == {"front_http_check": 1, "fluxo_prod_up": 1}
    assert [event["tool"] for event in report["recent_events"]] == [
        "api_health_check",
        "fluxo_prod_up",
        "front_http_check",
    ]


def test_audit_report_tracks_missing_and_invalid_lines(tmp_path: Path):
    audit_log = tmp_path / "ops.jsonl"
    audit_log.write_text(
        '{"timestamp":"2026-05-16T10:00:00+00:00","tool":"fluxo_check","ok":true}\n'
        'nao-json\n',
        encoding="utf-8",
    )

    report = AuditReportService({"frontend": tmp_path / "missing.jsonl", "ops": audit_log}).build()

    assert report["ok"] is True
    assert report["total_events"] == 1
    assert report["missing_logs"] == ["frontend"]
    assert report["invalid_lines"] == [{"mcp": "ops", "line": 2}]
