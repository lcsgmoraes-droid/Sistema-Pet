from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.services.api_service import ApiService
from ops_api_mcp.services.command_service import CommandService


config = ServerConfig.load()
command_service = CommandService(config)
api_service = ApiService()

mcp = FastMCP(
    "sistema-pet-ops-api",
    instructions=(
        "Ferramentas para operar o fluxo unico DEV->PROD e validar API/auth/permissoes "
        "do Sistema Pet com seguranca operacional."
    ),
)


@mcp.tool()
def fluxo_check(timeout_seconds: int = 600) -> dict:
    result = command_service.run_fluxo("check", timeout_seconds=timeout_seconds)
    return result.to_dict()


@mcp.tool()
def fluxo_dev_up(timeout_seconds: int = 900) -> dict:
    result = command_service.run_fluxo("dev-up", timeout_seconds=timeout_seconds)
    return result.to_dict()


@mcp.tool()
def fluxo_release_check(timeout_seconds: int = 600) -> dict:
    result = command_service.run_fluxo("release-check", timeout_seconds=timeout_seconds)
    return result.to_dict()


@mcp.tool()
def fluxo_prod_up(timeout_seconds: int = 900) -> dict:
    result = command_service.run_fluxo("prod-up", timeout_seconds=timeout_seconds)
    return result.to_dict()


@mcp.tool()
def fluxo_status(timeout_seconds: int = 300) -> dict:
    result = command_service.run_fluxo("status", timeout_seconds=timeout_seconds)
    return result.to_dict()


@mcp.tool()
def api_health_check(url: str = "https://localhost/health") -> dict:
    result = api_service.health_check(url)
    return result.to_dict()


@mcp.tool()
def api_auth_route_smoke(url: str = "https://localhost/api/auth/login-multitenant") -> dict:
    result = api_service.auth_route_smoke(url)
    return result.to_dict()


@mcp.tool()
def auth_validate_tabs_permissions(
    base_url: str,
    email: str,
    password: str,
    required_permissions: list[str] | None = None,
) -> dict:
    result = api_service.validate_tabs_permissions(
        base_url=base_url,
        email=email,
        password=password,
        required_permissions=required_permissions,
    )
    return result.to_dict()
