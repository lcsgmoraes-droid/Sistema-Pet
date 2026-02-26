from __future__ import annotations

import shutil
import subprocess
import time
from typing import Literal

from frontend_react_mcp.config import ServerConfig
from frontend_react_mcp.models import FrontCheckResult, FrontCommandResult


FrontScript = Literal["dev", "build", "build:dev", "preview"]


class FrontendService:
    _allowed_scripts: set[str] = {"dev", "build", "build:dev", "preview"}

    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def run_script(
        self,
        script: FrontScript,
        timeout_seconds: int | None = None,
        extra_args: list[str] | None = None,
    ) -> FrontCommandResult:
        if script not in self._allowed_scripts:
            raise ValueError(f"Script não permitido: {script}")

        if not self.config.frontend_root.exists():
            raise FileNotFoundError(f"Diretório frontend não encontrado: {self.config.frontend_root}")

        npm_executable = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm_executable:
            raise FileNotFoundError("npm não encontrado no PATH")

        timeout = timeout_seconds or self.config.default_timeout_seconds
        cmd = [npm_executable, "run", script]
        if extra_args:
            cmd.extend(["--", *extra_args])

        start = time.perf_counter()
        try:
            process = subprocess.run(
                cmd,
                cwd=self.config.frontend_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return FrontCommandResult(
                ok=process.returncode == 0,
                action=f"npm_run_{script}",
                exit_code=process.returncode,
                stdout=self._truncate(process.stdout),
                stderr=self._truncate(process.stderr),
                duration_ms=elapsed_ms,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            timed_stdout = (exc.stdout or "")
            timed_stderr = (exc.stderr or "")
            started = "ready in" in timed_stdout.lower() or "local:" in timed_stdout.lower()
            return FrontCommandResult(
                ok=started,
                action=f"npm_run_{script}",
                exit_code=124,
                stdout=self._truncate(timed_stdout),
                stderr=self._truncate(timed_stderr + "\n[timeout]"),
                duration_ms=elapsed_ms,
            )

    def status(self) -> FrontCheckResult:
        npm_path = shutil.which("npm")
        node_path = shutil.which("node")
        package_json = self.config.frontend_root / "package.json"

        details = {
            "frontend_root": str(self.config.frontend_root),
            "frontend_exists": self.config.frontend_root.exists(),
            "package_json_exists": package_json.exists(),
            "npm_found": npm_path is not None,
            "node_found": node_path is not None,
            "npm_path": npm_path,
            "node_path": node_path,
        }

        ok = all(
            [
                details["frontend_exists"],
                details["package_json_exists"],
                details["npm_found"],
                details["node_found"],
            ]
        )
        return FrontCheckResult(ok=ok, check="front_status", details=details)

    def _truncate(self, text: str) -> str:
        if text is None:
            return ""
        limit = self.config.max_output_chars
        if len(text) <= limit:
            return text
        return f"{text[:limit]}\n... [saida truncada]"
