import base64
from collections import Counter, deque
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import Request


_lock = threading.Lock()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


SLOW_REQUEST_EVENT_MS = _env_float("ERROR_REPORT_SLOW_REQUEST_MS", 3000)
ERROR_EVENT_LOG_PATH = os.getenv(
    "ERROR_EVENT_LOG_PATH",
    os.path.join(os.getcwd(), "logs", "error_events.jsonl"),
)
ERROR_EVENT_REPORT_MAX_READ_LINES = _env_int("ERROR_EVENT_REPORT_MAX_READ_LINES", 10000)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return {}


def _extract_identity(request: Request) -> dict[str, Any]:
    authorization = request.headers.get("authorization", "")
    tenant_id = request.headers.get("x-tenant-id")
    user_id = None
    user_email = None

    if authorization.lower().startswith("bearer "):
        payload = _decode_jwt_payload(authorization.split(" ", 1)[1].strip())
        tenant_id = tenant_id or payload.get("tenant_id")
        user_id = payload.get("user_id") or payload.get("id")
        user_email = payload.get("sub") or payload.get("email")

    return {
        "tenant_id": str(tenant_id) if tenant_id else None,
        "user_id": str(user_id) if user_id else None,
        "user_email": str(user_email) if user_email else None,
    }


def should_record_event(status_code: int | None, duration_ms: float) -> bool:
    return (status_code or 0) >= 500 or duration_ms >= SLOW_REQUEST_EVENT_MS


def record_request_event(
    *,
    request: Request,
    request_id: str,
    method: str,
    path: str,
    duration_ms: float,
    status_code: int | None = None,
    exception_type: str | None = None,
    exception_message: str | None = None,
) -> None:
    if exception_type is None and not should_record_event(status_code, duration_ms):
        return

    identity = _extract_identity(request)
    event = {
        "created_at": _utcnow_iso(),
        "request_id": request_id,
        "tenant_id": identity["tenant_id"],
        "user_id": identity["user_id"],
        "user_email": identity["user_email"],
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "exception_type": exception_type,
        "exception_message": (exception_message or "")[:300] or None,
        "client_ip": request.client.host if request.client else None,
        "user_agent": (request.headers.get("user-agent") or "")[:160] or None,
    }

    try:
        os.makedirs(os.path.dirname(ERROR_EVENT_LOG_PATH), exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with _lock:
            with open(ERROR_EVENT_LOG_PATH, "a", encoding="utf-8") as file:
                file.write(line + "\n")
    except Exception:
        # Telemetry must never break a customer request.
        return


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _event_created_at(event: dict[str, Any]) -> datetime | None:
    return _parse_dt(str(event.get("created_at") or ""))


def _read_recent_events(max_lines: int = ERROR_EVENT_REPORT_MAX_READ_LINES) -> list[dict[str, Any]]:
    if not os.path.exists(ERROR_EVENT_LOG_PATH):
        return []

    lines: deque[str] = deque(maxlen=max(1, max_lines))
    try:
        with open(ERROR_EVENT_LOG_PATH, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    lines.append(line)
    except OSError:
        return []

    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                events.append(parsed)
        except json.JSONDecodeError:
            continue
    return events


def _filter_events(
    events: list[dict[str, Any]],
    *,
    tenant_id: str | None = None,
    path_contains: str | None = None,
    status_min: int | None = None,
    slow_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    path_filter = path_contains.lower() if path_contains else None

    for event in events:
        if tenant_id and str(event.get("tenant_id") or "") != tenant_id:
            continue
        if path_filter and path_filter not in str(event.get("path") or "").lower():
            continue
        if status_min is not None and int(event.get("status_code") or 0) < status_min:
            continue
        if slow_only and float(event.get("duration_ms") or 0) < SLOW_REQUEST_EVENT_MS:
            continue

        created_at = _event_created_at(event)
        if since and created_at and created_at < since:
            continue
        if until and created_at and created_at > until:
            continue

        filtered.append(event)

    return filtered


def list_error_events(
    *,
    page: int = 1,
    page_size: int = 50,
    tenant_id: str | None = None,
    path_contains: str | None = None,
    status_min: int | None = None,
    slow_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    events = get_error_events(
        tenant_id=tenant_id,
        path_contains=path_contains,
        status_min=status_min,
        slow_only=slow_only,
        since=since,
        until=until,
    )
    events.reverse()

    safe_page = max(1, page)
    safe_page_size = min(max(1, page_size), 200)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size

    return {
        "items": events[start:end],
        "total": len(events),
        "page": safe_page,
        "page_size": safe_page_size,
        "source": {
            "path": ERROR_EVENT_LOG_PATH,
            "max_read_lines": ERROR_EVENT_REPORT_MAX_READ_LINES,
            "slow_request_ms": SLOW_REQUEST_EVENT_MS,
        },
    }


def summarize_error_events(
    *,
    tenant_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    events = get_error_events(
        tenant_id=tenant_id,
        since=since,
        until=until,
    )

    by_tenant = Counter(str(event.get("tenant_id") or "sem_tenant") for event in events)
    by_path = Counter(str(event.get("path") or "sem_path") for event in events)
    by_status = Counter(str(event.get("status_code") or "sem_status") for event in events)
    errors_5xx = sum(1 for event in events if int(event.get("status_code") or 0) >= 500)
    slow_requests = sum(
        1 for event in events if float(event.get("duration_ms") or 0) >= SLOW_REQUEST_EVENT_MS
    )

    latest = list(reversed(events))[:20]

    return {
        "total": len(events),
        "errors_5xx": errors_5xx,
        "slow_requests": slow_requests,
        "by_tenant": by_tenant.most_common(20),
        "by_path": by_path.most_common(20),
        "by_status": by_status.most_common(),
        "latest": latest,
        "source": {
            "path": ERROR_EVENT_LOG_PATH,
            "max_read_lines": ERROR_EVENT_REPORT_MAX_READ_LINES,
            "slow_request_ms": SLOW_REQUEST_EVENT_MS,
        },
    }


def get_error_events(
    *,
    tenant_id: str | None = None,
    path_contains: str | None = None,
    status_min: int | None = None,
    slow_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    return _filter_events(
        _read_recent_events(),
        tenant_id=tenant_id,
        path_contains=path_contains,
        status_min=status_min,
        slow_only=slow_only,
        since=since,
        until=until,
    )
