"""Integracao de assinaturas CorePet com a API do Asaas."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Tenant, User
from app.services.billing_contract_service import (
    ContractAcceptanceContext,
    acceptance_to_public,
    build_contract_acceptance,
)
from app.services.plan_catalog import PlanDefinition, get_plan


ASAAS_BASE_URLS = {
    "sandbox": "https://api-sandbox.asaas.com/v3",
    "production": "https://api.asaas.com/v3",
}
PAYMENT_SUCCESS_EVENTS = {
    "PAYMENT_CONFIRMED",
    "PAYMENT_RECEIVED",
    "PAYMENT_RECEIVED_IN_CASH",
}
PAYMENT_PAST_DUE_EVENTS = {"PAYMENT_OVERDUE"}
PAYMENT_BLOCK_EVENTS = {
    "PAYMENT_CHARGEBACK_REQUESTED",
    "PAYMENT_CHARGEBACK_DISPUTE",
    "PAYMENT_DELETED",
    "PAYMENT_REFUNDED",
    "PAYMENT_REFUND_IN_PROGRESS",
}


class AsaasBillingError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def asaas_environment() -> str:
    raw = (
        (os.getenv("ASAAS_ENVIRONMENT") or settings.ASAAS_ENVIRONMENT or "sandbox")
        .strip()
        .lower()
    )
    aliases = {"prod": "production", "producao": "production", "test": "sandbox"}
    environment = aliases.get(raw, raw)
    if environment not in ASAAS_BASE_URLS:
        raise AsaasBillingError(
            "ASAAS_ENVIRONMENT deve ser sandbox ou production", status_code=503
        )
    return environment


def asaas_is_configured() -> bool:
    return bool((os.getenv("ASAAS_API_KEY") or settings.ASAAS_API_KEY or "").strip())


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _date_from_asaas(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _error_description(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "O Asaas recusou a operacao"
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if isinstance(errors, list):
        descriptions = [
            str(item.get("description") or "").strip()
            for item in errors
            if isinstance(item, dict)
        ]
        descriptions = [item for item in descriptions if item]
        if descriptions:
            return "; ".join(descriptions[:3])
    return "O Asaas recusou a operacao"


class AsaasClient:
    def __init__(self) -> None:
        self.environment = asaas_environment()
        self.api_key = (
            os.getenv("ASAAS_API_KEY") or settings.ASAAS_API_KEY or ""
        ).strip()
        if not self.api_key:
            raise AsaasBillingError(
                "Integracao Asaas ainda nao configurada", status_code=503
            )
        self.base_url = ASAAS_BASE_URLS[self.environment]

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={
                        "access_token": self.api_key,
                        "accept": "application/json",
                        "content-type": "application/json",
                        "user-agent": "CorePet Billing/1.0",
                    },
                    json=payload,
                    params=params,
                )
        except httpx.RequestError as exc:
            raise AsaasBillingError(
                "Nao foi possivel conectar ao Asaas. Tente novamente."
            ) from exc

        if response.status_code >= 400:
            status_code = 422 if response.status_code in {400, 404, 422} else 502
            raise AsaasBillingError(
                _error_description(response), status_code=status_code
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise AsaasBillingError("Resposta invalida recebida do Asaas") from exc
        return data if isinstance(data, dict) else {}


def _reset_provider_references(tenant: Tenant, environment: str) -> None:
    if tenant.billing_provider_environment in {None, environment}:
        return
    tenant.billing_provider_customer_id = None
    tenant.billing_provider_subscription_id = None
    tenant.billing_provider_payment_id = None
    tenant.billing_payment_status = None
    tenant.billing_checkout_url = None
    tenant.billing_next_due_date = None


def _ensure_customer(client: AsaasClient, tenant: Tenant, current_user: User) -> str:
    _reset_provider_references(tenant, client.environment)
    if tenant.billing_provider_customer_id:
        return tenant.billing_provider_customer_id

    existing = client.request(
        "GET",
        "/customers",
        params={"externalReference": tenant.id, "limit": 1},
    )
    existing_data = existing.get("data")
    if isinstance(existing_data, list) and existing_data:
        customer_id = str(existing_data[0].get("id") or "").strip()
        if customer_id:
            tenant.billing_provider_customer_id = customer_id
            tenant.billing_provider_environment = client.environment
            return customer_id

    cpf_cnpj = _digits(tenant.cnpj or current_user.cpf_cnpj)
    if len(cpf_cnpj) not in {11, 14}:
        raise AsaasBillingError(
            "Cadastre um CPF ou CNPJ valido nos dados da empresa antes de assinar.",
            status_code=422,
        )

    email = (tenant.email or current_user.email or "").strip()
    payload: dict[str, Any] = {
        "name": (
            tenant.razao_social or tenant.name or current_user.nome or email
        ).strip(),
        "cpfCnpj": cpf_cnpj,
        "email": email,
        "externalReference": tenant.id,
        "notificationDisabled": False,
    }
    phone = _digits(tenant.telefone or current_user.telefone)
    if phone:
        payload["mobilePhone"] = phone

    customer = client.request("POST", "/customers", payload=payload)
    customer_id = str(customer.get("id") or "").strip()
    if not customer_id:
        raise AsaasBillingError("O Asaas nao retornou o cliente criado")
    tenant.billing_provider_customer_id = customer_id
    tenant.billing_provider_environment = client.environment
    return customer_id


def _subscription_payment(
    client: AsaasClient, subscription_id: str
) -> dict[str, Any] | None:
    response = client.request(
        "GET", f"/subscriptions/{subscription_id}/payments", params={"limit": 10}
    )
    items = response.get("data")
    if not isinstance(items, list) or not items:
        return None
    return items[0] if isinstance(items[0], dict) else None


def _apply_payment_snapshot(tenant: Tenant, payment: dict[str, Any] | None) -> None:
    if not payment:
        return
    tenant.billing_provider_payment_id = str(payment.get("id") or "") or None
    tenant.billing_payment_status = str(payment.get("status") or "") or None
    tenant.billing_type = str(payment.get("billingType") or "") or tenant.billing_type
    tenant.billing_next_due_date = _date_from_asaas(payment.get("dueDate"))
    tenant.billing_checkout_url = (
        str(payment.get("invoiceUrl") or payment.get("bankSlipUrl") or "") or None
    )


def _trial_active(tenant: Tenant) -> bool:
    ends_at = tenant.trial_ends_at
    if ends_at is None:
        return False
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    return ends_at > datetime.now(timezone.utc)


def _first_due_date(tenant: Tenant) -> date:
    if not _trial_active(tenant) or tenant.trial_ends_at is None:
        return date.today()
    trial_ends_at = tenant.trial_ends_at
    if trial_ends_at.tzinfo is None:
        trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)
    return max(date.today(), trial_ends_at.date())


def create_subscription(
    db: Session,
    *,
    tenant: Tenant,
    current_user: User,
    plan_code: str,
    acceptance_context: ContractAcceptanceContext,
    billing_type: str = "UNDEFINED",
) -> dict[str, Any]:
    plan = get_plan(plan_code)
    if plan is None:
        raise AsaasBillingError("Plano informado nao existe", status_code=422)

    allowed_types = {"UNDEFINED", "BOLETO", "PIX"}
    normalized_type = (billing_type or "UNDEFINED").strip().upper()
    if normalized_type not in allowed_types:
        raise AsaasBillingError("Forma de pagamento indisponivel", status_code=422)

    client = AsaasClient()
    customer_id = _ensure_customer(client, tenant, current_user)
    requested_first_due_date = _first_due_date(tenant)

    reusable = (
        tenant.billing_provider_subscription_id
        and tenant.billing_provider_environment == client.environment
        and (tenant.billing_status or "").lower()
        not in {"canceled", "blocked", "refunded"}
    )
    if reusable:
        subscription_id = tenant.billing_provider_subscription_id
        if tenant.plan != plan.code or tenant.billing_type != normalized_type:
            client.request(
                "PUT",
                f"/subscriptions/{subscription_id}",
                payload={
                    "billingType": normalized_type,
                    "value": float(Decimal(plan.price_cents) / Decimal(100)),
                    "description": f"CorePet - {plan.name}",
                    "externalReference": str(tenant.id),
                },
            )
        payment = _subscription_payment(client, subscription_id)
    else:
        subscription = client.request(
            "POST",
            "/subscriptions",
            payload={
                "customer": customer_id,
                "billingType": normalized_type,
                "nextDueDate": requested_first_due_date.isoformat(),
                "value": float(Decimal(plan.price_cents) / Decimal(100)),
                "cycle": "MONTHLY",
                "description": f"CorePet - {plan.name}",
                "externalReference": tenant.id,
            },
        )
        subscription_id = str(subscription.get("id") or "").strip()
        if not subscription_id:
            raise AsaasBillingError("O Asaas nao retornou a assinatura criada")
        tenant.billing_provider_subscription_id = subscription_id
        payment = _subscription_payment(client, subscription_id)

    tenant.plan = plan.code
    tenant.subscription_source = "asaas"
    tenant.billing_provider_environment = client.environment
    tenant.billing_type = normalized_type
    _apply_payment_snapshot(tenant, payment)
    if not _trial_active(tenant) and tenant.billing_status != "active":
        tenant.billing_status = "pending"

    acceptance = build_contract_acceptance(
        tenant=tenant,
        current_user=current_user,
        plan=plan,
        billing_type=normalized_type,
        first_due_date=tenant.billing_next_due_date or requested_first_due_date,
        provider_environment=client.environment,
        provider_subscription_id=subscription_id,
        context=acceptance_context,
    )
    from app.billing_models import BillingOffer

    (
        db.query(BillingOffer)
        .filter(
            BillingOffer.tenant_reference == str(tenant.id),
            BillingOffer.revoked.is_(False),
            BillingOffer.status.in_(["accepted", "active", "past_due", "blocked"]),
        )
        .update(
            {"status": "replaced", "revoked": True},
            synchronize_session=False,
        )
    )
    db.add(acceptance)
    db.commit()
    db.refresh(tenant)
    result = subscription_status(tenant, plan=plan)
    result["contract_acceptance"] = acceptance_to_public(acceptance)
    return result


def subscription_status(
    tenant: Tenant, *, plan: PlanDefinition | None = None
) -> dict[str, Any]:
    current_plan = plan or get_plan(tenant.plan)
    return {
        "configured": asaas_is_configured(),
        "environment": (
            os.getenv("ASAAS_ENVIRONMENT") or settings.ASAAS_ENVIRONMENT or "sandbox"
        )
        .strip()
        .lower(),
        "provider": "asaas",
        "plan": current_plan.to_public_dict() if current_plan else None,
        "billing_status": tenant.billing_status,
        "payment_status": tenant.billing_payment_status,
        "billing_type": tenant.billing_type,
        "next_due_date": tenant.billing_next_due_date.isoformat()
        if tenant.billing_next_due_date
        else None,
        "checkout_url": tenant.billing_checkout_url,
        "has_customer": bool(tenant.billing_provider_customer_id),
        "has_subscription": bool(tenant.billing_provider_subscription_id),
    }


def apply_payment_event(
    db: Session, event_type: str, payment: dict[str, Any]
) -> Tenant | None:
    from app.billing_models import BillingOffer
    from app.services.billing_offer_service import (
        apply_offer_payment_event,
        offer_id_from_external_reference,
    )

    external_reference = str(payment.get("externalReference") or "").strip()
    payment_id = str(payment.get("id") or "").strip()
    subscription_id = str(payment.get("subscription") or "").strip()
    customer_id = str(payment.get("customer") or "").strip()

    offer = None
    referenced_offer_id = offer_id_from_external_reference(external_reference)
    if referenced_offer_id:
        offer = (
            db.query(BillingOffer)
            .filter(
                BillingOffer.offer_id == referenced_offer_id,
                BillingOffer.revoked.is_(False),
                BillingOffer.status.in_(["accepted", "active", "past_due", "blocked"]),
            )
            .first()
        )

    tenant = None
    if offer is not None:
        tenant = (
            db.query(Tenant).filter(Tenant.id == str(offer.tenant_reference)).first()
        )
    if tenant is None and external_reference and not referenced_offer_id:
        tenant = db.query(Tenant).filter(Tenant.id == external_reference).first()
    if tenant is None and payment_id:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.billing_provider_payment_id == payment_id)
            .first()
        )
    if tenant is None and subscription_id:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.billing_provider_subscription_id == subscription_id)
            .first()
        )
    if tenant is None and customer_id:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.billing_provider_customer_id == customer_id)
            .first()
        )
    if tenant is None:
        return None

    if offer is None and subscription_id:
        offer = (
            db.query(BillingOffer)
            .filter(
                BillingOffer.provider_subscription_id == subscription_id,
                BillingOffer.revoked.is_(False),
                BillingOffer.status.in_(["accepted", "active", "past_due", "blocked"]),
            )
            .order_by(BillingOffer.accepted_at.desc(), BillingOffer.created_at.desc())
            .first()
        )
    if offer is None and payment_id:
        offer = (
            db.query(BillingOffer)
            .filter(
                BillingOffer.provider_payment_id == payment_id,
                BillingOffer.revoked.is_(False),
                BillingOffer.status.in_(["accepted", "active", "past_due", "blocked"]),
            )
            .order_by(BillingOffer.accepted_at.desc(), BillingOffer.created_at.desc())
            .first()
        )

    _apply_payment_snapshot(tenant, payment)
    tenant.subscription_source = "asaas"
    normalized_event = (event_type or "").strip().upper()
    if normalized_event in PAYMENT_SUCCESS_EVENTS:
        tenant.billing_status = "active"
        tenant.subscription_activated_at = datetime.now(timezone.utc)
    elif normalized_event in PAYMENT_PAST_DUE_EVENTS:
        if not _trial_active(tenant):
            tenant.billing_status = "past_due"
    elif normalized_event in PAYMENT_BLOCK_EVENTS:
        if not _trial_active(tenant):
            tenant.billing_status = (
                "refunded" if "REFUND" in normalized_event else "blocked"
            )
    elif tenant.billing_status not in {"active", "trial"}:
        tenant.billing_status = "pending"
    if offer is not None:
        apply_offer_payment_event(
            db,
            offer=offer,
            tenant=tenant,
            event_type=normalized_event,
            payment=payment,
        )
    return tenant
