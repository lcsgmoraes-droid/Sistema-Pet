from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile


def _env_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    return values or default


@dataclass(frozen=True)
class ServerConfig:
    project_root: Path
    frontend_root: Path
    default_timeout_seconds: int = 600
    max_timeout_seconds: int = 1800
    max_output_chars: int = 12000
    default_front_url: str = "http://localhost:5173"
    default_auth_url: str = "http://localhost:8000/auth/login-multitenant"
    allowed_http_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "::1")
    allowed_dev_hosts: tuple[str, ...] = ("localhost", "127.0.0.1")
    audit_log_path: Path | None = None

    @staticmethod
    def load() -> "ServerConfig":
        current = Path(__file__).resolve()
        project_root = current.parents[4]
        frontend_root = project_root / "frontend"
        return ServerConfig(
            project_root=project_root,
            frontend_root=frontend_root,
            default_timeout_seconds=int(os.getenv("SISTEMA_PET_FRONT_MCP_TIMEOUT_SECONDS", "600")),
            max_timeout_seconds=int(os.getenv("SISTEMA_PET_FRONT_MCP_MAX_TIMEOUT_SECONDS", "1800")),
            max_output_chars=int(os.getenv("SISTEMA_PET_FRONT_MCP_MAX_OUTPUT_CHARS", "12000")),
            default_front_url=os.getenv("SISTEMA_PET_FRONT_MCP_FRONT_URL", "http://localhost:5173"),
            default_auth_url=os.getenv(
                "SISTEMA_PET_FRONT_MCP_AUTH_URL",
                "http://localhost:8000/auth/login-multitenant",
            ),
            allowed_http_hosts=_env_tuple(
                "SISTEMA_PET_FRONT_MCP_ALLOWED_HTTP_HOSTS",
                ("localhost", "127.0.0.1", "::1"),
            ),
            allowed_dev_hosts=_env_tuple(
                "SISTEMA_PET_FRONT_MCP_ALLOWED_DEV_HOSTS",
                ("localhost", "127.0.0.1"),
            ),
            audit_log_path=Path(
                os.getenv(
                    "SISTEMA_PET_FRONT_MCP_AUDIT_LOG",
                    str(Path(tempfile.gettempdir()) / "sistema_pet_mcp_frontend_audit.jsonl"),
                )
            ),
        )
