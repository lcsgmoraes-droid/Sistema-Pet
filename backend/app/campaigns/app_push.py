from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.notification_service import enqueue_push
from app.services.push_devices import load_customer_push_targets


def enqueue_campaign_push(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
    body: str,
    idempotency_key: str,
    title: str,
    kind: str,
    campaign=None,
    payload: dict[str, Any] | None = None,
    legacy_push_token: str | None = None,
    privacy_customer_id: int | None = None,
) -> bool:
    if not load_customer_push_targets(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        legacy_push_token=legacy_push_token,
    ):
        return False

    push_payload = _campaign_payload(campaign=campaign, kind=kind, payload=payload)
    return enqueue_push(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        subject=title,
        body=body,
        idempotency_key=idempotency_key,
        push_token=legacy_push_token,
        privacy_customer_id=privacy_customer_id,
        source="campaign",
        kind=kind,
        payload=push_payload,
    )


def _campaign_payload(
    *, campaign=None, kind: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "source": "campaign",
        "kind": kind,
        "target": "benefits",
    }
    if campaign is not None:
        data["campaign_id"] = getattr(campaign, "id", None)
        campaign_type = getattr(campaign, "campaign_type", None)
        data["campaign_type"] = getattr(campaign_type, "value", campaign_type)
        data["campaign_name"] = getattr(campaign, "name", None)

    data.update(payload or {})
    return {key: value for key, value in data.items() if value is not None}
