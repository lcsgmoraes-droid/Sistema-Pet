"""Versao canonica e comprovantes do contrato de assinatura CorePet."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.billing_models import BillingContractAcceptance
from app.models import Tenant, User
from app.services.plan_catalog import PlanDefinition


CONTRACT_VERSION = "2026-08-14-01"
CONTRACT_DOCUMENT_SHA256 = (
    "827819d29b30bf7b6a14a6c5f659cf5b0da475311dba6845c846570fb15e70a8"
)
TERMS_VERSION = "termos-2026-08-14"
PRIVACY_VERSION = "privacidade-2026-08-14"
CONTRACT_URL = "/contrato-assinatura"
TERMS_URL = "/termos"
PRIVACY_URL = "/privacidade"
ACCEPTANCE_TEXT = (
    "Li e aceito o Resumo da Contratação, o Contrato de Assinatura CorePet, "
    "os Termos de Uso e a Política de Privacidade. Confirmo o plano, o valor, "
    "o ciclo e o primeiro vencimento exibidos e autorizo a cobrança "
    "correspondente. Declaro que tenho poderes para representar a empresa "
    "cadastrada."
)


@dataclass(frozen=True)
class ContractAcceptanceContext:
    ip_address: str | None = None
    user_agent: str | None = None
    client_timezone: str | None = None
    request_id: str | None = None
    channel: str = "web"


def contract_manifest() -> dict[str, str]:
    return {
        "contract_version": CONTRACT_VERSION,
        "contract_document_sha256": CONTRACT_DOCUMENT_SHA256,
        "contract_url": CONTRACT_URL,
        "terms_url": TERMS_URL,
        "privacy_url": PRIVACY_URL,
        "acceptance_text": ACCEPTANCE_TEXT,
    }


def validate_contract_acceptance(
    *, accepted: bool, contract_version: str, contract_document_sha256: str
) -> None:
    if accepted is not True:
        raise ValueError("Confirme o aceite do contrato para continuar.")
    if (
        contract_version != CONTRACT_VERSION
        or contract_document_sha256 != CONTRACT_DOCUMENT_SHA256
    ):
        raise RuntimeError(
            "O contrato foi atualizado. Recarregue a pagina, revise a nova versao e aceite novamente."
        )


def build_contract_acceptance(
    *,
    tenant: Tenant,
    current_user: User,
    plan: PlanDefinition,
    billing_type: str,
    first_due_date: date,
    provider_environment: str,
    provider_subscription_id: str,
    context: ContractAcceptanceContext,
    price_cents: int | None = None,
    plan_name: str | None = None,
    billing_offer_id: str | None = None,
    extra_modules: list[str] | tuple[str, ...] = (),
    representative_role: str = "Administrador",
) -> BillingContractAcceptance:
    accepted_at = datetime.now(timezone.utc)
    acceptance_id = str(uuid4())
    contractor_name = (
        tenant.razao_social or tenant.name or current_user.nome or current_user.email
    ).strip()
    user_email = (current_user.email or "").strip()
    snapshot = {
        "acceptance": {
            "accepted": True,
            "accepted_at": accepted_at.isoformat(),
            "acceptance_id": acceptance_id,
            "text": ACCEPTANCE_TEXT,
        },
        "contracting_party": {
            "name": contractor_name,
            "tax_id": tenant.cnpj or current_user.cpf_cnpj,
            "tenant_id": str(tenant.id),
        },
        "document_bundle": {
            "contract_document_sha256": CONTRACT_DOCUMENT_SHA256,
            "contract_url": CONTRACT_URL,
            "contract_version": CONTRACT_VERSION,
            "privacy_url": PRIVACY_URL,
            "privacy_version": PRIVACY_VERSION,
            "terms_url": TERMS_URL,
            "terms_version": TERMS_VERSION,
        },
        "offer": {
            "billing_cycle": "MONTHLY",
            "billing_type": billing_type,
            "currency": "BRL",
            "first_due_date": first_due_date.isoformat(),
            "plan_code": plan.code,
            "plan_name": plan_name or plan.name,
            "price_cents": price_cents if price_cents is not None else plan.price_cents,
            "billing_offer_id": billing_offer_id,
            "extra_modules": sorted(set(extra_modules)),
            "provider": "asaas",
            "provider_environment": provider_environment,
            "provider_subscription_id": provider_subscription_id,
        },
        "representative": {
            "email": user_email,
            "name": current_user.nome,
            "role": representative_role,
            "user_id": current_user.id,
        },
        "technical_context": {
            "channel": context.channel,
            "client_timezone": context.client_timezone,
            "ip_address": context.ip_address,
            "request_id": context.request_id,
            "user_agent": context.user_agent,
        },
    }
    snapshot_json = json.dumps(
        snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    snapshot_sha256 = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

    return BillingContractAcceptance(
        acceptance_id=acceptance_id,
        tenant_id=UUID(str(tenant.id)),
        user_id=current_user.id,
        user_name=current_user.nome,
        user_email=user_email,
        user_role=representative_role,
        contractor_name=contractor_name,
        contractor_tax_id=tenant.cnpj or current_user.cpf_cnpj,
        contract_version=CONTRACT_VERSION,
        terms_version=TERMS_VERSION,
        privacy_version=PRIVACY_VERSION,
        acceptance_text=ACCEPTANCE_TEXT,
        document_url=CONTRACT_URL,
        terms_url=TERMS_URL,
        privacy_url=PRIVACY_URL,
        document_sha256=CONTRACT_DOCUMENT_SHA256,
        plan_code=plan.code,
        plan_name=plan_name or plan.name,
        price_cents=price_cents if price_cents is not None else plan.price_cents,
        currency="BRL",
        billing_cycle="MONTHLY",
        billing_type=billing_type,
        first_due_date=first_due_date,
        provider="asaas",
        provider_environment=provider_environment,
        provider_subscription_id=provider_subscription_id,
        billing_offer_id=billing_offer_id,
        channel=context.channel,
        request_id=context.request_id,
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        client_timezone=context.client_timezone,
        snapshot_json=snapshot_json,
        snapshot_sha256=snapshot_sha256,
        accepted_at=accepted_at,
    )


def acceptance_to_public(
    acceptance: BillingContractAcceptance | None,
) -> dict[str, str] | None:
    if acceptance is None:
        return None
    return {
        "acceptance_id": acceptance.acceptance_id,
        "accepted_at": acceptance.accepted_at.isoformat(),
        "contract_version": acceptance.contract_version,
        "contract_document_sha256": acceptance.document_sha256,
        "plan_code": acceptance.plan_code,
        "snapshot_sha256": acceptance.snapshot_sha256,
    }


def latest_current_acceptance(
    db: Session, *, tenant_id: object, plan_code: str | None
) -> BillingContractAcceptance | None:
    if not plan_code:
        return None
    return (
        db.query(BillingContractAcceptance)
        .filter(
            BillingContractAcceptance.tenant_id == tenant_id,
            BillingContractAcceptance.plan_code == plan_code,
            BillingContractAcceptance.contract_version == CONTRACT_VERSION,
            BillingContractAcceptance.document_sha256 == CONTRACT_DOCUMENT_SHA256,
        )
        .order_by(
            BillingContractAcceptance.accepted_at.desc(),
            BillingContractAcceptance.id.desc(),
        )
        .first()
    )
