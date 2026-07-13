"""Orquestrador do painel operacional."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.services.deploy_event_reporter import (
    get_deploy_events,
    summarize_deploy_events,
)
from app.services.error_event_reporter import (
    get_error_events,
    summarize_error_events,
)
from app.services.ops_alert_notifier import notify_ops_alerts
from app.services.ops_continuity_service import summarize_continuity
from app.services.ops_dashboard_actionable_alerts import _build_actionable_alerts
from app.services.ops_dashboard_health import (
    _current_health_status,
    _overall_status,
    _self_healing_status,
    _watchdog_now,
)
from app.services.ops_dashboard_incidents import (
    _build_route_incidents,
    _build_tenant_incidents,
)
from app.services.ops_dashboard_period_alerts import _build_alerts
from app.services.ops_dashboard_utils import _env_int, _iso, _tenant_names, _utcnow
from app.services.ops_persistence_service import (
    list_ops_alerts,
    query_recovery_actions,
    summarize_ops_alerts,
    upsert_ops_alerts,
)
from app.services.ops_release_status_service import summarize_release_status
from app.services.ops_tls_status_service import summarize_tls_status
from app.services.watchdog_event_reporter import (
    get_watchdog_events,
    summarize_watchdog_events,
)

try:
    from app.services.bling_pedido_webhook_queue_service import (
        get_bling_pedido_webhook_queue_snapshot,
    )
except Exception:  # pragma: no cover - Ops must stay available during partial deploys
    get_bling_pedido_webhook_queue_snapshot = None


def build_ops_dashboard(
    db: Session, *, since: datetime | None = None, until: datetime | None = None
) -> dict[str, Any]:
    now = _utcnow()
    period_since = since or (now - timedelta(hours=24))
    period_until = until
    current_window_minutes = max(1, _env_int("OPS_CURRENT_WINDOW_MINUTES", 5))
    current_since = now - timedelta(minutes=current_window_minutes)

    error_events = get_error_events(since=period_since, until=period_until, db=db)
    deploy_events = get_deploy_events(since=period_since, until=period_until)
    watchdog_events = get_watchdog_events(since=period_since, until=period_until, db=db)

    error_summary = summarize_error_events(
        since=period_since, until=period_until, db=db
    )
    current_error_summary = summarize_error_events(
        since=current_since, until=now, db=db
    )
    deploy_summary = summarize_deploy_events(since=period_since, until=period_until)
    watchdog_summary = summarize_watchdog_events(
        since=period_since, until=period_until, db=db
    )
    watchdog = _watchdog_now(db)
    continuity = summarize_continuity(now=now)
    tls = summarize_tls_status(now=now)
    release = summarize_release_status()
    queue_snapshot: dict[str, Any] = {}
    if get_bling_pedido_webhook_queue_snapshot is not None:
        try:
            queue_snapshot = get_bling_pedido_webhook_queue_snapshot(db)
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            queue_snapshot = {"status": "unavailable"}
    if queue_snapshot.get("by_tenant"):
        queue_tenant_names = _tenant_names(
            db,
            {
                str(item.get("tenant_id") or item.get("tenant_key") or "")
                for item in queue_snapshot.get("by_tenant", [])
                if item.get("tenant_id") or item.get("tenant_key")
            },
        )
        for item in queue_snapshot.get("by_tenant", []):
            tenant_key = str(
                item.get("tenant_id") or item.get("tenant_key") or "sem_tenant"
            )
            item["tenant_name"] = queue_tenant_names.get(tenant_key) or (
                "Sem tenant identificado"
                if tenant_key == "sem_tenant"
                else f"Tenant {tenant_key[:8]}"
            )
    current_status = _current_health_status(
        watchdog=watchdog,
        error_summary=current_error_summary,
        since=current_since,
        until=now,
    )
    tenant_incidents = _build_tenant_incidents(db, error_events)
    route_incidents = _build_route_incidents(error_events)
    actionable_alerts = _build_actionable_alerts(
        db,
        error_events,
        watchdog,
        watchdog_summary,
        deploy_events,
        tls=tls,
        release=release,
    )
    persisted_actionable_alerts = upsert_ops_alerts(db, actionable_alerts)
    try:
        ops_notification_delivery = notify_ops_alerts(
            persisted_actionable_alerts or actionable_alerts
        )
    except Exception as exc:
        ops_notification_delivery = {
            "enabled": False,
            "status": "failed",
            "error_type": type(exc).__name__,
            "attempted": 0,
            "sent": 0,
            "failed": 0,
            "skipped_duplicate": 0,
        }
    ops_notifications = summarize_ops_alerts(db, since=period_since)
    active_ops_alerts = list_ops_alerts(db, status="open", since=period_since, limit=20)
    recovery_actions = query_recovery_actions(
        db, since=period_since, until=period_until, limit=20
    )
    alerts = _build_alerts(
        db=db,
        watchdog=watchdog,
        error_summary=error_summary,
        deploy_events=deploy_events,
        watchdog_summary=watchdog_summary,
        tenant_incidents=tenant_incidents,
        route_incidents=route_incidents,
        queue_snapshot=queue_snapshot,
        continuity=continuity,
        tls=tls,
        release=release,
    )
    period_status = _overall_status(alerts)

    return {
        "generated_at": _iso(now),
        "period": {
            "since": _iso(period_since),
            "until": _iso(period_until) if period_until else None,
        },
        "status": period_status,
        "period_status": period_status,
        "current_status": current_status,
        "alerts": alerts,
        "watchdog": watchdog,
        "self_healing": _self_healing_status(),
        "errors": error_summary,
        "deploys": deploy_summary,
        "watchdog_events": watchdog_summary,
        "queues": {
            "bling_pedido_webhooks": queue_snapshot,
        },
        "continuity": continuity,
        "tls": tls,
        "release": release,
        "actionable_alerts": persisted_actionable_alerts or actionable_alerts,
        "ops_notifications": {
            **ops_notifications,
            "active": active_ops_alerts,
            "delivery": ops_notification_delivery,
        },
        "recovery_actions": recovery_actions,
        "tenant_incidents": tenant_incidents,
        "route_incidents": route_incidents,
        "latest": {
            "errors": list(reversed(error_events))[:10],
            "deploys": list(reversed(deploy_events))[:10],
            "watchdog": list(reversed(watchdog_events))[:10],
        },
    }
