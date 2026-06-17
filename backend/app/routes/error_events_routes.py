from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import require_admin
from app.services.audit_event_report_service import list_audit_events
from app.services.deploy_event_reporter import (
    list_deploy_events,
    summarize_deploy_events,
)
from app.services.error_event_reporter import list_error_events, summarize_error_events
from app.services.ops_dashboard_service import build_ops_dashboard
from app.services.ops_persistence_service import (
    list_ops_alerts,
    query_recovery_actions,
    summarize_ops_alerts,
)
from app.services.watchdog_event_reporter import (
    list_watchdog_events,
    summarize_watchdog_events,
)
from app.db import get_session
from sqlalchemy.orm import Session


router = APIRouter(
    prefix="/admin/observabilidade",
    tags=["Admin - Observabilidade"],
    dependencies=[Depends(require_admin)],
)


@router.get("/ops-summary")
def resumo_cockpit_ops(
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return build_ops_dashboard(db, since=since, until=until)


@router.get("/error-events")
def listar_eventos_erro(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tenant_id: str | None = Query(None),
    request_id: str | None = Query(None),
    path_contains: str | None = Query(None),
    status_min: int | None = Query(None, ge=100, le=599),
    slow_only: bool = Query(False),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return list_error_events(
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        request_id=request_id,
        path_contains=path_contains,
        status_min=status_min,
        slow_only=slow_only,
        since=since,
        until=until,
        db=db,
    )


@router.get("/error-events/summary")
def resumo_eventos_erro(
    tenant_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return summarize_error_events(
        tenant_id=tenant_id,
        since=since,
        until=until,
        db=db,
    )


@router.get("/audit-events")
def listar_eventos_auditoria(
    tenant_id: str | None = Query(None),
    request_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return list_audit_events(
        db,
        tenant_id=tenant_id,
        request_id=request_id,
        since=since,
        until=until,
        limit=limit,
    )


@router.get("/ops-alerts")
def listar_alertas_ops(
    status: str | None = Query("open"),
    severity: str | None = Query(None),
    tenant_id: str | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return {
        "items": list_ops_alerts(
            db,
            status=status,
            severity=severity,
            tenant_id=tenant_id,
            since=since,
            limit=limit,
        ),
        "summary": summarize_ops_alerts(db, since=since),
    }


@router.get("/recovery-actions")
def listar_acoes_recuperacao(
    action_type: str | None = Query(None),
    status: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    items = query_recovery_actions(
        db,
        action_type=action_type,
        status=status,
        since=since,
        until=until,
        limit=limit,
    )
    return {"items": items, "total": len(items)}


@router.get("/deploy-events")
def listar_eventos_deploy(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    status: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
) -> dict[str, Any]:
    return list_deploy_events(
        page=page,
        page_size=page_size,
        status=status,
        since=since,
        until=until,
    )


@router.get("/deploy-events/summary")
def resumo_eventos_deploy(
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
) -> dict[str, Any]:
    return summarize_deploy_events(
        since=since,
        until=until,
    )


@router.get("/watchdog-events")
def listar_eventos_watchdog(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    event_type: str | None = Query(None),
    status: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return list_watchdog_events(
        page=page,
        page_size=page_size,
        event_type=event_type,
        status=status,
        since=since,
        until=until,
        db=db,
    )


@router.get("/watchdog-events/summary")
def resumo_eventos_watchdog(
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return summarize_watchdog_events(
        since=since,
        until=until,
        db=db,
    )
