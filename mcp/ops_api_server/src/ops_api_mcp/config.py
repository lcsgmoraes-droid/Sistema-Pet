from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "sim", "s"}


def _env_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    return values or default


@dataclass(frozen=True)
class ServerConfig:
    project_root: Path
    fluxo_script: Path
    default_timeout_seconds: int = 600
    max_timeout_seconds: int = 1800
    max_output_chars: int = 12000
    default_health_url: str = "http://localhost:8000/health"
    default_auth_url: str = "http://localhost:8000/auth/login-multitenant"
    allowed_http_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "::1")
    allow_prod_actions: bool = False
    prod_confirmation_phrase: str = "AUTORIZO PROD-UP LOCAL"
    dev_postgres_container: str = "petshop-dev-postgres"
    dev_backend_container: str = "petshop-dev-backend"
    dev_db_user: str = "postgres"
    dev_db_name: str = "petshop_dev"
    audit_log_path: Path | None = None

    @staticmethod
    def load() -> "ServerConfig":
        current = Path(__file__).resolve()
        project_root = current.parents[4]
        fluxo_script = project_root / "scripts" / "fluxo_unico.ps1"
        return ServerConfig(
            project_root=project_root,
            fluxo_script=fluxo_script,
            default_timeout_seconds=int(os.getenv("SISTEMA_PET_MCP_TIMEOUT_SECONDS", "600")),
            max_timeout_seconds=int(os.getenv("SISTEMA_PET_MCP_MAX_TIMEOUT_SECONDS", "1800")),
            max_output_chars=int(os.getenv("SISTEMA_PET_MCP_MAX_OUTPUT_CHARS", "12000")),
            default_health_url=os.getenv("SISTEMA_PET_MCP_HEALTH_URL", "http://localhost:8000/health"),
            default_auth_url=os.getenv(
                "SISTEMA_PET_MCP_AUTH_URL",
                "http://localhost:8000/auth/login-multitenant",
            ),
            allowed_http_hosts=_env_tuple(
                "SISTEMA_PET_MCP_ALLOWED_HTTP_HOSTS",
                ("localhost", "127.0.0.1", "::1"),
            ),
            allow_prod_actions=_env_bool("SISTEMA_PET_MCP_ALLOW_PROD_ACTIONS", False),
            prod_confirmation_phrase=os.getenv(
                "SISTEMA_PET_MCP_PROD_CONFIRMATION",
                "AUTORIZO PROD-UP LOCAL",
            ),
            dev_postgres_container=os.getenv("SISTEMA_PET_MCP_DEV_POSTGRES_CONTAINER", "petshop-dev-postgres"),
            dev_backend_container=os.getenv("SISTEMA_PET_MCP_DEV_BACKEND_CONTAINER", "petshop-dev-backend"),
            dev_db_user=os.getenv("SISTEMA_PET_MCP_DEV_DB_USER", "postgres"),
            dev_db_name=os.getenv("SISTEMA_PET_MCP_DEV_DB_NAME", "petshop_dev"),
            audit_log_path=Path(
                os.getenv(
                    "SISTEMA_PET_MCP_AUDIT_LOG",
                    str(Path(tempfile.gettempdir()) / "sistema_pet_mcp_ops_audit.jsonl"),
                )
            ),
        )
