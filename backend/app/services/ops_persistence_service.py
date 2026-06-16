from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.ops_models import OpsAlert, OpsErrorEvent, OpsRecoveryAction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _tenant_uuid(value: Any) -> UUID | None:
    if not value:
        return None
    text = str(value)
    if text == "sem_tenant":
        return None
    try:
        return UUID(text)
    except ValueError:
        return None


def _hash_key(prefix: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def _error_event_key(event: dict[str, Any]) -> str:
    request_id = str(event.get("request_id") or "").strip()
    if request_id:
        return f"request:{request_id}"
    return _hash_key(
        "legacy",
        {
            "created_at": event.get("created_at"),
            "method": event.get("method"),
            "path": event.get("path"),
            "status_code": event.get("status_code"),
            "duration_ms": event.get("duration_ms"),
            "exception_type": event.get("exception_type"),
            "exception_message": event.get("exception_message"),
        },
    )


def _recovery_action_key(event: dict[str, Any]) -> str:
    return _hash_key(
        "watchdog",
        {
            "created_at": event.get("created_at"),
            "event_type": event.get("event_type"),
            "status": event.get("status"),
            "message": event.get("message"),
            "pid": event.get("pid"),
            "uvicorn_pid": event.get("uvicorn_pid"),
        },
    )


def _action_type(event_type: str) -> str:
    mapping = {
        "restart_triggered": "restart_backend",
        "restart_loop_guard": "restart_loop_guard",
        "health_failure": "health_failure",
        "health_recovered": "health_recovered",
        "uvicorn_start": "server_start",
        "uvicorn_stop": "server_stop",
        "uvicorn_exit": "server_exit",
    }
    return mapping.get(event_type, event_type or "watchdog_event")


def _row_to_error_event(row: OpsErrorEvent) -> dict[str, Any]:
    payload = row.payload or {}
    return {
        "created_at": _iso(row.created_at),
        "request_id": row.request_id,
        "tenant_id": str(row.tenant_id) if row.tenant_id else payload.get("tenant_id"),
        "user_id": row.user_id,
        "user_email": row.user_email,
        "method": row.method,
        "path": row.path,
        "status_code": row.status_code,
        "duration_ms": row.duration_ms,
        "exception_type": row.exception_type,
        "exception_message": row.exception_message,
        "client_ip": row.client_ip,
        "user_agent": row.user_agent,
        "source": row.source,
    }


def _row_to_alert(row: OpsAlert) -> dict[str, Any]:
    payload = row.payload or {}
    data = {
        "id": row.id,
        "alert_key": row.alert_key,
        "tenant_filter": str(row.tenant_id)
        if row.tenant_id
        else payload.get("tenant_filter"),
        "scope": row.scope,
        "kind": row.kind,
        "severity": row.severity,
        "status": row.status,
        "title": row.title,
        "detail": row.detail,
        "action": row.action,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "tenant_name": row.tenant_name,
        "path": row.path,
        "request_id": row.request_id,
        "first_seen_at": _iso(row.first_seen_at),
        "last_seen_at": _iso(row.last_seen_at),
        "latest_event_at": _iso(row.latest_event_at),
        "occurrence_count": row.occurrence_count,
        "score": row.score,
        "payload": payload,
    }
    for key in (
        "tone",
        "errors_5xx",
        "slow_requests",
        "total",
        "tenant_count",
        "latest_at",
    ):
        if key in payload:
            data[key] = payload[key]
    return data


def _row_to_recovery_action(row: OpsRecoveryAction) -> dict[str, Any]:
    payload = row.payload or {}
    return {
        "id": row.id,
        "action_key": row.action_key,
        "action_type": row.action_type,
        "event_type": row.source_event_type,
        "status": row.status,
        "reason": row.reason,
        "message": row.message,
        "pid": row.pid,
        "uvicorn_pid": row.uvicorn_pid,
        "hostname": row.hostname,
        "created_at": _iso(row.created_at),
        "started_at": _iso(row.started_at),
        "finished_at": _iso(row.finished_at),
        "payload": payload,
    }


def persist_error_event(
    db: Session, event: dict[str, Any], *, commit: bool = False
) -> bool:
    event_key = _error_event_key(event)
    if db.query(OpsErrorEvent.id).filter(OpsErrorEvent.event_key == event_key).first():
        return False

    created_at = _parse_dt(event.get("created_at")) or _utcnow()
    tenant_raw = event.get("tenant_id")
    db.add(
        OpsErrorEvent(
            event_key=event_key,
            created_at=created_at,
            tenant_id=_tenant_uuid(tenant_raw),
            user_id=str(event.get("user_id")) if event.get("user_id") else None,
            user_email=str(event.get("user_email"))
            if event.get("user_email")
            else None,
            request_id=str(event.get("request_id"))
            if event.get("request_id")
            else None,
            method=str(event.get("method")) if event.get("method") else None,
            path=str(event.get("path"))[:600] if event.get("path") else None,
            status_code=_safe_int(event.get("status_code"), 0) or None,
            duration_ms=_safe_float(event.get("duration_ms")),
            exception_type=str(event.get("exception_type"))[:160]
            if event.get("exception_type")
            else None,
            exception_message=str(event.get("exception_message"))
            if event.get("exception_message")
            else None,
            client_ip=str(event.get("client_ip"))[:80]
            if event.get("client_ip")
            else None,
            user_agent=str(event.get("user_agent"))[:300]
            if event.get("user_agent")
            else None,
            source=str(event.get("source") or "request_context")[:60],
            payload={**event, "tenant_id": str(tenant_raw) if tenant_raw else None},
        )
    )
    if commit:
        db.commit()
    return True


def sync_error_events_to_db(db: Session, events: list[dict[str, Any]]) -> int:
    if not events:
        return 0

    added = 0
    keys = [_error_event_key(event) for event in events]
    existing: set[str] = set()
    for start in range(0, len(keys), 500):
        chunk = keys[start : start + 500]
        rows = (
            db.query(OpsErrorEvent.event_key)
            .filter(OpsErrorEvent.event_key.in_(chunk))
            .all()
        )
        existing.update(row[0] for row in rows)

    for event, key in zip(events, keys):
        if key in existing:
            continue
        try:
            if persist_error_event(db, event, commit=False):
                added += 1
                existing.add(key)
        except Exception:
            db.rollback()
            return added

    if added:
        db.commit()
    return added


def query_error_events(
    db: Session,
    *,
    tenant_id: str | None = None,
    request_id: str | None = None,
    path_contains: str | None = None,
    status_min: int | None = None,
    slow_only: bool = False,
    slow_request_ms: float = 3000,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    query = db.query(OpsErrorEvent)

    if tenant_id:
        if tenant_id == "sem_tenant":
            query = query.filter(OpsErrorEvent.tenant_id.is_(None))
        else:
            tenant_uuid = _tenant_uuid(tenant_id)
            if tenant_uuid is None:
                return []
            query = query.filter(OpsErrorEvent.tenant_id == tenant_uuid)
    if request_id:
        query = query.filter(OpsErrorEvent.request_id == request_id.strip())
    if path_contains:
        query = query.filter(OpsErrorEvent.path.ilike(f"%{path_contains}%"))
    if status_min is not None:
        query = query.filter(OpsErrorEvent.status_code >= status_min)
    if slow_only:
        query = query.filter(OpsErrorEvent.duration_ms >= slow_request_ms)
    if since:
        query = query.filter(OpsErrorEvent.created_at >= since)
    if until:
        query = query.filter(OpsErrorEvent.created_at <= until)

    rows = (
        query.order_by(OpsErrorEvent.created_at.asc(), OpsErrorEvent.id.asc())
        .limit(10000)
        .all()
    )
    return [_row_to_error_event(row) for row in rows]


def persist_recovery_event(
    db: Session, event: dict[str, Any], *, commit: bool = False
) -> bool:
    action_key = _recovery_action_key(event)
    if (
        db.query(OpsRecoveryAction.id)
        .filter(OpsRecoveryAction.action_key == action_key)
        .first()
    ):
        return False

    event_type = str(event.get("event_type") or "watchdog_event")
    created_at = _parse_dt(event.get("created_at")) or _utcnow()
    db.add(
        OpsRecoveryAction(
            action_key=action_key,
            action_type=_action_type(event_type),
            status=str(event.get("status") or "info")[:32],
            reason=str(event.get("message")) if event.get("message") else None,
            source_event_type=event_type[:80],
            message=str(event.get("message")) if event.get("message") else None,
            pid=_safe_int(event.get("pid"), 0) or None,
            uvicorn_pid=_safe_int(event.get("uvicorn_pid"), 0) or None,
            hostname=str(event.get("hostname"))[:255]
            if event.get("hostname")
            else None,
            started_at=created_at,
            finished_at=created_at,
            created_at=created_at,
            payload=event,
        )
    )
    if commit:
        db.commit()
    return True


def sync_watchdog_events_to_db(db: Session, events: list[dict[str, Any]]) -> int:
    if not events:
        return 0

    added = 0
    keys = [_recovery_action_key(event) for event in events]
    existing: set[str] = set()
    for start in range(0, len(keys), 500):
        chunk = keys[start : start + 500]
        rows = (
            db.query(OpsRecoveryAction.action_key)
            .filter(OpsRecoveryAction.action_key.in_(chunk))
            .all()
        )
        existing.update(row[0] for row in rows)

    for event, key in zip(events, keys):
        if key in existing:
            continue
        try:
            if persist_recovery_event(db, event, commit=False):
                added += 1
                existing.add(key)
        except Exception:
            db.rollback()
            return added

    if added:
        db.commit()
    return added


def query_recovery_actions(
    db: Session,
    *,
    action_type: str | None = None,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    query = db.query(OpsRecoveryAction)
    if action_type:
        query = query.filter(OpsRecoveryAction.action_type == action_type)
    if status:
        query = query.filter(OpsRecoveryAction.status == status)
    if since:
        query = query.filter(OpsRecoveryAction.created_at >= since)
    if until:
        query = query.filter(OpsRecoveryAction.created_at <= until)
    rows = (
        query.order_by(OpsRecoveryAction.created_at.asc(), OpsRecoveryAction.id.asc())
        .limit(limit)
        .all()
    )
    return [_row_to_recovery_action(row) for row in rows]


def upsert_ops_alerts(
    db: Session, alerts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    now = _utcnow()
    persisted: list[dict[str, Any]] = []

    for alert in alerts:
        alert_key = str(alert.get("id") or _hash_key("alert", alert))[:180]
        latest_event_at = _parse_dt(alert.get("latest_at")) or now
        row = db.query(OpsAlert).filter(OpsAlert.alert_key == alert_key).first()

        if row is None:
            row = OpsAlert(
                alert_key=alert_key,
                first_seen_at=latest_event_at,
                last_seen_at=latest_event_at,
                occurrence_count=1,
            )
            db.add(row)
        else:
            previous_payload = row.payload or {}
            changed = (
                previous_payload.get("latest_at") != alert.get("latest_at")
                or previous_payload.get("total") != alert.get("total")
                or previous_payload.get("errors_5xx") != alert.get("errors_5xx")
                or previous_payload.get("slow_requests") != alert.get("slow_requests")
            )
            if changed:
                row.occurrence_count = (row.occurrence_count or 0) + 1
            row.last_seen_at = latest_event_at

        row.scope = str(alert.get("scope") or "system")[:40]
        row.kind = str(alert.get("kind") or "ops_alert")[:80]
        row.severity = str(alert.get("severity") or "info")[:24]
        row.status = "open"
        row.title = str(alert.get("title") or "Alerta operacional")[:255]
        row.detail = str(alert.get("detail")) if alert.get("detail") else None
        row.action = str(alert.get("action")) if alert.get("action") else None
        row.tenant_id = _tenant_uuid(
            alert.get("tenant_filter") or alert.get("tenant_id")
        )
        row.tenant_name = (
            str(alert.get("tenant_name"))[:255] if alert.get("tenant_name") else None
        )
        row.path = str(alert.get("path"))[:600] if alert.get("path") else None
        row.request_id = (
            str(alert.get("request_id"))[:80] if alert.get("request_id") else None
        )
        row.latest_event_at = latest_event_at
        row.score = _safe_int(alert.get("score"), 0)
        row.payload = alert
        row.updated_at = now
        persisted.append(_row_to_alert(row))

    if alerts:
        db.commit()
    return persisted


def list_ops_alerts(
    db: Session,
    *,
    status: str | None = "open",
    severity: str | None = None,
    tenant_id: str | None = None,
    since: datetime | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    query = db.query(OpsAlert)
    if status:
        query = query.filter(OpsAlert.status == status)
    if severity:
        query = query.filter(OpsAlert.severity == severity)
    if tenant_id:
        tenant_uuid = _tenant_uuid(tenant_id)
        if tenant_id == "sem_tenant":
            query = query.filter(OpsAlert.tenant_id.is_(None))
        elif tenant_uuid:
            query = query.filter(OpsAlert.tenant_id == tenant_uuid)
    if since:
        query = query.filter(OpsAlert.last_seen_at >= since)

    rows = (
        query.order_by(
            OpsAlert.severity.asc(), OpsAlert.score.desc(), OpsAlert.last_seen_at.desc()
        )
        .limit(max(1, min(limit, 200)))
        .all()
    )
    return [_row_to_alert(row) for row in rows]


def summarize_ops_alerts(
    db: Session, *, since: datetime | None = None
) -> dict[str, Any]:
    query = db.query(OpsAlert)
    if since:
        query = query.filter(OpsAlert.last_seen_at >= since)
    rows = query.all()
    by_status = Counter(row.status for row in rows)
    by_severity = Counter(row.severity for row in rows)
    open_rows = [row for row in rows if row.status == "open"]
    return {
        "total": len(rows),
        "open": len(open_rows),
        "critical_open": len([row for row in open_rows if row.severity == "critical"]),
        "warning_open": len([row for row in open_rows if row.severity == "warning"]),
        "by_status": by_status.most_common(),
        "by_severity": by_severity.most_common(),
        "latest": [
            _row_to_alert(row)
            for row in sorted(rows, key=lambda item: item.last_seen_at, reverse=True)[
                :10
            ]
        ],
    }
