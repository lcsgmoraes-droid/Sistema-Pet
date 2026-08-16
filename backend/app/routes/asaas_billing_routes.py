"""Assinaturas do CorePet cobradas pelo Asaas."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.billing_models import BillingOffer, BillingWebhookEvent
from app.config import settings
from app.db import get_session
from app.middlewares.request_context import get_request_id
from app.models import Tenant, User
from app.security.client_ip import get_client_ip
from app.services.asaas_billing_service import (
    AsaasBillingError,
    apply_payment_event,
    create_subscription,
    subscription_status,
)
from app.services.billing_contract_service import (
    ContractAcceptanceContext,
    acceptance_to_public,
    contract_manifest,
    latest_current_acceptance,
    validate_contract_acceptance,
)
from app.services.billing_offer_service import (
    BillingOfferError,
    accept_billing_offer,
    find_offer_by_token,
    offer_to_public,
)


router = APIRouter(prefix="/billing/asaas", tags=["Assinaturas Asaas"])


class SubscriptionCreateRequest(BaseModel):
    plan_code: str
    billing_type: Literal["UNDEFINED", "BOLETO", "PIX"] = "UNDEFINED"
    accepted: bool = False
    contract_version: str = ""
    contract_document_sha256: str = ""
    client_timezone: str | None = None


class PublicOfferAcceptRequest(BaseModel):
    representative_name: str = Field(min_length=3, max_length=255)
    representative_email: EmailStr
    representative_role: str | None = Field(default=None, max_length=120)
    accepted: bool = False
    contract_version: str = ""
    contract_document_sha256: str = ""
    client_timezone: str | None = Field(default=None, max_length=80)


def _tenant(db: Session, tenant_id: object) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")
    return tenant


def _require_billing_admin(user: User) -> None:
    if not any(
        bool(getattr(user, flag, False))
        for flag in ("is_admin", "is_superadmin", "is_system_admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente um administrador pode contratar ou alterar o plano.",
        )


@router.get("/status")
def get_billing_status(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = auth
    tenant = _tenant(db, tenant_id)
    result = subscription_status(tenant)
    result["contract"] = contract_manifest()
    result["contract_acceptance"] = acceptance_to_public(
        latest_current_acceptance(db, tenant_id=tenant_id, plan_code=tenant.plan)
    )
    custom_offer = (
        db.query(BillingOffer)
        .filter(
            BillingOffer.tenant_reference == str(tenant.id),
            BillingOffer.status.in_(["accepted", "active", "past_due", "blocked"]),
            BillingOffer.revoked.is_(False),
        )
        .order_by(BillingOffer.accepted_at.desc(), BillingOffer.created_at.desc())
        .first()
    )
    result["custom_offer"] = (
        offer_to_public(custom_offer, tenant, include_checkout=False)
        if custom_offer
        else None
    )
    if custom_offer:
        result["contract_acceptance"] = acceptance_to_public(
            latest_current_acceptance(
                db, tenant_id=tenant_id, plan_code=custom_offer.plan_code
            )
        )
    return result


@router.get("/offers/public/{token}")
def get_public_billing_offer(
    token: str,
    db: Session = Depends(get_session),
):
    try:
        offer, tenant = find_offer_by_token(db, token)
        return offer_to_public(offer, tenant)
    except BillingOfferError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/offers/public/{token}/accept")
def accept_public_billing_offer(
    token: str,
    body: PublicOfferAcceptRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    try:
        validate_contract_acceptance(
            accepted=body.accepted,
            contract_version=body.contract_version,
            contract_document_sha256=body.contract_document_sha256,
        )
        offer, tenant = find_offer_by_token(db, token, for_update=True)
        return accept_billing_offer(
            db,
            offer=offer,
            tenant=tenant,
            representative_name=body.representative_name,
            representative_email=str(body.representative_email),
            representative_role=body.representative_role,
            context=ContractAcceptanceContext(
                ip_address=get_client_ip(request),
                user_agent=(request.headers.get("user-agent") or "")[:1000] or None,
                client_timezone=body.client_timezone,
                request_id=get_request_id(),
                channel="public_offer",
            ),
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BillingOfferError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except AsaasBillingError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/subscriptions")
def subscribe(
    body: SubscriptionCreateRequest,
    request: Request,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_billing_admin(current_user)
    try:
        validate_contract_acceptance(
            accepted=body.accepted,
            contract_version=body.contract_version,
            contract_document_sha256=body.contract_document_sha256,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        return create_subscription(
            db,
            tenant=_tenant(db, tenant_id),
            current_user=current_user,
            plan_code=body.plan_code,
            billing_type=body.billing_type,
            acceptance_context=ContractAcceptanceContext(
                ip_address=get_client_ip(request),
                user_agent=(request.headers.get("user-agent") or "")[:1000] or None,
                client_timezone=(body.client_timezone or "")[:80] or None,
                request_id=get_request_id(),
            ),
        )
    except AsaasBillingError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _validate_webhook_token(received_token: str | None) -> None:
    expected = (
        os.getenv("ASAAS_WEBHOOK_TOKEN") or settings.ASAAS_WEBHOOK_TOKEN or ""
    ).strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook Asaas ainda nao configurado",
        )
    if not received_token or not hmac.compare_digest(received_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de webhook invalido",
        )


@router.post("/webhook")
async def asaas_webhook(
    request: Request,
    asaas_access_token: str | None = Header(default=None, alias="asaas-access-token"),
    db: Session = Depends(get_session),
):
    _validate_webhook_token(asaas_access_token)
    raw_body = await request.body()
    if len(raw_body) > 256 * 1024:
        raise HTTPException(status_code=413, detail="Payload muito grande")
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Payload invalido") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload invalido")

    payload_hash = hashlib.sha256(raw_body).hexdigest()
    event_id = str(payload.get("id") or payload_hash).strip()
    event_type = str(payload.get("event") or "UNKNOWN").strip().upper()
    payment = payload.get("payment")
    if not isinstance(payment, dict):
        payment = {}

    existing = (
        db.query(BillingWebhookEvent)
        .filter(
            BillingWebhookEvent.provider == "asaas",
            BillingWebhookEvent.event_id == event_id,
        )
        .first()
    )
    if existing and existing.processing_status in {"processed", "ignored"}:
        return {"received": True, "duplicate": True}

    if existing:
        event = existing
        event.event_type = event_type
        event.payload_sha256 = payload_hash
        event.processing_status = "processing"
        event.error_message = None
        event.processed_at = None
    else:
        event = BillingWebhookEvent(
            provider="asaas",
            event_id=event_id,
            event_type=event_type,
            tenant_reference=str(payment.get("externalReference") or "") or None,
            provider_payment_id=str(payment.get("id") or "") or None,
            payload_sha256=payload_hash,
            processing_status="processing",
        )
        db.add(event)
    try:
        # Persiste o recibo antes de alterar a assinatura. Assim uma falha posterior
        # continua auditavel e pode ser reenviada pelo Asaas com o mesmo event_id.
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"received": True, "duplicate": True}

    try:
        tenant = apply_payment_event(db, event_type, payment)
        event.processing_status = "processed" if tenant else "ignored"
        if tenant:
            event.tenant_reference = tenant.id
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        failed_event = (
            db.query(BillingWebhookEvent)
            .filter(
                BillingWebhookEvent.provider == "asaas",
                BillingWebhookEvent.event_id == event_id,
            )
            .first()
        )
        if failed_event:
            failed_event.processing_status = "failed"
            failed_event.error_message = str(exc)[:500]
            failed_event.processed_at = datetime.now(timezone.utc)
            db.commit()
        raise HTTPException(
            status_code=500, detail="Falha ao processar webhook"
        ) from exc

    return {"received": True, "duplicate": False}
