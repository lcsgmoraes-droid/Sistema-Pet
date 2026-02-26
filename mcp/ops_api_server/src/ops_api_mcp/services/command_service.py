from __future__ import annotations

import subprocess
import time
from typing import Literal

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.models import CommandResult


FluxAction = Literal["check", "dev-up", "release-check", "prod-up", "status"]


class CommandService:
    _allowed_actions: set[str] = {"check", "dev-up", "release-check", "prod-up", "status"}

    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def run_fluxo(self, action: FluxAction, timeout_seconds: int | None = None) -> CommandResult:
        if action not in self._allowed_actions:
            raise ValueError(f"Ação não permitida: {action}")

        if not self.config.fluxo_script.exists():
            raise FileNotFoundError(f"Script não encontrado: {self.config.fluxo_script}")

        timeout = timeout_seconds or self.config.default_timeout_seconds
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.config.fluxo_script),
            action,
        ]

        start = time.perf_counter()
        process = subprocess.run(
            cmd,
            cwd=self.config.project_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        stdout = self._truncate(process.stdout)
        stderr = self._truncate(process.stderr)

        return CommandResult(
            ok=process.returncode == 0,
            action=action,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=elapsed_ms,
        )

    def _truncate(self, text: str) -> str:
        if text is None:
            return ""
        limit = self.config.max_output_chars
        if len(text) <= limit:
            return text
        return f"{text[:limit]}\n... [saida truncada]"
