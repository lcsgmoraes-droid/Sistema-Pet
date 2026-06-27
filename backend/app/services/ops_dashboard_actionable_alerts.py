"""Alertas acionaveis persistidos do painel operacional."""

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.services.error_event_reporter import SLOW_REQUEST_EVENT_MS
from app.services.ops_dashboard_incidents import _top_path
from app.services.ops_dashboard_utils import (
    _duration,
    _env_int,
    _event_dt,
    _event_payload_value,
    _event_time_text,
    _iso,
    _latest_event,
    _status_code,
    _tenant_names,
)


def _alert_tone(severity: str) -> str:
    if severity == "critical":
        return "red"
    if severity == "warning":
        return "amber"
    return "blue"


def _summary_count(summary: dict[str, Any], key: str, names: set[str]) -> int:
    total = 0
    for item in summary.get(key) or []:
        if not item:
            continue
        if isinstance(item, (list, tuple)):
            name = str(item[0] if item else "").lower()
            value = item[1] if len(item) > 1 else 0
        elif isinstance(item, dict):
            name = str(item.get("name", "")).lower()
            value = item.get("count", 0)
        else:
            name = str(item).lower()
            value = 1
        if name in names:
            total += int(value or 0)
    return total


def _last_failed_deploy_after_success(
    deploy_events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    latest = list(reversed(deploy_events))
    last_success = next(
        (
            event
            for event in latest
            if str(event.get("status") or "").lower() == "success"
        ),
        None,
    )
    last_failed = next(
        (
            event
            for event in latest
            if str(event.get("status") or "").lower() == "failed"
        ),
        None,
    )
    if last_failed and (
        not last_success
        or str(last_failed.get("created_at") or "")
        > str(last_success.get("created_at") or "")
    ):
        return last_failed
    return None


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
    watchdog_problem_statuses = {
        "warning",
        "cooldown",
        "restart_loop_guard",
        "failed",
        "unhealthy",
    }
    watchdog_failure_threshold = _env_int("OPS_ALERT_WATCHDOG_FAILURE_WARNING", 2)
    watchdog_failures = _summary_count(
        watchdog_summary, "by_status", watchdog_problem_statuses
    )
    latest_watchdog_event = (watchdog_summary.get("latest") or [None])[0]
    latest_watchdog_status = str(
        _event_payload_value(latest_watchdog_event, "status") or "unknown"
    )
    latest_watchdog_message = str(
        _event_payload_value(latest_watchdog_event, "message") or ""
    )
    latest_watchdog_at = _event_time_text(latest_watchdog_event)
    worker_health = str(
        _event_payload_value(latest_watchdog_event, "worker_health") or ""
    ).lower()

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

    if watchdog_failures >= watchdog_failure_threshold:
        alerts.append(
            {
                "id": "system:watchdog:recurrent_failures",
                "scope": "system",
                "kind": "watchdog_recurrent_failure",
                "severity": "warning",
                "tone": "amber",
                "title": f"{watchdog_failures} falha(s) recorrente(s) do watchdog externo",
                "detail": latest_watchdog_message
                or f"Ultimo status: {latest_watchdog_status}",
                "action": "Abrir eventos do watchdog externo e corrigir a causa recorrente antes que vire restart em loop.",
                "latest_at": latest_watchdog_at,
                "total": watchdog_failures,
                "score": 760 + watchdog_failures,
            }
        )

    if worker_health and worker_health not in {"healthy", "running"}:
        alerts.append(
            {
                "id": "system:job:worker_bling_unhealthy",
                "scope": "system",
                "kind": "worker_bling_unhealthy",
                "severity": "critical",
                "tone": "red",
                "title": "Worker Bling degradado",
                "detail": f"Health do worker: {worker_health}. {latest_watchdog_message}".strip(),
                "action": "Checar container worker-bling, heartbeat e jobs Bling antes de aceitar novos eventos.",
                "latest_at": latest_watchdog_at,
                "total": 1,
                "score": 880,
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
                "detail": last_failed.get("message")
                or f"Etapa: {last_failed.get('step') or '-'}",
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
        slow_requests = sum(
            1 for event in tenant_events if _duration(event) >= SLOW_REQUEST_EVENT_MS
        )
        if (
            errors_5xx < tenant_error_threshold
            and slow_requests < tenant_slow_threshold
        ):
            continue

        latest = _latest_event(tenant_events)
        top_path = _top_path(tenant_events)
        tenant_name = tenant_names.get(tenant_id) or (
            "Sem tenant identificado"
            if tenant_id == "sem_tenant"
            else f"Tenant {tenant_id[:8]}"
        )
        severity = "critical" if errors_5xx >= tenant_error_threshold else "warning"
        kind = (
            "tenant_5xx_recurrent"
            if severity == "critical"
            else "tenant_slow_recurrent"
        )
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
                "score": (500 if severity == "critical" else 250)
                + (errors_5xx * 20)
                + slow_requests,
            }
        )

    for path, path_events in grouped_by_path.items():
        errors_5xx = sum(1 for event in path_events if _status_code(event) >= 500)
        slow_requests = sum(
            1 for event in path_events if _duration(event) >= SLOW_REQUEST_EVENT_MS
        )
        if errors_5xx < route_error_threshold and slow_requests < route_slow_threshold:
            continue

        latest = _latest_event(path_events)
        tenant_count = len(
            {str(event.get("tenant_id") or "sem_tenant") for event in path_events}
        )
        severity = "critical" if errors_5xx >= route_error_threshold else "warning"
        kind = (
            "route_5xx_recurrent" if severity == "critical" else "route_slow_recurrent"
        )
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
                "score": (450 if severity == "critical" else 220)
                + (errors_5xx * 18)
                + slow_requests
                + tenant_count,
            }
        )

    return sorted(alerts, key=lambda item: int(item.get("score") or 0), reverse=True)[
        :20
    ]
