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


DEPLOY_EVENT_LOG_PATH = os.getenv(
    "DEPLOY_EVENT_LOG_PATH",
    os.path.join(os.getcwd(), "logs", "deploy_events.jsonl"),
)
DEPLOY_EVENT_MAX_READ_LINES = _env_int("DEPLOY_EVENT_MAX_READ_LINES", 500)


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


def _read_recent_deploy_events(
    max_lines: int = DEPLOY_EVENT_MAX_READ_LINES,
) -> list[dict[str, Any]]:
    if not os.path.exists(DEPLOY_EVENT_LOG_PATH):
        return []

    lines: deque[str] = deque(maxlen=max(1, max_lines))
    try:
        with open(DEPLOY_EVENT_LOG_PATH, "r", encoding="utf-8") as file:
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


def _filter_deploy_events(
    events: list[dict[str, Any]],
    *,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    normalized_status = status.lower() if status else None

    for event in events:
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


def list_deploy_events(
    *,
    page: int = 1,
    page_size: int = 30,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    events = get_deploy_events(
        status=status,
        since=since,
        until=until,
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
            "path": DEPLOY_EVENT_LOG_PATH,
            "max_read_lines": DEPLOY_EVENT_MAX_READ_LINES,
        },
    }


def summarize_deploy_events(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    events = get_deploy_events(
        since=since,
        until=until,
    )

    by_status = Counter(str(event.get("status") or "unknown") for event in events)
    latest = list(reversed(events))[:10]
    last_success = next(
        (
            event
            for event in reversed(events)
            if str(event.get("status") or "").lower() == "success"
        ),
        None,
    )
    last_failed = next(
        (
            event
            for event in reversed(events)
            if str(event.get("status") or "").lower() == "failed"
        ),
        None,
    )

    return {
        "total": len(events),
        "by_status": by_status.most_common(),
        "latest": latest,
        "last_success": last_success,
        "last_failed": last_failed,
        "source": {
            "path": DEPLOY_EVENT_LOG_PATH,
            "max_read_lines": DEPLOY_EVENT_MAX_READ_LINES,
        },
    }


def get_deploy_events(
    *,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    return _filter_deploy_events(
        _read_recent_deploy_events(),
        status=status,
        since=since,
        until=until,
    )
