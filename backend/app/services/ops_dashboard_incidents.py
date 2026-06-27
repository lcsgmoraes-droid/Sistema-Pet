"""Montagem de incidentes operacionais por tenant e rota."""

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.services.error_event_reporter import SLOW_REQUEST_EVENT_MS
from app.services.ops_dashboard_utils import (
    _duration,
    _event_dt,
    _iso,
    _status_code,
    _tenant_names,
)


def _top_paths(events: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    grouped: dict[str, int] = defaultdict(int)
    for event in events:
        grouped[str(event.get("path") or "sem_path")] += 1
    return [
        {"path": path, "total": total}
        for path, total in sorted(
            grouped.items(), key=lambda item: item[1], reverse=True
        )[:limit]
    ]


def _top_path(events: list[dict[str, Any]]) -> str | None:
    paths = _top_paths(events, limit=1)
    return paths[0]["path"] if paths else None


def _build_tenant_incidents(
    db: Session, events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event.get("tenant_id") or "sem_tenant")].append(event)

    names = _tenant_names(db, set(grouped.keys()))
    incidents: list[dict[str, Any]] = []

    for tenant_id, tenant_events in grouped.items():
        errors_5xx = sum(1 for event in tenant_events if _status_code(event) >= 500)
        slow_requests = sum(
            1 for event in tenant_events if _duration(event) >= SLOW_REQUEST_EVENT_MS
        )
        latest_at = max((_event_dt(event) for event in tenant_events), default=None)
        severity = "critical" if errors_5xx else "warning" if slow_requests else "info"
        incidents.append(
            {
                "tenant_id": None if tenant_id == "sem_tenant" else tenant_id,
                "tenant_name": names.get(tenant_id)
                or (
                    "Sem tenant identificado"
                    if tenant_id == "sem_tenant"
                    else f"Tenant {tenant_id[:8]}"
                ),
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
        slow_requests = sum(
            1 for event in route_events if _duration(event) >= SLOW_REQUEST_EVENT_MS
        )
        tenant_count = len(
            {str(event.get("tenant_id") or "sem_tenant") for event in route_events}
        )
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
        key=lambda item: (
            item["errors_5xx"],
            item["slow_requests"],
            item["max_duration_ms"],
        ),
        reverse=True,
    )[:20]
