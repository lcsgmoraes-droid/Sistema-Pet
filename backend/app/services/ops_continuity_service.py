"""Read safe backup/restore evidence for the operational cockpit."""

from collections import deque
from datetime import datetime, timezone
import json
import os
from typing import Any


CONTINUITY_EVENT_LOG_PATH = os.getenv(
    "OPS_CONTINUITY_EVENT_LOG_PATH",
    os.path.join(os.getcwd(), "logs", "continuity_events.jsonl"),
)
CONTINUITY_EVENT_MAX_READ_LINES = 500


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _parse_datetime(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_events() -> list[dict[str, Any]]:
    lines: deque[str] = deque(maxlen=CONTINUITY_EVENT_MAX_READ_LINES)
    try:
        with open(CONTINUITY_EVENT_LOG_PATH, encoding="utf-8") as event_file:
            for line in event_file:
                if line.strip():
                    lines.append(line)
    except OSError:
        return []

    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(event, dict)
            and event.get("operation") in {"backup", "external_copy", "restore"}
            and event.get("status") in {"ok", "failed"}
            and _parse_datetime(event.get("created_at"))
        ):
            events.append(event)
    return sorted(events, key=lambda item: _parse_datetime(item["created_at"]))


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if str(value) else None
    except (TypeError, ValueError):
        return None


def _operation_summary(
    events: list[dict[str, Any]],
    operation: str,
    *,
    max_age_hours: float,
    now: datetime,
) -> dict[str, Any]:
    operation_events = [event for event in events if event["operation"] == operation]
    latest_attempt = operation_events[-1] if operation_events else None
    successes = [event for event in operation_events if event["status"] == "ok"]
    latest_success = successes[-1] if successes else None
    success_at = (
        _parse_datetime(latest_success.get("created_at")) if latest_success else None
    )
    age_hours = (
        max(0.0, (now - success_at).total_seconds() / 3600) if success_at else None
    )

    if latest_attempt and latest_attempt["status"] == "failed":
        status = "failed"
    elif latest_success is None:
        status = "missing"
    elif age_hours is not None and age_hours > max_age_hours:
        status = "stale"
    else:
        status = "healthy"

    return {
        "status": status,
        "last_attempt_at": latest_attempt.get("created_at") if latest_attempt else None,
        "last_success_at": latest_success.get("created_at") if latest_success else None,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
        "max_age_hours": max_age_hours,
        "backup_file": latest_success.get("backup_file") if latest_success else None,
        "backup_bytes": _safe_int(latest_success.get("backup_bytes"))
        if latest_success
        else None,
        "backup_sha256": latest_success.get("backup_sha256")
        if latest_success
        else None,
        "public_tables": _safe_int(latest_success.get("public_tables"))
        if latest_success
        else None,
        "alembic_rows": _safe_int(latest_success.get("alembic_rows"))
        if latest_success
        else None,
    }


def summarize_continuity(*, now: datetime | None = None) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    backup_max_age_hours = _env_float("OPS_BACKUP_MAX_AGE_HOURS", 26)
    restore_max_age_hours = _env_float("OPS_RESTORE_MAX_AGE_HOURS", 24 * 31)
    rpo_target_hours = _env_float("OPS_RPO_TARGET_HOURS", 24)
    rto_target_hours = _env_float("OPS_RTO_TARGET_HOURS", 4)
    events = _read_events()
    backup = _operation_summary(
        events, "backup", max_age_hours=backup_max_age_hours, now=current_time
    )
    restore = _operation_summary(
        events, "restore", max_age_hours=restore_max_age_hours, now=current_time
    )
    external_copy = _operation_summary(
        events,
        "external_copy",
        max_age_hours=backup_max_age_hours,
        now=current_time,
    )

    if backup["status"] != "healthy":
        status = "critical"
    elif restore["status"] != "healthy" or external_copy["status"] != "healthy":
        status = "warning"
    else:
        status = "healthy"

    backup_age = backup["age_hours"]
    return {
        "status": status,
        "backup": backup,
        "external_copy": external_copy,
        "restore": restore,
        "objectives": {
            "rpo_target_hours": rpo_target_hours,
            "rpo_met": backup_age is not None and backup_age <= rpo_target_hours,
            "rto_target_hours": rto_target_hours,
            "rto_test_evidence": restore["status"] == "healthy",
            "external_copy_verified": external_copy["status"] == "healthy",
        },
    }
