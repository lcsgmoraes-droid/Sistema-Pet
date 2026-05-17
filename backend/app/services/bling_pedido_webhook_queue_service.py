from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.bling_pedido_webhook_queue_models import BlingPedidoWebhookEvent
from app.utils.correlation import derive_correlation_id, operation_correlation_context
from app.utils.logger import logger


STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_PROCESSED = "processed"
STATUS_FAILED = "failed"
STATUS_DEAD = "dead"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _webhook_tenant_id() -> UUID | None:
    raw = _text(os.getenv("BLING_WEBHOOK_TENANT_ID"))
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


def _canonical_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _extract_metadata(payload: dict) -> dict[str, str | None]:
    envelope = _dict(payload)
    data = _dict(envelope.get("data", envelope))
    pedido_ref = _dict(data.get("pedido") or data.get("pedidoVenda"))

    event_id = _text(
        envelope.get("eventId")
        or envelope.get("event_id")
        or envelope.get("idEvento")
        or envelope.get("id_evento")
    )
    event_type = _text(
        envelope.get("event")
        or envelope.get("event_type")
        or envelope.get("tipo")
        or envelope.get("type")
    ) or "legacy"

    pedido_bling_id = _text(
        data.get("id")
        or pedido_ref.get("id")
        or pedido_ref.get("numero")
        or data.get("pedido_bling_id")
    )

    if event_id:
        dedupe_key = f"event:{event_id}"
    else:
        digest = hashlib.sha256(_canonical_payload(envelope).encode("utf-8")).hexdigest()
        dedupe_key = f"payload:{digest[:88]}"

    return {
        "dedupe_key": dedupe_key[:96],
        "event_id": event_id[:120] if event_id else None,
        "event_type": event_type[:80],
        "pedido_bling_id": pedido_bling_id[:50] if pedido_bling_id else None,
    }


def _summarize_response(value: Any) -> dict:
    if isinstance(value, dict):
        return {
            key: value.get(key)
            for key in ("status", "acao", "motivo", "pedido_id", "erros_estoque", "request_id", "correlation_id")
            if key in value
        }
    return {"result": str(value)[:300]}


def _backoff_seconds(attempts: int) -> int:
    base = _env_int("BLING_PEDIDO_WEBHOOK_RETRY_BASE_SECONDS", 30)
    cap = _env_int("BLING_PEDIDO_WEBHOOK_RETRY_MAX_SECONDS", 15 * 60)
    return min(cap, max(5, base) * (2 ** max(0, attempts - 1)))


def _event_correlation_id(event: Any) -> str:
    reference = (
        getattr(event, "event_id", None)
        or getattr(event, "dedupe_key", None)
        or getattr(event, "id", None)
    )
    return derive_correlation_id("job.bling_pedido_webhook", reference)


def enqueue_bling_pedido_webhook(db: Session, payload: dict) -> dict[str, Any]:
    """Persiste o webhook e retorna rapidamente para o Bling."""
    metadata = _extract_metadata(payload)
    existing = (
        db.query(BlingPedidoWebhookEvent)
        .filter(BlingPedidoWebhookEvent.dedupe_key == metadata["dedupe_key"])
        .first()
    )
    if existing:
        return {
            "status": "queued",
            "queue_id": existing.id,
            "queue_status": existing.status,
            "deduplicated": True,
        }

    event = BlingPedidoWebhookEvent(
        tenant_id=_webhook_tenant_id(),
        dedupe_key=metadata["dedupe_key"],
        event_id=metadata["event_id"],
        event_type=metadata["event_type"] or "legacy",
        pedido_bling_id=metadata["pedido_bling_id"],
        status=STATUS_PENDING,
        max_attempts=_env_int("BLING_PEDIDO_WEBHOOK_MAX_ATTEMPTS", 6),
        next_attempt_at=_utcnow(),
        payload=payload,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(BlingPedidoWebhookEvent)
            .filter(BlingPedidoWebhookEvent.dedupe_key == metadata["dedupe_key"])
            .first()
        )
        if existing:
            return {
                "status": "queued",
                "queue_id": existing.id,
                "queue_status": existing.status,
                "deduplicated": True,
            }
        raise

    db.refresh(event)
    return {
        "status": "queued",
        "queue_id": event.id,
        "queue_status": event.status,
        "deduplicated": False,
    }


def _claim_next_event(db: Session) -> BlingPedidoWebhookEvent | None:
    now = _utcnow()
    stale_after = now - timedelta(seconds=_env_int("BLING_PEDIDO_WEBHOOK_PROCESSING_TIMEOUT_SECONDS", 10 * 60))

    event = (
        db.query(BlingPedidoWebhookEvent)
        .filter(
            or_(
                BlingPedidoWebhookEvent.status.in_([STATUS_PENDING, STATUS_FAILED]),
                (
                    (BlingPedidoWebhookEvent.status == STATUS_PROCESSING)
                    & (BlingPedidoWebhookEvent.started_at < stale_after)
                ),
            ),
            BlingPedidoWebhookEvent.next_attempt_at <= now,
            BlingPedidoWebhookEvent.attempts < BlingPedidoWebhookEvent.max_attempts,
        )
        .order_by(BlingPedidoWebhookEvent.next_attempt_at.asc(), BlingPedidoWebhookEvent.id.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not event:
        return None

    event.status = STATUS_PROCESSING
    event.started_at = now
    event.attempts = int(event.attempts or 0) + 1
    event.last_error = None
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _mark_processed(db: Session, event_id: int, response: Any) -> None:
    event = db.get(BlingPedidoWebhookEvent, event_id)
    if not event:
        return

    event.status = STATUS_PROCESSED
    event.processed_at = _utcnow()
    event.response_payload = _summarize_response(response)
    event.last_error = None
    db.add(event)
    db.commit()


def _mark_failed(db: Session, event_id: int, exc: Exception) -> None:
    db.rollback()
    event = db.get(BlingPedidoWebhookEvent, event_id)
    if not event:
        return

    attempts = int(event.attempts or 0)
    max_attempts = int(event.max_attempts or 1)
    event.status = STATUS_DEAD if attempts >= max_attempts else STATUS_FAILED
    event.next_attempt_at = _utcnow() + timedelta(seconds=_backoff_seconds(attempts))
    event.last_error = f"{type(exc).__name__}: {str(exc)[:900]}"
    db.add(event)
    db.commit()


def process_pending_bling_pedido_webhooks(db: Session, *, limit: int | None = None) -> dict[str, Any]:
    """Processa webhooks pendentes fora da request HTTP."""
    safe_limit = max(1, min(int(limit or _env_int("BLING_PEDIDO_WEBHOOK_QUEUE_LIMIT", 20)), 100))
    processed = 0
    failed = 0
    dead = 0

    for _ in range(safe_limit):
        event = _claim_next_event(db)
        if not event:
            break

        correlation_id = _event_correlation_id(event)
        try:
            from app.integracao_bling_pedido_routes import processar_pedido_bling_payload

            with operation_correlation_context(
                "job.bling_pedido_webhook",
                correlation_id=correlation_id,
            ):
                response = processar_pedido_bling_payload(dict(event.payload or {}), db)
                if isinstance(response, dict):
                    response = dict(response)
                    response.setdefault("request_id", correlation_id)
                    response.setdefault("correlation_id", correlation_id)
            _mark_processed(db, event.id, response)
            processed += 1
        except Exception as exc:  # pragma: no cover - defensive operational guard
            logger.error(
                "bling_pedido_webhook_queue_failed",
                f"Falha ao processar webhook id={event.id}: {exc}",
                event_id=event.id,
                correlation_id=correlation_id,
                error=str(exc),
            )
            _mark_failed(db, event.id, exc)
            failed += 1
            refreshed = db.get(BlingPedidoWebhookEvent, event.id)
            if refreshed and refreshed.status == STATUS_DEAD:
                dead += 1

    return {
        "processed": processed,
        "failed": failed,
        "dead": dead,
        "limit": safe_limit,
    }


def get_bling_pedido_webhook_queue_snapshot(db: Session) -> dict[str, Any]:
    rows = (
        db.query(BlingPedidoWebhookEvent.status, func.count(BlingPedidoWebhookEvent.id))
        .group_by(BlingPedidoWebhookEvent.status)
        .all()
    )
    counts: dict[str, int] = {
        str(status or "unknown"): int(total or 0)
        for status, total in rows
    }
    open_statuses = [STATUS_PENDING, STATUS_PROCESSING, STATUS_FAILED, STATUS_DEAD]
    tenant_rows = (
        db.query(
            BlingPedidoWebhookEvent.tenant_id,
            BlingPedidoWebhookEvent.status,
            func.count(BlingPedidoWebhookEvent.id),
            func.min(BlingPedidoWebhookEvent.created_at),
            func.max(BlingPedidoWebhookEvent.updated_at),
        )
        .filter(BlingPedidoWebhookEvent.status.in_(open_statuses))
        .group_by(BlingPedidoWebhookEvent.tenant_id, BlingPedidoWebhookEvent.status)
        .all()
    )
    tenants: dict[str, dict[str, Any]] = {}
    for tenant_id, status, total, oldest_at, latest_at in tenant_rows:
        tenant_key = str(tenant_id) if tenant_id else "sem_tenant"
        item = tenants.setdefault(
            tenant_key,
            {
                "tenant_id": None if tenant_key == "sem_tenant" else tenant_key,
                "tenant_key": tenant_key,
                "pending": 0,
                "processing": 0,
                "failed": 0,
                "dead": 0,
                "total_open": 0,
                "oldest_open_at": None,
                "latest_event_at": None,
            },
        )
        status_key = str(status or "unknown")
        if status_key in open_statuses:
            item[status_key] = int(total or 0)
        item["total_open"] += int(total or 0)
        if oldest_at and (not item["oldest_open_at"] or oldest_at.isoformat() < item["oldest_open_at"]):
            item["oldest_open_at"] = oldest_at.isoformat()
        if latest_at and (not item["latest_event_at"] or latest_at.isoformat() > item["latest_event_at"]):
            item["latest_event_at"] = latest_at.isoformat()

    by_tenant = sorted(
        tenants.values(),
        key=lambda item: (int(item.get("dead") or 0), int(item.get("failed") or 0), int(item.get("total_open") or 0)),
        reverse=True,
    )
    return {
        "total": sum(counts.values()),
        "total_sampled": sum(counts.values()),
        "pending": counts.get(STATUS_PENDING, 0),
        "processing": counts.get(STATUS_PROCESSING, 0),
        "failed": counts.get(STATUS_FAILED, 0),
        "dead": counts.get(STATUS_DEAD, 0),
        "processed": counts.get(STATUS_PROCESSED, 0),
        "counts": counts,
        "by_tenant": by_tenant,
    }
