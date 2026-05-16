from __future__ import annotations

import subprocess
import time
from typing import Literal

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.models import CommandResult
from ops_api_mcp.security import clamp_int, redact_text


FluxAction = Literal["check", "dev-up", "release-check", "prod-up", "status"]


class CommandService:
    _allowed_actions: set[str] = {"check", "dev-up", "release-check", "prod-up", "status"}

    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def run_fluxo(
        self,
        action: FluxAction,
        timeout_seconds: int | None = None,
        confirmacao: str | None = None,
    ) -> CommandResult:
        if action not in self._allowed_actions:
            raise ValueError(f"Acao nao permitida: {action}")

        if action == "prod-up":
            blocked = self._validate_prod_action(confirmacao)
            if blocked is not None:
                return blocked

        if not self.config.fluxo_script.exists():
            raise FileNotFoundError(f"Script nao encontrado: {self.config.fluxo_script}")

        timeout = clamp_int(
            timeout_seconds or self.config.default_timeout_seconds,
            minimum=1,
            maximum=self.config.max_timeout_seconds,
        )
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
        try:
            process = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return CommandResult(
                ok=process.returncode == 0,
                action=action,
                exit_code=process.returncode,
                stdout=self._truncate(process.stdout),
                stderr=self._truncate(process.stderr),
                duration_ms=elapsed_ms,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return CommandResult(
                ok=False,
                action=action,
                exit_code=124,
                stdout=self._truncate(exc.stdout or ""),
                stderr=self._truncate((exc.stderr or "") + "\n[timeout]"),
                duration_ms=elapsed_ms,
            )

    def _validate_prod_action(self, confirmacao: str | None) -> CommandResult | None:
        if not self.config.allow_prod_actions:
            return CommandResult(
                ok=False,
                action="prod-up",
                exit_code=126,
                stdout="",
                stderr=(
                    "Acao bloqueada: prod-up exige SISTEMA_PET_MCP_ALLOW_PROD_ACTIONS=true "
                    "e confirmacao explicita."
                ),
                duration_ms=0,
            )

        if confirmacao != self.config.prod_confirmation_phrase:
            return CommandResult(
                ok=False,
                action="prod-up",
                exit_code=126,
                stdout="",
                stderr=f"Confirmacao invalida. Use exatamente: {self.config.prod_confirmation_phrase}",
                duration_ms=0,
            )

        return None

    def _truncate(self, text: str | bytes | None) -> str:
        if text is None:
            return ""
        if isinstance(text, bytes):
            text = text.decode(errors="replace")
        text = redact_text(text)
        limit = self.config.max_output_chars
        if len(text) <= limit:
            return text
        return f"{text[:limit]}\n... [saida truncada]"
