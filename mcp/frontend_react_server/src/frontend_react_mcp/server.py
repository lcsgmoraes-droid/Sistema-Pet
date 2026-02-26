from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from frontend_react_mcp.config import ServerConfig
from frontend_react_mcp.services.frontend_service import FrontendService
from frontend_react_mcp.services.http_service import HttpService


config = ServerConfig.load()
frontend_service = FrontendService(config)
http_service = HttpService()

mcp = FastMCP(
    "sistema-pet-frontend-react",
    instructions=(
        "Ferramentas para validar e operar o frontend React/Vite do Sistema Pet com "
        "diagnóstico de build, dev e conectividade com a API."
    ),
)


@mcp.tool()
def front_status() -> dict:
    return frontend_service.status().to_dict()


@mcp.tool()
def front_build_check(timeout_seconds: int = 900) -> dict:
    return frontend_service.run_script("build", timeout_seconds=timeout_seconds).to_dict()


@mcp.tool()
def front_build_dev_check(timeout_seconds: int = 900) -> dict:
    return frontend_service.run_script("build:dev", timeout_seconds=timeout_seconds).to_dict()


@mcp.tool()
def front_dev_smoke(timeout_seconds: int = 35, host: str = "127.0.0.1", port: int = 5173) -> dict:
    result = frontend_service.run_script(
        "dev",
        timeout_seconds=timeout_seconds,
        extra_args=["--host", host, "--port", str(port), "--strictPort"],
    )
    return result.to_dict()


@mcp.tool()
def front_http_check(url: str = "http://localhost:5173") -> dict:
    return http_service.front_http_check(url).to_dict()


@mcp.tool()
def front_api_auth_smoke(url: str = "https://localhost/api/auth/login-multitenant") -> dict:
    return http_service.api_auth_smoke(url).to_dict()
