from __future__ import annotations

import subprocess
import time

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


def _run_docker_exec(container: str, cmd: list[str], timeout: int = 20) -> dict:
    """Executa comando em container Docker e retorna {ok, stdout, stderr}."""
    full_cmd = ["docker", "exec", container] + cmd
    try:
        result = subprocess.run(
            full_cmd, capture_output=True, text=True, timeout=timeout
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip()[-6000:],
            "stderr": result.stderr.strip()[-2000:],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Timeout", "exit_code": -1}
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "exit_code": -1}


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


# ---------------------------------------------------------------------------
# Ferramentas do Motor de Campanhas (DEV)
# ---------------------------------------------------------------------------

@mcp.tool()
def campaign_logs(limit: int = 20) -> dict:
    """
    Retorna os últimos registros de execução de campanhas (campaign_run_log)
    do banco DEV. Útil para verificar se os handlers estão disparando.

    Args:
        limit: Número de registros a retornar (padrão 20, máximo 100).
    """
    limit = min(int(limit), 100)
    sql = (
        f"SELECT id, campaign_id, event_type, evaluated, rewarded, errors, "
        f"duration_ms, run_at AT TIME ZONE 'America/Sao_Paulo' AS run_at_brt "
        f"FROM campaign_run_log "
        f"ORDER BY run_at DESC LIMIT {limit};"
    )
    return _run_docker_exec(
        "petshop-dev-postgres",
        ["psql", "-U", "petshop", "-d", "petshop_dev", "-c", sql],
    )


@mcp.tool()
def campaign_queue_status() -> dict:
    """
    Mostra o estado atual da fila de eventos do motor de campanhas
    (campaign_event_queue) no banco DEV — pendentes, processando, falhos.
    """
    sql = (
        "SELECT status, event_type, COUNT(*) as total, "
        "MAX(created_at AT TIME ZONE 'America/Sao_Paulo') as mais_recente "
        "FROM campaign_event_queue "
        "GROUP BY status, event_type "
        "ORDER BY status, total DESC;"
    )
    return _run_docker_exec(
        "petshop-dev-postgres",
        ["psql", "-U", "petshop", "-d", "petshop_dev", "-c", sql],
    )


@mcp.tool()
def campaign_enqueue_test_event(
    event_type: str,
    payload_json: str = "{}",
    tenant_id: str = "",
) -> dict:
    """
    Injeta um evento de teste na fila de campanhas do banco DEV.
    Útil para testar handlers sem esperar o scheduler semanal/mensal.

    Args:
        event_type: Tipo do evento. Opções válidas:
            "daily_birthday_check", "weekly_inactivity_check",
            "monthly_ranking_recalc", "purchase_completed", "customer_registered"
        payload_json: JSON do payload (ex: '{"customer_id": 1, "venda_id": 5, "venda_total": 150}')
        tenant_id: UUID do tenant. Se vazio, usa o primeiro tenant ativo no banco.
    """
    allowed = {
        "daily_birthday_check", "weekly_inactivity_check",
        "monthly_ranking_recalc", "purchase_completed", "customer_registered",
        "drawing_execution", "cpf_linked",
    }
    if event_type not in allowed:
        return {
            "ok": False,
            "error": f"event_type '{event_type}' não permitido. Use: {sorted(allowed)}",
        }

    # Se tenant_id não foi passado, busca o primeiro tenant
    if not tenant_id:
        result = _run_docker_exec(
            "petshop-dev-postgres",
            ["psql", "-U", "petshop", "-d", "petshop_dev", "-t", "-c",
             "SELECT id FROM tenants WHERE status='active' LIMIT 1;"],
        )
        if not result["ok"] or not result["stdout"].strip():
            return {"ok": False, "error": "Nenhum tenant ativo encontrado", **result}
        tenant_id = result["stdout"].strip()

    sql = (
        f"INSERT INTO campaign_event_queue "
        f"(tenant_id, event_type, event_origin, payload, status) "
        f"VALUES ('{tenant_id}', '{event_type}', 'system_scheduled', "
        f"'{payload_json}'::jsonb, 'pending') RETURNING id, tenant_id, event_type, status;"
    )
    return _run_docker_exec(
        "petshop-dev-postgres",
        ["psql", "-U", "petshop", "-d", "petshop_dev", "-c", sql],
    )


@mcp.tool()
def backend_logs(lines: int = 50, filter_text: str = "") -> dict:
    """
    Retorna os últimos N logs do container backend DEV.
    Pode filtrar por texto relevante (ex: "Campaign", "ERROR", "BirthdayHandler").

    Args:
        lines: Número de linhas finais a retornar (padrão 50).
        filter_text: Se informado, retorna apenas linhas que contêm esse texto (case-insensitive).
    """
    lines = min(int(lines), 500)
    if filter_text:
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines * 5), "petshop-dev-backend"],
                capture_output=True, text=True, timeout=15,
            )
            combined = result.stdout + result.stderr
            filtered = [
                line for line in combined.splitlines()
                if filter_text.lower() in line.lower()
            ][-lines:]
            return {
                "ok": True,
                "stdout": "\n".join(filtered),
                "total_matched": len(filtered),
            }
        except Exception as exc:
            return {"ok": False, "stderr": str(exc)}
    else:
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), "petshop-dev-backend"],
                capture_output=True, text=True, timeout=15,
            )
            return {
                "ok": result.returncode == 0,
                "stdout": (result.stdout + result.stderr).strip()[-8000:],
            }
        except Exception as exc:
            return {"ok": False, "stderr": str(exc)}
