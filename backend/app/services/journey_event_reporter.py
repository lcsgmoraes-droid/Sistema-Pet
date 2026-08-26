"""Telemetria sanitizada para SLOs de jornadas críticas.

O caminho de request grava somente uma linha JSONL curta e nunca consulta o
banco. A sincronização para PostgreSQL acontece quando o painel Ops consulta os
dados, mantendo falhas de telemetria fora das jornadas do cliente.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import threading
from typing import Any, Iterable
import uuid

from fastapi import Request
from sqlalchemy.orm import Session


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


JOURNEY_EVENT_LOG_PATH = os.getenv(
    "JOURNEY_EVENT_LOG_PATH",
    os.path.join(os.getcwd(), "logs", "journey_events.jsonl"),
)
JOURNEY_EVENT_REPORT_MAX_READ_LINES = _env_int(
    "JOURNEY_EVENT_REPORT_MAX_READ_LINES", 50000
)
OUTCOMES = frozenset({"success", "expected_rejection", "failure"})
SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9_.-]{1,80}$")
SALE_FINALIZATION_PATH = re.compile(r"^/vendas/[0-9]+/finalizar$")
_lock = threading.Lock()

JOURNEY_OBJECTIVES: dict[str, dict[str, float]] = {
    "auth.login": {"success_rate_percent": 99.5, "p95_ms": 2000.0},
    "auth.tenant_selection": {
        "success_rate_percent": 99.5,
        "p95_ms": 2000.0,
    },
    "sale.finalization": {"success_rate_percent": 99.5, "p95_ms": 3000.0},
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_uuid_text(value: Any) -> str | None:
    try:
        return str(uuid.UUID(str(value))) if value else None
    except (TypeError, ValueError):
        return None


def _safe_code(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if SAFE_CODE_PATTERN.fullmatch(candidate) else fallback


def _normalize_path(path: str) -> str:
    normalized = str(path or "").split("?", 1)[0].rstrip("/") or "/"
    if normalized.startswith("/api/"):
        return normalized[4:] or "/"
    return normalized


def match_http_journey(method: str, path: str) -> dict[str, str] | None:
    """Retorna somente nomes e templates definidos pelo sistema."""

    if str(method or "").upper() != "POST":
        return None

    normalized = _normalize_path(path)
    if normalized == "/auth/login-multitenant":
        return {
            "journey": "auth.login",
            "path_template": "/auth/login-multitenant",
        }
    if normalized == "/auth/select-tenant":
        return {
            "journey": "auth.tenant_selection",
            "path_template": "/auth/select-tenant",
        }
    if SALE_FINALIZATION_PATH.fullmatch(normalized):
        return {
            "journey": "sale.finalization",
            "path_template": "/vendas/{venda_id}/finalizar",
        }
    if normalized == "/app/funcionario/pdv/vendas/finalizar":
        return {
            "journey": "sale.finalization",
            "path_template": "/app/funcionario/pdv/vendas/finalizar",
        }
    return None


def _verified_tenant_id(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    try:
        from app.auth.core import ALGORITHM
        from app.config import JWT_SECRET_KEY
        from app.security.jwt_compat import jwt

        payload = jwt.decode(token.strip(), JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
    return _safe_uuid_text(payload.get("tenant_id"))


def classify_http_outcome(
    status_code: int | None,
    *,
    exception: bool = False,
    replayed: bool = False,
) -> tuple[str, str]:
    if exception or status_code is None:
        return "failure", "unhandled_exception"
    if 200 <= status_code < 400:
        return "success", "idempotent_replay" if replayed else "completed"
    if 400 <= status_code < 500:
        return "expected_rejection", f"http_{status_code}"
    return "failure", f"http_{status_code}"


def record_journey_event(
    *,
    journey: str,
    outcome: str,
    reason_code: str,
    duration_ms: float,
    method: str,
    path_template: str,
    tenant_id: str | None = None,
    request_id: str | None = None,
    operation_id: str | None = None,
    status_code: int | None = None,
    provider: str | None = None,
    source: str = "request_context",
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Anexa um evento terminal seguro; qualquer falha retorna ``None``."""

    safe_journey = _safe_code(journey, "")
    safe_outcome = _safe_code(outcome, "")
    safe_reason = _safe_code(reason_code, "unknown")
    safe_method = str(method or "").upper()[:12]
    safe_template = str(path_template or "")[:180]
    if (
        not safe_journey
        or safe_outcome not in OUTCOMES
        or not safe_method
        or not safe_template.startswith("/")
    ):
        return None

    safe_request_id = str(request_id or "").strip()[:80] or None
    safe_operation_id = str(operation_id or safe_request_id or uuid.uuid4()).strip()[
        :96
    ]
    try:
        event = {
            "event_key": str(uuid.uuid4()),
            "created_at": _iso(now or _utcnow()),
            "journey": safe_journey,
            "outcome": safe_outcome,
            "reason_code": safe_reason,
            "duration_ms": round(max(float(duration_ms or 0), 0.0), 2),
            "status_code": int(status_code) if status_code is not None else None,
            "tenant_id": _safe_uuid_text(tenant_id),
            "request_id": safe_request_id,
            "operation_id": safe_operation_id,
            "method": safe_method,
            "path_template": safe_template,
            "provider": _safe_code(provider, "") or None,
            "source": _safe_code(source, "request_context"),
        }
        path = Path(JOURNEY_EVENT_LOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with _lock:
            with path.open("a", encoding="utf-8") as file:
                file.write(serialized + "\n")
    except Exception:
        return None
    return event


def record_http_journey_event(
    *,
    request: Request,
    request_id: str,
    method: str,
    path: str,
    duration_ms: float,
    status_code: int | None = None,
    exception: bool = False,
    replayed: bool = False,
) -> dict[str, Any] | None:
    matched = match_http_journey(method, path)
    if not matched:
        return None
    outcome, reason_code = classify_http_outcome(
        status_code,
        exception=exception,
        replayed=replayed,
    )
    return record_journey_event(
        journey=matched["journey"],
        outcome=outcome,
        reason_code=reason_code,
        duration_ms=duration_ms,
        method=method,
        path_template=matched["path_template"],
        tenant_id=_verified_tenant_id(request),
        request_id=request_id,
        operation_id=request_id,
        status_code=status_code,
    )


def _read_recent_events(
    max_lines: int = JOURNEY_EVENT_REPORT_MAX_READ_LINES,
) -> list[dict[str, Any]]:
    path = Path(JOURNEY_EVENT_LOG_PATH)
    if not path.exists():
        return []

    lines: deque[str] = deque(maxlen=max(1, max_lines))
    try:
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    lines.append(line.strip())
    except OSError:
        return []

    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("event_key"):
            events.append(event)
    return events


def _row_to_event(row) -> dict[str, Any]:
    return {
        "event_key": row.event_key,
        "created_at": _iso(row.created_at),
        "journey": row.journey,
        "outcome": row.outcome,
        "reason_code": row.reason_code,
        "duration_ms": float(row.duration_ms or 0),
        "status_code": row.status_code,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "request_id": row.request_id,
        "operation_id": row.operation_id,
        "method": row.method,
        "path_template": row.path_template,
        "provider": row.provider,
        "source": row.source,
    }


def sync_journey_events_to_db(db: Session, events: Iterable[dict[str, Any]]) -> int:
    from app.ops_models import OpsJourneyEvent

    unique_events: dict[str, dict[str, Any]] = {}
    for event in events:
        event_key = str(event.get("event_key") or "").strip()
        if event_key:
            unique_events[event_key] = event
    if not unique_events:
        return 0

    keys = list(unique_events)
    existing: set[str] = set()
    for start in range(0, len(keys), 500):
        existing.update(
            str(row[0])
            for row in db.query(OpsJourneyEvent.event_key)
            .filter(OpsJourneyEvent.event_key.in_(keys[start : start + 500]))
            .all()
        )

    inserted = 0
    for event_key, event in unique_events.items():
        if event_key in existing:
            continue
        created_at = _parse_dt(event.get("created_at"))
        journey = _safe_code(event.get("journey"), "")
        outcome = _safe_code(event.get("outcome"), "")
        if created_at is None or not journey or outcome not in OUTCOMES:
            continue
        db.add(
            OpsJourneyEvent(
                event_key=event_key[:96],
                created_at=created_at,
                journey=journey,
                outcome=outcome,
                reason_code=_safe_code(event.get("reason_code"), "unknown"),
                duration_ms=max(float(event.get("duration_ms") or 0), 0.0),
                status_code=int(event["status_code"])
                if event.get("status_code") is not None
                else None,
                tenant_id=uuid.UUID(str(event["tenant_id"]))
                if event.get("tenant_id")
                else None,
                request_id=str(event.get("request_id") or "")[:80] or None,
                operation_id=str(event.get("operation_id") or event_key)[:96],
                method=str(event.get("method") or "UNKNOWN")[:12],
                path_template=str(event.get("path_template") or "/unknown")[:180],
                provider=_safe_code(event.get("provider"), "") or None,
                source=_safe_code(event.get("source"), "request_context"),
            )
        )
        inserted += 1
    if inserted:
        db.commit()
    return inserted


def _filter_events(
    events: Iterable[dict[str, Any]],
    *,
    journey: str | None = None,
    tenant_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for event in events:
        if journey and event.get("journey") != journey:
            continue
        if tenant_id:
            actual_tenant = str(event.get("tenant_id") or "")
            if tenant_id == "sem_tenant":
                if actual_tenant:
                    continue
            elif actual_tenant != tenant_id:
                continue
        created_at = _parse_dt(event.get("created_at"))
        if created_at is None:
            continue
        if since and created_at < since:
            continue
        if until and created_at > until:
            continue
        selected.append(event)
    selected.sort(key=lambda event: _parse_dt(event.get("created_at")) or _utcnow())
    return selected


def get_journey_events(
    *,
    journey: str | None = None,
    tenant_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    if db is not None:
        try:
            from app.ops_models import OpsJourneyEvent

            sync_journey_events_to_db(db, _read_recent_events())
            query = db.query(OpsJourneyEvent)
            if journey:
                query = query.filter(OpsJourneyEvent.journey == journey)
            if tenant_id:
                if tenant_id == "sem_tenant":
                    query = query.filter(OpsJourneyEvent.tenant_id.is_(None))
                else:
                    query = query.filter(
                        OpsJourneyEvent.tenant_id == uuid.UUID(tenant_id)
                    )
            if since:
                query = query.filter(OpsJourneyEvent.created_at >= since)
            if until:
                query = query.filter(OpsJourneyEvent.created_at <= until)
            rows = query.order_by(
                OpsJourneyEvent.created_at.asc(), OpsJourneyEvent.id.asc()
            ).all()
            return [_row_to_event(row) for row in rows]
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    return _filter_events(
        _read_recent_events(),
        journey=journey,
        tenant_id=tenant_id,
        since=since,
        until=until,
    )


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 2)


def _summarize_group(
    events: list[dict[str, Any]], objective: dict[str, float] | None = None
) -> dict[str, Any]:
    successes = [event for event in events if event.get("outcome") == "success"]
    failures = [event for event in events if event.get("outcome") == "failure"]
    expected = [
        event for event in events if event.get("outcome") == "expected_rejection"
    ]
    eligible = successes + failures
    durations = [float(event.get("duration_ms") or 0) for event in eligible]
    eligible_count = len(eligible)
    success_rate = (
        round(len(successes) * 100 / eligible_count, 3) if eligible_count else None
    )
    p95_ms = _percentile(durations, 0.95)
    sample_status = (
        "no_measurement"
        if eligible_count == 0
        else "baseline_low"
        if eligible_count < 100
        else "measured"
    )

    objective_status = sample_status
    if sample_status == "measured" and objective:
        rate_met = (
            success_rate is not None
            and success_rate >= objective["success_rate_percent"]
        )
        latency_met = p95_ms is not None and p95_ms <= objective["p95_ms"]
        objective_status = "healthy" if rate_met and latency_met else "breached"

    return {
        "total_attempts": len(events),
        "eligible_attempts": eligible_count,
        "successes": len(successes),
        "expected_rejections": len(expected),
        "failures": len(failures),
        "success_rate_percent": success_rate,
        "latency_ms": {
            "p50": _percentile(durations, 0.50),
            "p95": p95_ms,
            "p99": _percentile(durations, 0.99),
            "max": round(max(durations), 2) if durations else None,
        },
        "sample_status": sample_status,
        "objective_status": objective_status,
        "objective": objective,
    }


def summarize_journey_events(
    *,
    events: list[dict[str, Any]] | None = None,
    journey: str | None = None,
    tenant_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    selected = events
    if selected is None:
        selected = get_journey_events(
            journey=journey,
            tenant_id=tenant_id,
            since=since,
            until=until,
            db=db,
        )

    by_journey: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_tenant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in selected:
        by_journey[str(event.get("journey") or "unknown")].append(event)
        by_tenant[str(event.get("tenant_id") or "sem_tenant")].append(event)

    return {
        "period": {
            "since": _iso(since) if since else None,
            "until": _iso(until) if until else None,
        },
        "overall": _summarize_group(selected),
        "by_journey": [
            {
                "journey": name,
                **_summarize_group(items, JOURNEY_OBJECTIVES.get(name)),
            }
            for name, items in sorted(by_journey.items())
        ],
        "by_tenant": [
            {"tenant_id": name, **_summarize_group(items)}
            for name, items in sorted(by_tenant.items())
        ],
        "source": {
            "path": JOURNEY_EVENT_LOG_PATH,
            "max_read_lines": JOURNEY_EVENT_REPORT_MAX_READ_LINES,
            "contains_personal_payload": False,
        },
    }


def list_journey_events(
    *,
    page: int = 1,
    page_size: int = 50,
    journey: str | None = None,
    tenant_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    events = get_journey_events(
        journey=journey,
        tenant_id=tenant_id,
        since=since,
        until=until,
        db=db,
    )
    events.reverse()
    safe_page = max(1, page)
    safe_size = min(max(1, page_size), 200)
    start = (safe_page - 1) * safe_size
    return {
        "items": events[start : start + safe_size],
        "total": len(events),
        "page": safe_page,
        "page_size": safe_size,
    }


__all__ = [
    "JOURNEY_EVENT_LOG_PATH",
    "classify_http_outcome",
    "get_journey_events",
    "list_journey_events",
    "match_http_journey",
    "record_http_journey_event",
    "record_journey_event",
    "summarize_journey_events",
    "sync_journey_events_to_db",
]
