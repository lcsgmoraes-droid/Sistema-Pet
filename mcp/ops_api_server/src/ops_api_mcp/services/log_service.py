from __future__ import annotations

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.security import clamp_int, redact_text
from ops_api_mcp.services.docker_service import DockerService


class LogService:
    def __init__(self, config: ServerConfig, docker_service: DockerService) -> None:
        self.config = config
        self.docker_service = docker_service

    def backend_logs(self, lines: int = 50, filter_text: str = "") -> dict:
        bounded_lines = clamp_int(lines, minimum=1, maximum=500)
        safe_filter = (filter_text or "").strip()

        if len(safe_filter) > 120:
            return {"ok": False, "stderr": "filter_text deve ter no maximo 120 caracteres"}

        read_lines = bounded_lines * 5 if safe_filter else bounded_lines
        result = self.docker_service.logs(self.config.dev_backend_container, lines=read_lines)
        if not result.get("ok"):
            return result

        output = result.get("stdout", "")
        if safe_filter:
            filtered = [
                line
                for line in output.splitlines()
                if safe_filter.lower() in line.lower()
            ][-bounded_lines:]
            return {
                "ok": True,
                "stdout": redact_text("\n".join(filtered)),
                "total_matched": len(filtered),
            }

        return {
            "ok": True,
            "stdout": redact_text(output.strip()[-8000:]),
        }
