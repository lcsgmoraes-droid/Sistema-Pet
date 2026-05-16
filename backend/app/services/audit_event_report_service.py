from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models import AuditLog


REQUEST_ID_KEYS = {"request_id", "correlation_id", "trace_id"}


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


def parse_json_object(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def extract_request_id_from_audit_payload(payload: Any) -> str | None:
    parsed = parse_json_object(payload)
    if isinstance(parsed, dict):
        for key in REQUEST_ID_KEYS:
            value = parsed.get(key)
            if value:
                return str(value)
        for value in parsed.values():
            found = extract_request_id_from_audit_payload(value)
            if found:
                return found
    if isinstance(parsed, list):
        for value in parsed:
            found = extract_request_id_from_audit_payload(value)
            if found:
                return found
    return None


def audit_row_matches_request_id(row: AuditLog, request_id: str | None) -> bool:
    if not request_id:
        return True
    normalized = str(request_id).strip()
    if not normalized:
        return True
    for field in (row.details, row.new_value, row.old_value):
        if extract_request_id_from_audit_payload(field) == normalized:
            return True
    return False


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def row_to_audit_event(row: AuditLog) -> dict[str, Any]:
    details = parse_json_object(row.details)
    new_value = parse_json_object(row.new_value)
    old_value = parse_json_object(row.old_value)
    request_id = (
        extract_request_id_from_audit_payload(details)
        or extract_request_id_from_audit_payload(new_value)
        or extract_request_id_from_audit_payload(old_value)
    )

    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "user_id": row.user_id,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "request_id": request_id,
        "old_value": old_value,
        "new_value": new_value,
        "details": details,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "timestamp": _iso(row.timestamp),
    }


def list_audit_events(
    db: Session,
    *,
    tenant_id: str | None = None,
    request_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    query = db.query(AuditLog)

    if tenant_id:
        if tenant_id == "sem_tenant":
            query = query.filter(AuditLog.tenant_id.is_(None))
        else:
            tenant_uuid = _tenant_uuid(tenant_id)
            if tenant_uuid is None:
                return {"items": [], "total": 0}
            query = query.filter(AuditLog.tenant_id == tenant_uuid)
    if since:
        query = query.filter(AuditLog.timestamp >= since)
    if until:
        query = query.filter(AuditLog.timestamp <= until)

    normalized_request_id = str(request_id or "").strip()
    if normalized_request_id:
        pattern = f"%{normalized_request_id}%"
        query = query.filter(
            or_(
                AuditLog.details.ilike(pattern),
                AuditLog.new_value.ilike(pattern),
                AuditLog.old_value.ilike(pattern),
            )
        )

    rows = query.order_by(desc(AuditLog.timestamp), desc(AuditLog.id)).limit(max(1, min(limit, 500))).all()
    if normalized_request_id:
        rows = [row for row in rows if audit_row_matches_request_id(row, normalized_request_id)]

    return {
        "items": [row_to_audit_event(row) for row in rows],
        "total": len(rows),
    }
