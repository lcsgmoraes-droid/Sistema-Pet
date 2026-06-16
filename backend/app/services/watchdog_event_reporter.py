from collections import Counter, deque
from datetime import datetime
import json
import os
from typing import Any


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


WATCHDOG_EVENT_LOG_PATH = os.getenv(
    "WATCHDOG_EVENT_LOG_PATH",
    os.path.join(os.getcwd(), "logs", "watchdog_events.jsonl"),
)
WATCHDOG_EVENT_MAX_READ_LINES = _env_int("WATCHDOG_EVENT_MAX_READ_LINES", 1000)


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


def _read_recent_watchdog_events(
    max_lines: int = WATCHDOG_EVENT_MAX_READ_LINES,
) -> list[dict[str, Any]]:
    if not os.path.exists(WATCHDOG_EVENT_LOG_PATH):
        return []

    lines: deque[str] = deque(maxlen=max(1, max_lines))
    try:
        with open(WATCHDOG_EVENT_LOG_PATH, "r", encoding="utf-8") as file:
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


def _filter_watchdog_events(
    events: list[dict[str, Any]],
    *,
    event_type: str | None = None,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    normalized_event_type = event_type.lower() if event_type else None
    normalized_status = status.lower() if status else None
    filtered: list[dict[str, Any]] = []

    for event in events:
        if (
            normalized_event_type
            and str(event.get("event_type") or "").lower() != normalized_event_type
        ):
            continue
        if (
            normalized_status
            and str(event.get("status") or "").lower() != normalized_status
        ):
            continue

        created_at = _event_created_at(event)
        if since and created_at and created_at < since:
            continue
        if until and created_at and created_at > until:
            continue

        filtered.append(event)

    return filtered


def get_watchdog_events(
    *,
    event_type: str | None = None,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db=None,
) -> list[dict[str, Any]]:
    if db is not None:
        events = _read_recent_watchdog_events()
        try:
            from app.services.ops_persistence_service import (
                query_recovery_actions,
                sync_watchdog_events_to_db,
            )

            sync_watchdog_events_to_db(db, events)
            action_type = None
            if event_type:
                action_type_map = {
                    "restart_triggered": "restart_backend",
                    "restart_loop_guard": "restart_loop_guard",
                    "health_failure": "health_failure",
                    "health_recovered": "health_recovered",
                    "uvicorn_start": "server_start",
                    "uvicorn_stop": "server_stop",
                    "uvicorn_exit": "server_exit",
                }
                action_type = action_type_map.get(event_type, event_type)
            return query_recovery_actions(
                db,
                action_type=action_type,
                status=status,
                since=since,
                until=until,
                limit=WATCHDOG_EVENT_MAX_READ_LINES,
            )
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    return _filter_watchdog_events(
        _read_recent_watchdog_events(),
        event_type=event_type,
        status=status,
        since=since,
        until=until,
    )


def list_watchdog_events(
    *,
    page: int = 1,
    page_size: int = 30,
    event_type: str | None = None,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db=None,
) -> dict[str, Any]:
    events = get_watchdog_events(
        event_type=event_type,
        status=status,
        since=since,
        until=until,
        db=db,
    )
    events.reverse()

    safe_page = max(1, page)
    safe_page_size = min(max(1, page_size), 100)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size

    return {
        "items": events[start:end],
        "total": len(events),
        "page": safe_page,
        "page_size": safe_page_size,
        "source": {
            "path": WATCHDOG_EVENT_LOG_PATH,
            "max_read_lines": WATCHDOG_EVENT_MAX_READ_LINES,
        },
    }


def summarize_watchdog_events(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    db=None,
) -> dict[str, Any]:
    events = get_watchdog_events(since=since, until=until, db=db)

    by_type = Counter(str(event.get("event_type") or "unknown") for event in events)
    by_status = Counter(str(event.get("status") or "unknown") for event in events)
    recovery_events = [
        event
        for event in events
        if str(event.get("event_type") or "").lower()
        in {"restart_triggered", "uvicorn_start", "uvicorn_exit"}
    ]

    return {
        "total": len(events),
        "by_type": by_type.most_common(),
        "by_status": by_status.most_common(),
        "recoveries": len(
            [
                event
                for event in events
                if str(event.get("event_type") or "").lower() == "restart_triggered"
            ]
        ),
        "latest": list(reversed(events))[:10],
        "latest_recovery": list(reversed(recovery_events))[:5],
        "source": {
            "path": WATCHDOG_EVENT_LOG_PATH,
            "max_read_lines": WATCHDOG_EVENT_MAX_READ_LINES,
        },
    }
