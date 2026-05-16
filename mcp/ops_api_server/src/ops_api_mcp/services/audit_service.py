from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.security import redact_value


class AuditService:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def record(self, tool: str, result: dict[str, Any]) -> dict[str, Any]:
        if not self.config.audit_log_path:
            return result

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "ok": result.get("ok"),
            "action": result.get("action"),
            "operation": result.get("operation"),
            "check": result.get("check"),
            "exit_code": result.get("exit_code"),
            "status_code": result.get("status_code"),
            "duration_ms": result.get("duration_ms"),
        }

        try:
            self.config.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config.audit_log_path.open("a", encoding="utf-8") as audit_file:
                audit_file.write(json.dumps(redact_value(entry), ensure_ascii=False) + "\n")
        except OSError:
            result = dict(result)
            result.setdefault("audit_warning", "Falha ao gravar auditoria local do MCP")

        return result
