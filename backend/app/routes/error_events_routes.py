from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import require_admin
from app.services.deploy_event_reporter import list_deploy_events, summarize_deploy_events
from app.services.error_event_reporter import list_error_events, summarize_error_events


router = APIRouter(
    prefix="/admin/observabilidade",
    tags=["Admin - Observabilidade"],
    dependencies=[Depends(require_admin)],
)


@router.get("/error-events")
def listar_eventos_erro(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tenant_id: str | None = Query(None),
    path_contains: str | None = Query(None),
    status_min: int | None = Query(None, ge=100, le=599),
    slow_only: bool = Query(False),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
) -> dict[str, Any]:
    return list_error_events(
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        path_contains=path_contains,
        status_min=status_min,
        slow_only=slow_only,
        since=since,
        until=until,
    )


@router.get("/error-events/summary")
def resumo_eventos_erro(
    tenant_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
) -> dict[str, Any]:
    return summarize_error_events(
        tenant_id=tenant_id,
        since=since,
        until=until,
    )


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
