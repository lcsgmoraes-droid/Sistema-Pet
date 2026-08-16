"""Propostas personalizadas com aceite publico e cobranca recorrente no Asaas."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.billing_models import BillingOffer
from app.models import AssinaturaModulo, Tenant, User
from app.services.asaas_billing_service import (
    AsaasBillingError,
    AsaasClient,
    PAYMENT_BLOCK_EVENTS,
    PAYMENT_PAST_DUE_EVENTS,
    PAYMENT_SUCCESS_EVENTS,
    _apply_payment_snapshot,
    _ensure_customer,
    _subscription_payment,
    _trial_active,
)
from app.services.billing_contract_service import (
    ContractAcceptanceContext,
    build_contract_acceptance,
    contract_manifest,
)
from app.services.plan_catalog import PlanDefinition, get_plan
from app.tenancy.context import tenant_context


ALLOWED_BILLING_TYPES = frozenset({"UNDEFINED", "PIX", "BOLETO", "CREDIT_CARD"})
OFFER_REFERENCE_PREFIX = "billing_offer:"
PUBLIC_LINK_TTL_DAYS = 30


class BillingOfferError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _offer_reference(offer_id: str) -> str:
    return f"{OFFER_REFERENCE_PREFIX}{offer_id}"


def offer_id_from_external_reference(value: object) -> str | None:
    reference = str(value or "").strip()
    if not reference.startswith(OFFER_REFERENCE_PREFIX):
        return None
    offer_id = reference.removeprefix(OFFER_REFERENCE_PREFIX).strip()
    return offer_id or None


def _extra_modules(offer: BillingOffer) -> list[str]:
    try:
        parsed = json.loads(offer.extra_modules_json or "[]")
    except (json.JSONDecodeError, TypeError):
        return []
    return sorted({str(item) for item in parsed if isinstance(item, str)})


def _included_modules(offer: BillingOffer) -> list[str]:
    plan = get_plan(offer.plan_code)
    return sorted(set(plan.modules if plan else ()) | set(_extra_modules(offer)))


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def offer_to_public(
    offer: BillingOffer,
    tenant: Tenant,
    *,
    include_checkout: bool = True,
) -> dict[str, Any]:
    plan = get_plan(offer.plan_code)
    return {
        "id": offer.offer_id,
        "tenant": {"name": tenant.razao_social or tenant.name},
        "title": offer.title,
        "plan": {
            "code": offer.plan_code,
            "name": offer.plan_name,
            "base_modules": sorted(plan.modules) if plan else [],
        },
        "extra_modules": _extra_modules(offer),
        "included_modules": _included_modules(offer),
        "price_cents": offer.price_cents,
        "currency": offer.currency,
        "billing_cycle": offer.billing_cycle,
        "billing_type": offer.billing_type,
        "first_due_date": offer.first_due_date.isoformat(),
        "status": offer.status,
        "payment_status": offer.payment_status,
        "expires_at": _iso(offer.expires_at),
        "accepted_at": _iso(offer.accepted_at),
        "representative": {
            "name": offer.representative_name,
            "email": offer.representative_email,
            "role": offer.representative_role,
        }
        if offer.accepted_at
        else None,
        "checkout_url": offer.checkout_url if include_checkout else None,
        "contract": contract_manifest(),
    }


def offer_to_admin(offer: BillingOffer, tenant: Tenant) -> dict[str, Any]:
    result = offer_to_public(offer, tenant, include_checkout=True)
    result.update(
        {
            "tenant_reference": offer.tenant_reference,
            "provider": offer.provider,
            "provider_environment": offer.provider_environment,
            "has_subscription": bool(offer.provider_subscription_id),
            "revoked": bool(offer.revoked),
            "created_at": _iso(offer.created_at),
        }
    )
    return result


def _tenant(db: Session, tenant_reference: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_reference)).first()
    if tenant is None:
        raise BillingOfferError("Empresa não encontrada", status_code=404)
    return tenant


def _validate_modules(plan: PlanDefinition, values: list[str]) -> list[str]:
    from app.routes.modulos_routes import MODULOS_PREMIUM

    normalized = sorted({str(value or "").strip().lower() for value in values if value})
    invalid = [value for value in normalized if value not in MODULOS_PREMIUM]
    if invalid:
        raise BillingOfferError(f"Módulo indisponível: {', '.join(invalid)}")
    return [value for value in normalized if value not in plan.modules]


def create_billing_offer(
    db: Session,
    *,
    tenant_reference: str,
    created_by: User,
    title: str,
    plan_code: str,
    price_cents: int,
    first_due_date: date,
    billing_type: str,
    extra_modules: list[str],
) -> tuple[BillingOffer, str]:
    tenant = _tenant(db, tenant_reference)
    if len(_digits(tenant.cnpj)) not in {11, 14}:
        raise BillingOfferError(
            "Cadastre um CPF ou CNPJ válido na empresa antes de gerar o link."
        )

    plan = get_plan(plan_code)
    if plan is None:
        raise BillingOfferError("Plano-base informado não existe")
    if not 100 <= int(price_cents) <= 10_000_000:
        raise BillingOfferError("Informe uma mensalidade entre R$ 1,00 e R$ 100.000,00")
    if first_due_date < date.today():
        raise BillingOfferError("O primeiro vencimento não pode estar no passado")
    if first_due_date > date.today() + timedelta(days=366):
        raise BillingOfferError("O primeiro vencimento deve ocorrer em até 12 meses")

    normalized_type = str(billing_type or "UNDEFINED").strip().upper()
    if normalized_type not in ALLOWED_BILLING_TYPES:
        raise BillingOfferError("Forma de pagamento indisponivel")
    normalized_modules = _validate_modules(plan, extra_modules)
    normalized_title = str(title or "").strip() or f"CorePet - {plan.name}"
    if len(normalized_title) > 160:
        raise BillingOfferError("O nome da proposta deve ter no maximo 160 caracteres")

    now = datetime.now(timezone.utc)
    (
        db.query(BillingOffer)
        .filter(
            BillingOffer.tenant_reference == str(tenant.id),
            BillingOffer.status == "ready",
            BillingOffer.revoked.is_(False),
        )
        .update({"status": "replaced", "revoked": True}, synchronize_session=False)
    )

    token = secrets.token_urlsafe(32)
    offer = BillingOffer(
        offer_id=str(uuid4()),
        tenant_reference=str(tenant.id),
        token_sha256=_token_hash(token),
        created_by_user_id=created_by.id,
        title=normalized_title,
        plan_code=plan.code,
        plan_name=plan.name,
        price_cents=int(price_cents),
        billing_type=normalized_type,
        first_due_date=first_due_date,
        extra_modules_json=json.dumps(normalized_modules, separators=(",", ":")),
        status="ready",
        expires_at=now + timedelta(days=PUBLIC_LINK_TTL_DAYS),
    )
    db.add(offer)
    db.flush()
    return offer, token


def list_billing_offers(
    db: Session, *, tenant_reference: str, limit: int = 10
) -> list[dict[str, Any]]:
    tenant = _tenant(db, tenant_reference)
    offers = (
        db.query(BillingOffer)
        .filter(BillingOffer.tenant_reference == str(tenant.id))
        .order_by(BillingOffer.created_at.desc())
        .limit(max(1, min(int(limit), 50)))
        .all()
    )
    return [offer_to_admin(offer, tenant) for offer in offers]


def find_offer_by_token(
    db: Session, token: str, *, for_update: bool = False
) -> tuple[BillingOffer, Tenant]:
    clean_token = str(token or "").strip()
    if len(clean_token) < 32:
        raise BillingOfferError("Link de contratação inválido", status_code=404)
    query = db.query(BillingOffer).filter(
        BillingOffer.token_sha256 == _token_hash(clean_token)
    )
    if for_update:
        query = query.with_for_update()
    offer = query.first()
    if offer is None or offer.revoked:
        raise BillingOfferError("Link de contratação inválido", status_code=404)
    expires_at = offer.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        offer.status == "ready"
        and expires_at
        and expires_at < datetime.now(timezone.utc)
    ):
        offer.status = "expired"
        db.flush()
        raise BillingOfferError("Este link de contratação expirou", status_code=410)
    return offer, _tenant(db, offer.tenant_reference)


def _recover_offer_subscription(client: AsaasClient, offer: BillingOffer) -> str | None:
    response = client.request(
        "GET",
        "/subscriptions",
        params={"externalReference": _offer_reference(offer.offer_id), "limit": 1},
    )
    items = response.get("data")
    if not isinstance(items, list) or not items:
        return None
    return str(items[0].get("id") or "").strip() or None


def _create_or_update_subscription(
    client: AsaasClient,
    *,
    offer: BillingOffer,
    tenant: Tenant,
    customer_id: str,
) -> tuple[str, dict[str, Any] | None]:
    subscription_id = offer.provider_subscription_id or _recover_offer_subscription(
        client, offer
    )
    if not subscription_id:
        reusable = (
            tenant.billing_provider_subscription_id
            and tenant.billing_provider_environment == client.environment
            and (tenant.billing_status or "").lower()
            not in {"canceled", "blocked", "refunded"}
        )
        subscription_id = tenant.billing_provider_subscription_id if reusable else None

    payload = {
        "billingType": offer.billing_type,
        "value": float(Decimal(offer.price_cents) / Decimal(100)),
        "description": offer.title,
        "nextDueDate": offer.first_due_date.isoformat(),
        "externalReference": _offer_reference(offer.offer_id),
    }
    if subscription_id:
        client.request("PUT", f"/subscriptions/{subscription_id}", payload=payload)
    else:
        subscription = client.request(
            "POST",
            "/subscriptions",
            payload={
                **payload,
                "customer": customer_id,
                "cycle": "MONTHLY",
                "externalReference": _offer_reference(offer.offer_id),
            },
        )
        subscription_id = str(subscription.get("id") or "").strip()
    if not subscription_id:
        raise AsaasBillingError("O Asaas não retornou a assinatura criada")
    return subscription_id, _subscription_payment(client, subscription_id)


def accept_billing_offer(
    db: Session,
    *,
    offer: BillingOffer,
    tenant: Tenant,
    representative_name: str,
    representative_email: str,
    representative_role: str | None,
    context: ContractAcceptanceContext,
) -> dict[str, Any]:
    if offer.status in {"accepted", "active", "past_due", "blocked"}:
        return offer_to_public(offer, tenant)
    if offer.status != "ready":
        raise BillingOfferError(
            "Esta proposta não está mais disponível", status_code=409
        )

    plan = get_plan(offer.plan_code)
    if plan is None:
        raise BillingOfferError(
            "O plano desta proposta não está mais disponível", status_code=409
        )

    clean_name = str(representative_name or "").strip()
    clean_email = str(representative_email or "").strip().lower()
    clean_role = str(representative_role or "Representante legal").strip()
    if len(clean_name) < 3:
        raise BillingOfferError("Informe o nome completo do representante")
    if "@" not in clean_email:
        raise BillingOfferError("Informe um e-mail valido para o aceite")
    payer = SimpleNamespace(
        id=None,
        nome=clean_name,
        email=clean_email,
        cpf_cnpj=None,
        telefone=None,
    )
    client = AsaasClient()
    customer_id = _ensure_customer(client, tenant, payer)
    subscription_id, payment = _create_or_update_subscription(
        client,
        offer=offer,
        tenant=tenant,
        customer_id=customer_id,
    )

    now = datetime.now(timezone.utc)
    offer.status = "accepted"
    offer.accepted_at = now
    offer.representative_name = clean_name
    offer.representative_email = clean_email
    offer.representative_role = clean_role
    offer.provider_environment = client.environment
    offer.provider_customer_id = customer_id
    offer.provider_subscription_id = subscription_id

    tenant.subscription_source = "asaas"
    tenant.billing_provider_environment = client.environment
    tenant.billing_provider_customer_id = customer_id
    tenant.billing_provider_subscription_id = subscription_id
    tenant.billing_type = offer.billing_type
    _apply_payment_snapshot(tenant, payment)
    offer.provider_payment_id = tenant.billing_provider_payment_id
    offer.payment_status = tenant.billing_payment_status
    offer.checkout_url = tenant.billing_checkout_url
    if not _trial_active(tenant) and tenant.billing_status not in {"active", "trial"}:
        tenant.billing_status = "pending"

    acceptance = build_contract_acceptance(
        tenant=tenant,
        current_user=payer,
        plan=plan,
        billing_type=offer.billing_type,
        first_due_date=offer.first_due_date,
        provider_environment=client.environment,
        provider_subscription_id=subscription_id,
        context=context,
        price_cents=offer.price_cents,
        plan_name=offer.title,
        billing_offer_id=offer.offer_id,
        extra_modules=_extra_modules(offer),
        representative_role=clean_role,
    )
    with tenant_context(tenant.id):
        db.add(acceptance)
        db.commit()
    db.refresh(offer)
    return offer_to_public(offer, tenant)


def _sync_offer_modules(
    db: Session, *, offer: BillingOffer, tenant: Tenant, active: bool
) -> None:
    marker = f"offer:{offer.offer_id}"
    now = datetime.now(timezone.utc)
    desired = set(_extra_modules(offer))
    with tenant_context(tenant.id):
        existing = (
            db.query(AssinaturaModulo)
            .filter(
                AssinaturaModulo.tenant_id == UUID(str(tenant.id)),
                AssinaturaModulo.gateway == "asaas_offer",
            )
            .all()
        )
        by_module = {
            item.modulo: item for item in existing if item.payment_id == marker
        }
        if active:
            for item in existing:
                if item.payment_id != marker and item.status == "ativo":
                    item.status = "substituido"
                    item.data_fim = now
        for module in desired:
            item = by_module.get(module)
            if item is None:
                item = AssinaturaModulo(
                    tenant_id=UUID(str(tenant.id)),
                    modulo=module,
                    gateway="asaas_offer",
                    payment_id=marker,
                    data_inicio=now,
                )
                db.add(item)
            item.status = "ativo" if active else "suspenso"
            item.data_fim = None if active else now
        for module, item in by_module.items():
            if module not in desired:
                item.status = "cancelado"
                item.data_fim = now
        db.flush()


def apply_offer_payment_event(
    db: Session,
    *,
    offer: BillingOffer,
    tenant: Tenant,
    event_type: str,
    payment: dict[str, Any],
) -> None:
    normalized_event = str(event_type or "").strip().upper()
    offer.provider_payment_id = (
        str(payment.get("id") or "") or offer.provider_payment_id
    )
    offer.payment_status = str(payment.get("status") or "") or offer.payment_status
    offer.checkout_url = (
        str(payment.get("invoiceUrl") or payment.get("bankSlipUrl") or "")
        or offer.checkout_url
    )
    if normalized_event in PAYMENT_SUCCESS_EVENTS:
        offer.status = "active"
        tenant.plan = offer.plan_code
        if offer.accepted_at is not None:
            (
                db.query(BillingOffer)
                .filter(
                    BillingOffer.tenant_reference == str(tenant.id),
                    BillingOffer.offer_id != offer.offer_id,
                    BillingOffer.revoked.is_(False),
                    BillingOffer.status.in_(
                        ["accepted", "active", "past_due", "blocked"]
                    ),
                    BillingOffer.accepted_at <= offer.accepted_at,
                )
                .update(
                    {"status": "replaced", "revoked": True},
                    synchronize_session=False,
                )
            )
        _sync_offer_modules(db, offer=offer, tenant=tenant, active=True)
    elif normalized_event in PAYMENT_PAST_DUE_EVENTS:
        offer.status = "past_due"
        _sync_offer_modules(db, offer=offer, tenant=tenant, active=False)
    elif normalized_event in PAYMENT_BLOCK_EVENTS:
        offer.status = "blocked"
        _sync_offer_modules(db, offer=offer, tenant=tenant, active=False)
