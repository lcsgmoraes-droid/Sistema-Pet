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


def _latest_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return max(events, key=lambda event: _event_dt(event) or epoch, default=None)


def _top_path(events: list[dict[str, Any]]) -> str | None:
    paths = _top_paths(events, limit=1)
    return paths[0]["path"] if paths else None


def _alert_tone(severity: str) -> str:
    if severity == "critical":
        return "red"
    if severity == "warning":
        return "amber"
    return "blue"


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


def _build_actionable_alerts(
    db: Session,
    events: list[dict[str, Any]],
    watchdog: dict[str, Any],
    watchdog_summary: dict[str, Any],
    deploy_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    tenant_error_threshold = _env_int("OPS_ALERT_TENANT_5XX_CRITICAL", 2)
    tenant_slow_threshold = _env_int("OPS_ALERT_TENANT_SLOW_WARNING", 4)
    route_error_threshold = _env_int("OPS_ALERT_ROUTE_5XX_CRITICAL", 2)
    route_slow_threshold = _env_int("OPS_ALERT_ROUTE_SLOW_WARNING", 4)
    watchdog_recoveries = int(watchdog_summary.get("recoveries") or 0)

    if watchdog.get("status") != "healthy":
        alerts.append(
            {
                "id": "system:watchdog:degraded",
                "scope": "system",
                "kind": "watchdog_degraded",
                "severity": "critical",
                "tone": "red",
                "title": "Watchdog degradado agora",
                "detail": "O health operacional indica problema no banco, pool ou resposta interna.",
                "action": "Checar pool do banco, rotas lentas recentes e reinicios do backend antes de novas alteracoes.",
                "score": 1000,
            }
        )

    if watchdog_recoveries:
        alerts.append(
            {
                "id": "system:watchdog:recoveries",
                "scope": "system",
                "kind": "watchdog_recovery",
                "severity": "warning",
                "tone": "amber",
                "title": f"{watchdog_recoveries} recuperacao(oes) automatica(s)",
                "detail": "O sistema precisou se recuperar sozinho no periodo selecionado.",
                "action": "Abrir eventos imediatamente anteriores ao restart e procurar rota ou tenant recorrente.",
                "score": 700 + watchdog_recoveries,
            }
        )

    last_failed = _last_failed_deploy_after_success(deploy_events)
    if last_failed:
        alerts.append(
            {
                "id": "system:deploy:last_failed",
                "scope": "system",
                "kind": "deploy_failed",
                "severity": "critical",
                "tone": "red",
                "title": "Ultimo deploy registrado falhou",
                "detail": last_failed.get("message") or f"Etapa: {last_failed.get('step') or '-'}",
                "action": "Investigar a falha de deploy antes de empilhar nova mudanca em producao.",
                "score": 900,
            }
        )

    grouped_by_tenant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped_by_tenant[str(event.get("tenant_id") or "sem_tenant")].append(event)
        grouped_by_path[str(event.get("path") or "sem_path")].append(event)

    tenant_names = _tenant_names(db, set(grouped_by_tenant.keys()))

    for tenant_id, tenant_events in grouped_by_tenant.items():
        errors_5xx = sum(1 for event in tenant_events if _status_code(event) >= 500)
        slow_requests = sum(1 for event in tenant_events if _duration(event) >= SLOW_REQUEST_EVENT_MS)
        if errors_5xx < tenant_error_threshold and slow_requests < tenant_slow_threshold:
            continue

        latest = _latest_event(tenant_events)
        top_path = _top_path(tenant_events)
        tenant_name = tenant_names.get(tenant_id) or (
            "Sem tenant identificado" if tenant_id == "sem_tenant" else f"Tenant {tenant_id[:8]}"
        )
        severity = "critical" if errors_5xx >= tenant_error_threshold else "warning"
        kind = "tenant_5xx_recurrent" if severity == "critical" else "tenant_slow_recurrent"
        metric_detail = (
            f"{errors_5xx} erro(s) 5xx"
            if severity == "critical"
            else f"{slow_requests} requisicao(oes) lenta(s)"
        )
        alerts.append(
            {
                "id": f"tenant:{tenant_id}:{kind}",
                "scope": "tenant",
                "kind": kind,
                "severity": severity,
                "tone": _alert_tone(severity),
                "title": f"{tenant_name}: {metric_detail}",
                "detail": f"Rota mais recorrente: {top_path or 'sem rota dominante'}.",
                "action": "Filtrar o tenant, abrir o request_id mais recente e corrigir a causa raiz antes de tratar caso a caso.",
                "tenant_id": None if tenant_id == "sem_tenant" else tenant_id,
                "tenant_filter": tenant_id,
                "tenant_name": tenant_name,
                "path": top_path,
                "request_id": latest.get("request_id") if latest else None,
                "latest_at": _iso(_event_dt(latest) if latest else None),
                "total": len(tenant_events),
                "errors_5xx": errors_5xx,
                "slow_requests": slow_requests,
                "score": (500 if severity == "critical" else 250) + (errors_5xx * 20) + slow_requests,
            }
        )

    for path, path_events in grouped_by_path.items():
        errors_5xx = sum(1 for event in path_events if _status_code(event) >= 500)
        slow_requests = sum(1 for event in path_events if _duration(event) >= SLOW_REQUEST_EVENT_MS)
        if errors_5xx < route_error_threshold and slow_requests < route_slow_threshold:
            continue

        latest = _latest_event(path_events)
        tenant_count = len({str(event.get("tenant_id") or "sem_tenant") for event in path_events})
        severity = "critical" if errors_5xx >= route_error_threshold else "warning"
        kind = "route_5xx_recurrent" if severity == "critical" else "route_slow_recurrent"
        metric_detail = (
            f"{errors_5xx} erro(s) 5xx"
            if severity == "critical"
            else f"{slow_requests} chamada(s) lenta(s)"
        )
        alerts.append(
            {
                "id": f"route:{path}:{kind}",
                "scope": "route",
                "kind": kind,
                "severity": severity,
                "tone": _alert_tone(severity),
                "title": f"{metric_detail} em rota recorrente",
                "detail": f"{path} afetou {tenant_count} tenant(s) no periodo.",
                "action": "Filtrar a rota, comparar tenants afetados e procurar regressao, query lenta ou integracao externa.",
                "path": path,
                "request_id": latest.get("request_id") if latest else None,
                "latest_at": _iso(_event_dt(latest) if latest else None),
                "total": len(path_events),
                "errors_5xx": errors_5xx,
                "slow_requests": slow_requests,
                "tenant_count": tenant_count,
                "score": (450 if severity == "critical" else 220) + (errors_5xx * 18) + slow_requests + tenant_count,
            }
        )

    return sorted(alerts, key=lambda item: int(item.get("score") or 0), reverse=True)[:20]


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
    actionable_alerts = _build_actionable_alerts(
        db,
        error_events,
        watchdog,
        watchdog_summary,
        deploy_events,
    )
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
        "actionable_alerts": actionable_alerts,
        "tenant_incidents": tenant_incidents,
        "route_incidents": route_incidents,
        "latest": {
            "errors": list(reversed(error_events))[:10],
            "deploys": list(reversed(deploy_events))[:10],
            "watchdog": list(reversed(watchdog_events))[:10],
        },
    }
