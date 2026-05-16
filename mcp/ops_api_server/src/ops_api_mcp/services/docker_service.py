from __future__ import annotations

import subprocess

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.security import clamp_int, redact_text


class DockerService:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def exec(self, container: str, cmd: list[str], timeout_seconds: int = 20) -> dict:
        full_cmd = ["docker", "exec", container, *cmd]
        timeout = clamp_int(timeout_seconds, minimum=1, maximum=120)

        try:
            result = subprocess.run(
                full_cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
            return {
                "ok": result.returncode == 0,
                "stdout": self._tail(result.stdout, 6000),
                "stderr": self._tail(result.stderr, 2000),
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "Timeout", "exit_code": 124}
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": redact_text(str(exc)), "exit_code": -1}

    def logs(self, container: str, lines: int, timeout_seconds: int = 15) -> dict:
        bounded_lines = clamp_int(lines, minimum=1, maximum=2500)
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(bounded_lines), container],
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                shell=False,
            )
            return {
                "ok": result.returncode == 0,
                "stdout": self._tail((result.stdout or "") + (result.stderr or ""), 12000),
                "stderr": "",
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "Timeout", "exit_code": 124}
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": redact_text(str(exc)), "exit_code": -1}

    def _tail(self, text: str | None, limit: int) -> str:
        safe = redact_text(text)
        return safe.strip()[-limit:]
