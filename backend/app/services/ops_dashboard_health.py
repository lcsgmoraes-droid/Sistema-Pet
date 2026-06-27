"""Status atual e health operacional do painel Ops."""

from datetime import datetime
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ops_dashboard_utils import (
    _env_bool,
    _env_float,
    _env_int,
    _iso,
    _utcnow,
)


def _watchdog_now(db: Session) -> dict[str, Any]:
    started = time.perf_counter()
    max_latency_ms = _env_float("WATCHDOG_DB_MAX_LATENCY_MS", 3000)

    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        status = "healthy" if latency_ms <= max_latency_ms else "degraded"
        return {
            "status": status,
            "database": "connected",
            "latency_ms": latency_ms,
            "max_latency_ms": max_latency_ms,
            "pool": db.bind.pool.status() if db.bind is not None else None,
            "timestamp": _iso(_utcnow()),
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "database": "error",
            "error_type": type(exc).__name__,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "pool": db.bind.pool.status() if db.bind is not None else None,
            "timestamp": _iso(_utcnow()),
        }


def _self_healing_status() -> dict[str, Any]:
    enabled = _env_bool("WATCHDOG_ENABLED", True)
    return {
        "status": "ativo" if enabled else "desativado",
        "watchdog_enabled": enabled,
        "docker_restart_policy": "always",
        "failure_threshold": _env_int("WATCHDOG_FAILURE_THRESHOLD", 4),
        "interval_seconds": _env_int("WATCHDOG_INTERVAL_SECONDS", 15),
        "timeout_seconds": _env_int("WATCHDOG_TIMEOUT_SECONDS", 6),
        "startup_grace_seconds": _env_int("WATCHDOG_STARTUP_GRACE_SECONDS", 90),
        "restart_delay_seconds": _env_int("WATCHDOG_RESTART_DELAY_SECONDS", 10),
        "db_max_latency_ms": _env_float("WATCHDOG_DB_MAX_LATENCY_MS", 3000),
        "capabilities": [
            "Reinicia o servidor se o health operacional falhar repetidamente",
            "Mantem o container em pe com restart policy do Docker",
            "Registra eventos de recuperacao em banco para auditoria operacional",
            "Aciona guarda contra loop de restart quando falhas se repetem em janela curta",
        ],
    }


def _overall_status(alerts: list[dict[str, Any]]) -> str:
    severities = {alert.get("severity") for alert in alerts}
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "degraded"
    return "healthy"


def _current_health_status(
    *,
    watchdog: dict[str, Any],
    error_summary: dict[str, Any],
    since: datetime,
    until: datetime,
) -> dict[str, Any]:
    watchdog_status = str(watchdog.get("status") or "unknown")
    errors_5xx = int(error_summary.get("errors_5xx") or 0)
    slow_requests = int(error_summary.get("slow_requests") or 0)
    window_minutes = max(1, round((until - since).total_seconds() / 60))
    latency_ms = watchdog.get("latency_ms")

    status = "healthy"
    title = "Servidor saudavel agora"
    detail = f"Sem 5xx ou lentidao nos ultimos {window_minutes} min."
    action = "Manter monitoramento."

    if watchdog_status == "unhealthy":
        status = "critical"
        title = "Servidor indisponivel agora"
        detail = "O watchdog nao conseguiu consultar o banco neste momento."
        action = "Verificar container, conexao com banco e pool imediatamente."
    elif watchdog_status == "degraded":
        status = "degraded"
        title = "Servidor degradado agora"
        detail = f"O banco respondeu acima do limite ({latency_ms or '-'} ms)."
        action = "Acompanhar pool, banco e rotas lentas antes de novo deploy."
    elif errors_5xx:
        status = "degraded"
        title = "Instabilidade recente"
        detail = f"{errors_5xx} erro(s) 5xx nos ultimos {window_minutes} min."
        action = "Abrir incidentes recentes e corrigir a rota com falha."
    elif slow_requests:
        status = "degraded"
        title = "Lentidao recente"
        detail = f"{slow_requests} requisicao(oes) lenta(s) nos ultimos {window_minutes} min."
        action = "Verificar rotas lentas e tenants afetados agora."

    return {
        "status": status,
        "title": title,
        "detail": detail,
        "action": action,
        "since": _iso(since),
        "until": _iso(until),
        "window_minutes": window_minutes,
        "errors_5xx": errors_5xx,
        "slow_requests": slow_requests,
        "watchdog_status": watchdog_status,
        "database": watchdog.get("database"),
        "latency_ms": latency_ms,
    }
