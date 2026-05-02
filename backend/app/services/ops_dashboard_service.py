from collections import defaultdict
from datetime import datetime, timedelta, timezone
import os
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Tenant
from app.services.deploy_event_reporter import get_deploy_events, summarize_deploy_events
from app.services.error_event_reporter import (
    SLOW_REQUEST_EVENT_MS,
    get_error_events,
    summarize_error_events,
)
from app.services.watchdog_event_reporter import (
    get_watchdog_events,
    summarize_watchdog_events,
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _event_dt(event: dict[str, Any]) -> datetime | None:
    raw = str(event.get("created_at") or "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _status_code(event: dict[str, Any]) -> int:
    try:
        return int(event.get("status_code") or 0)
    except (TypeError, ValueError):
        return 0


def _duration(event: dict[str, Any]) -> float:
    try:
        return float(event.get("duration_ms") or 0)
    except (TypeError, ValueError):
        return 0


def _tenant_names(db: Session, tenant_ids: set[str]) -> dict[str, str]:
    real_ids = {tenant_id for tenant_id in tenant_ids if tenant_id and tenant_id != "sem_tenant"}
    if not real_ids:
        return {}

    tenants = db.query(Tenant.id, Tenant.name).filter(Tenant.id.in_(real_ids)).all()
    return {str(tenant.id): tenant.name for tenant in tenants}


def _top_paths(events: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    grouped: dict[str, int] = defaultdict(int)
    for event in events:
        grouped[str(event.get("path") or "sem_path")] += 1
    return [
        {"path": path, "total": total}
        for path, total in sorted(grouped.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def _build_tenant_incidents(db: Session, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event.get("tenant_id") or "sem_tenant")].append(event)

    names = _tenant_names(db, set(grouped.keys()))
    incidents: list[dict[str, Any]] = []

    for tenant_id, tenant_events in grouped.items():
        errors_5xx = sum(1 for event in tenant_events if _status_code(event) >= 500)
        slow_requests = sum(1 for event in tenant_events if _duration(event) >= SLOW_REQUEST_EVENT_MS)
        latest_at = max((_event_dt(event) for event in tenant_events), default=None)
        severity = "critical" if errors_5xx else "warning" if slow_requests else "info"
        incidents.append(
            {
                "tenant_id": None if tenant_id == "sem_tenant" else tenant_id,
                "tenant_name": names.get(tenant_id) or ("Sem tenant identificado" if tenant_id == "sem_tenant" else f"Tenant {tenant_id[:8]}"),
                "severity": severity,
                "total": len(tenant_events),
                "errors_5xx": errors_5xx,
                "slow_requests": slow_requests,
                "latest_at": _iso(latest_at),
                "top_paths": _top_paths(tenant_events),
            }
        )

    return sorted(
        incidents,
        key=lambda item: (item["errors_5xx"], item["slow_requests"], item["total"]),
        reverse=True,
    )[:20]


def _build_route_incidents(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event.get("path") or "sem_path")].append(event)

    incidents: list[dict[str, Any]] = []
    for path, route_events in grouped.items():
        durations = [_duration(event) for event in route_events]
        errors_5xx = sum(1 for event in route_events if _status_code(event) >= 500)
        slow_requests = sum(1 for event in route_events if _duration(event) >= SLOW_REQUEST_EVENT_MS)
        tenant_count = len({str(event.get("tenant_id") or "sem_tenant") for event in route_events})
        latest_at = max((_event_dt(event) for event in route_events), default=None)
        severity = "critical" if errors_5xx else "warning" if slow_requests else "info"
        incidents.append(
            {
                "path": path,
                "severity": severity,
                "total": len(route_events),
                "errors_5xx": errors_5xx,
                "slow_requests": slow_requests,
                "avg_duration_ms": round(sum(durations) / max(len(durations), 1), 2),
                "max_duration_ms": round(max(durations) if durations else 0, 2),
                "tenant_count": tenant_count,
                "latest_at": _iso(latest_at),
            }
        )

    return sorted(
        incidents,
        key=lambda item: (item["errors_5xx"], item["slow_requests"], item["max_duration_ms"]),
        reverse=True,
    )[:20]


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
            "Registra eventos de recuperacao para auditoria operacional",
        ],
    }


def _last_failed_deploy_after_success(deploy_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest = list(reversed(deploy_events))
    last_success = next(
        (event for event in latest if str(event.get("status") or "").lower() == "success"),
        None,
    )
    last_failed = next(
        (event for event in latest if str(event.get("status") or "").lower() == "failed"),
        None,
    )
    if last_failed and (not last_success or str(last_failed.get("created_at") or "") > str(last_success.get("created_at") or "")):
        return last_failed
    return None


def _build_alerts(
    *,
    watchdog: dict[str, Any],
    error_summary: dict[str, Any],
    deploy_events: list[dict[str, Any]],
    watchdog_summary: dict[str, Any],
    tenant_incidents: list[dict[str, Any]],
    route_incidents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    errors_5xx = int(error_summary.get("errors_5xx") or 0)
    slow_requests = int(error_summary.get("slow_requests") or 0)
    last_failed = _last_failed_deploy_after_success(deploy_events)
    recoveries = int(watchdog_summary.get("recoveries") or 0)

    if watchdog.get("status") != "healthy":
        alerts.append(
            {
                "severity": "critical",
                "tone": "red",
                "title": "Watchdog degradado",
                "detail": "O banco ou o pool nao respondeu dentro do limite operacional.",
                "action": "Acompanhar eventos do watchdog; se repetir, revisar pool, banco e rotas lentas.",
                "source": "watchdog",
            }
        )

    if errors_5xx:
        top_route = route_incidents[0]["path"] if route_incidents else "rotas com erro"
        top_tenant = tenant_incidents[0]["tenant_name"] if tenant_incidents else "tenant afetado"
        alerts.append(
            {
                "severity": "critical",
                "tone": "red",
                "title": f"{errors_5xx} erro(s) 5xx no periodo",
                "detail": f"Maior incidencia em {top_route}; tenant em destaque: {top_tenant}.",
                "action": "Abrir a rota critica, localizar request_id e corrigir a causa raiz.",
                "source": "error_events",
            }
        )

    if slow_requests:
        alerts.append(
            {
                "severity": "warning",
                "tone": "amber",
                "title": f"{slow_requests} requisicao(oes) lenta(s)",
                "detail": f"Acima de {int(SLOW_REQUEST_EVENT_MS)} ms.",
                "action": "Priorizar rotas com maior tempo maximo e tenants com recorrencia.",
                "source": "slow_requests",
            }
        )

    if last_failed:
        alerts.append(
            {
                "severity": "critical",
                "tone": "red",
                "title": "Ultimo deploy falhou",
                "detail": last_failed.get("message") or f"Etapa: {last_failed.get('step') or '-'}",
                "action": "Nao seguir com novo deploy sem entender a falha anterior.",
                "source": "deploy",
            }
        )

    if recoveries:
        alerts.append(
            {
                "severity": "warning",
                "tone": "amber",
                "title": f"{recoveries} recuperacao(oes) automatica(s)",
                "detail": "O watchdog precisou reiniciar o servidor no periodo.",
                "action": "Verificar eventos anteriores ao restart e identificar o gatilho.",
                "source": "watchdog_events",
            }
        )

    if not alerts:
        alerts.append(
            {
                "severity": "ok",
                "tone": "green",
                "title": "Sem alerta critico no periodo",
                "detail": "Health, deploys, erros e recuperacao automatica estao dentro do esperado.",
                "action": "Manter monitoramento.",
                "source": "ops",
            }
        )

    return alerts


def _overall_status(alerts: list[dict[str, Any]]) -> str:
    severities = {alert.get("severity") for alert in alerts}
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "degraded"
    return "healthy"


def build_ops_dashboard(db: Session, *, since: datetime | None = None, until: datetime | None = None) -> dict[str, Any]:
    now = _utcnow()
    period_since = since or (now - timedelta(hours=24))
    period_until = until

    error_events = get_error_events(since=period_since, until=period_until)
    deploy_events = get_deploy_events(since=period_since, until=period_until)
    watchdog_events = get_watchdog_events(since=period_since, until=period_until)

    error_summary = summarize_error_events(since=period_since, until=period_until)
    deploy_summary = summarize_deploy_events(since=period_since, until=period_until)
    watchdog_summary = summarize_watchdog_events(since=period_since, until=period_until)
    watchdog = _watchdog_now(db)
    tenant_incidents = _build_tenant_incidents(db, error_events)
    route_incidents = _build_route_incidents(error_events)
    alerts = _build_alerts(
        watchdog=watchdog,
        error_summary=error_summary,
        deploy_events=deploy_events,
        watchdog_summary=watchdog_summary,
        tenant_incidents=tenant_incidents,
        route_incidents=route_incidents,
    )

    return {
        "generated_at": _iso(now),
        "period": {
            "since": _iso(period_since),
            "until": _iso(period_until) if period_until else None,
        },
        "status": _overall_status(alerts),
        "alerts": alerts,
        "watchdog": watchdog,
        "self_healing": _self_healing_status(),
        "errors": error_summary,
        "deploys": deploy_summary,
        "watchdog_events": watchdog_summary,
        "tenant_incidents": tenant_incidents,
        "route_incidents": route_incidents,
        "latest": {
            "errors": list(reversed(error_events))[:10],
            "deploys": list(reversed(deploy_events))[:10],
            "watchdog": list(reversed(watchdog_events))[:10],
        },
    }
