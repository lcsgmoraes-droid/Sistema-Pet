from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.services.api_service import ApiService
from ops_api_mcp.services.audit_report_service import AuditReportService
from ops_api_mcp.services.audit_service import AuditService
from ops_api_mcp.services.campaign_service import CampaignService
from ops_api_mcp.services.command_service import CommandService
from ops_api_mcp.services.docker_service import DockerService
from ops_api_mcp.services.log_service import LogService


config = ServerConfig.load()
command_service = CommandService(config)
api_service = ApiService(config)
docker_service = DockerService(config)
campaign_service = CampaignService(config, docker_service)
log_service = LogService(config, docker_service)
audit_service = AuditService(config)
audit_report_service = AuditReportService(
    {
        "frontend": config.frontend_audit_log_path,
        "ops": config.audit_log_path,
    }
)

mcp = FastMCP(
    "sistema-pet-ops-api",
    instructions=(
        "Ferramentas para operar o fluxo unico DEV->PROD e validar API/auth/permissoes "
        "do Sistema Pet com seguranca operacional."
    ),
)


def _record(tool: str, result: dict) -> dict:
    return audit_service.record(tool, result)


@mcp.tool()
def fluxo_check(timeout_seconds: int = 600) -> dict:
    result = command_service.run_fluxo("check", timeout_seconds=timeout_seconds)
    return _record("fluxo_check", result.to_dict())


@mcp.tool()
def fluxo_dev_up(timeout_seconds: int = 900) -> dict:
    result = command_service.run_fluxo("dev-up", timeout_seconds=timeout_seconds)
    return _record("fluxo_dev_up", result.to_dict())


@mcp.tool()
def fluxo_release_check(timeout_seconds: int = 600) -> dict:
    result = command_service.run_fluxo("release-check", timeout_seconds=timeout_seconds)
    return _record("fluxo_release_check", result.to_dict())


@mcp.tool()
def fluxo_prod_up(timeout_seconds: int = 900, confirmacao: str = "") -> dict:
    """
    Sobe o ambiente local de producao apenas quando a trava estiver habilitada.

    Requer SISTEMA_PET_MCP_ALLOW_PROD_ACTIONS=true e a confirmacao configurada
    em SISTEMA_PET_MCP_PROD_CONFIRMATION. Nao executa deploy remoto.
    """
    result = command_service.run_fluxo(
        "prod-up",
        timeout_seconds=timeout_seconds,
        confirmacao=confirmacao,
    )
    return _record("fluxo_prod_up", result.to_dict())


@mcp.tool()
def fluxo_status(timeout_seconds: int = 300) -> dict:
    result = command_service.run_fluxo("status", timeout_seconds=timeout_seconds)
    return _record("fluxo_status", result.to_dict())


@mcp.tool()
def api_health_check(url: str = config.default_health_url) -> dict:
    result = api_service.health_check(url)
    return _record("api_health_check", result.to_dict())


@mcp.tool()
def api_auth_route_smoke(url: str = config.default_auth_url) -> dict:
    result = api_service.auth_route_smoke(url)
    return _record("api_auth_route_smoke", result.to_dict())


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
    return _record("auth_validate_tabs_permissions", result.to_dict())


@mcp.tool()
def campaign_logs(limit: int = 20) -> dict:
    """
    Retorna os ultimos registros de execucao de campanhas no banco DEV.
    """
    return _record("campaign_logs", campaign_service.logs(limit=limit))


@mcp.tool()
def campaign_queue_status() -> dict:
    """
    Mostra o estado atual da fila de eventos do motor de campanhas no banco DEV.
    """
    return _record("campaign_queue_status", campaign_service.queue_status())


@mcp.tool()
def campaign_enqueue_test_event(
    event_type: str,
    payload_json: str = "{}",
    tenant_id: str = "",
) -> dict:
    """
    Injeta um evento de teste na fila de campanhas do banco DEV.
    """
    return _record(
        "campaign_enqueue_test_event",
        campaign_service.enqueue_test_event(
            event_type=event_type,
            payload_json=payload_json,
            tenant_id=tenant_id,
        ),
    )


@mcp.tool()
def backend_logs(lines: int = 50, filter_text: str = "") -> dict:
    """
    Retorna logs recentes do container backend DEV, com redaction de segredos.
    """
    return _record("backend_logs", log_service.backend_logs(lines=lines, filter_text=filter_text))


@mcp.tool()
def mcp_audit_report(limit: int = 50) -> dict:
    """
    Resume os logs locais de auditoria dos MCPs Frontend e Ops/API.
    """
    return _record("mcp_audit_report", audit_report_service.build(limit=limit))
