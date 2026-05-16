from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

from ops_api_mcp.security import clamp_int, redact_value


class AuditReportService:
    def __init__(self, sources: Mapping[str, Path]) -> None:
        self.sources = dict(sources)

    def build(self, limit: int = 50) -> dict[str, Any]:
        bounded_limit = clamp_int(limit, minimum=1, maximum=200)
        events: list[dict[str, Any]] = []
        totals_by_mcp: dict[str, int] = {}
        failures_by_tool: dict[str, int] = {}
        missing_logs: list[str] = []
        invalid_lines: list[dict[str, Any]] = []

        for mcp_name, path in self.sources.items():
            if not path.exists():
                missing_logs.append(mcp_name)
                totals_by_mcp[mcp_name] = 0
                continue

            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue

                try:
                    raw_event = json.loads(line)
                except json.JSONDecodeError:
                    invalid_lines.append({"mcp": mcp_name, "line": line_number})
                    continue

                event = self._normalize_event(mcp_name, raw_event)
                events.append(event)
                totals_by_mcp[mcp_name] = totals_by_mcp.get(mcp_name, 0) + 1
                if event["ok"] is False:
                    failures_by_tool[event["tool"]] = failures_by_tool.get(event["tool"], 0) + 1

            totals_by_mcp.setdefault(mcp_name, 0)

        events.sort(key=self._sort_key, reverse=True)

        return {
            "ok": True,
            "sources": {name: str(path) for name, path in self.sources.items()},
            "total_events": len(events),
            "totals_by_mcp": totals_by_mcp,
            "failures_by_tool": failures_by_tool,
            "missing_logs": missing_logs,
            "invalid_lines": invalid_lines,
            "recent_events": events[:bounded_limit],
        }

    def _normalize_event(self, mcp_name: str, event: dict[str, Any]) -> dict[str, Any]:
        return redact_value(
            {
                "mcp": mcp_name,
                "timestamp": event.get("timestamp"),
                "tool": event.get("tool") or "unknown",
                "ok": event.get("ok"),
                "action": event.get("action"),
                "operation": event.get("operation"),
                "check": event.get("check"),
                "exit_code": event.get("exit_code"),
                "status_code": event.get("status_code"),
                "duration_ms": event.get("duration_ms"),
            }
        )

    def _sort_key(self, event: dict[str, Any]) -> datetime:
        timestamp = event.get("timestamp")
        if not timestamp:
            return datetime.min

        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return datetime.min
