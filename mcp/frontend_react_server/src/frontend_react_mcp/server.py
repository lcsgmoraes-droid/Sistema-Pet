from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from frontend_react_mcp.config import ServerConfig
from frontend_react_mcp.services.audit_service import AuditService
from frontend_react_mcp.services.frontend_service import FrontendService
from frontend_react_mcp.services.http_service import HttpService


config = ServerConfig.load()
frontend_service = FrontendService(config)
http_service = HttpService(config)
audit_service = AuditService(config)

mcp = FastMCP(
    "sistema-pet-frontend-react",
    instructions=(
        "Ferramentas para validar e operar o frontend React/Vite do Sistema Pet com "
        "diagnostico de build, dev e conectividade com a API."
    ),
)


def _record(tool: str, result: dict) -> dict:
    return audit_service.record(tool, result)


@mcp.tool()
def front_status() -> dict:
    return _record("front_status", frontend_service.status().to_dict())


@mcp.tool()
def front_build_check(timeout_seconds: int = 900) -> dict:
    return _record("front_build_check", frontend_service.run_script("build", timeout_seconds=timeout_seconds).to_dict())


@mcp.tool()
def front_build_dev_check(timeout_seconds: int = 900) -> dict:
    return _record(
        "front_build_dev_check",
        frontend_service.run_script("build:dev", timeout_seconds=timeout_seconds).to_dict(),
    )


@mcp.tool()
def front_dev_smoke(timeout_seconds: int = 35, host: str = "127.0.0.1", port: int = 5173) -> dict:
    return _record(
        "front_dev_smoke",
        frontend_service.run_dev_smoke(
            timeout_seconds=timeout_seconds,
            host=host,
            port=port,
        ).to_dict(),
    )


@mcp.tool()
def front_http_check(url: str = config.default_front_url) -> dict:
    return _record("front_http_check", http_service.front_http_check(url).to_dict())


@mcp.tool()
def front_api_auth_smoke(url: str = config.default_auth_url) -> dict:
    return _record("front_api_auth_smoke", http_service.api_auth_smoke(url).to_dict())
