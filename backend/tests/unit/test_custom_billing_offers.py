import hashlib
import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

import app.produtos_models  # noqa: F401 - completa o registry ORM antes dos construtores
from app.billing_models import BillingContractAcceptance, BillingOffer
from app.models import AssinaturaModulo, Tenant
from app.services import billing_offer_service as service
from app.services.asaas_billing_service import apply_payment_event
from app.services.billing_contract_service import ContractAcceptanceContext


TENANT_ID = "4c48c5c9-bf40-49a8-b323-7b8fb8b3dc8f"


def _tenant(**overrides):
    values = {
        "id": TENANT_ID,
        "name": "Pet Shop Cliente",
        "razao_social": "Pet Shop Cliente LTDA",
        "cnpj": "12.345.678/0001-90",
        "email": "financeiro@cliente.test",
        "telefone": None,
        "plan": "pet-start",
        "billing_status": "trial",
        "trial_ends_at": datetime(2026, 8, 30, tzinfo=timezone.utc),
        "subscription_source": "manual",
        "billing_provider_environment": None,
        "billing_provider_customer_id": None,
        "billing_provider_subscription_id": None,
        "billing_provider_payment_id": None,
        "billing_payment_status": None,
        "billing_type": None,
        "billing_next_due_date": None,
        "billing_checkout_url": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _Query:
    def __init__(self, model, *, tenant=None, offers=None, modules=None):
        self.model = model
        self.tenant = tenant
        self.offers = offers or []
        self.modules = modules or []

    def filter(self, *_args):
        return self

    def update(self, *_args, **_kwargs):
        return 0

    def order_by(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def first(self):
        if self.model is Tenant:
            return self.tenant
        if self.model is BillingOffer:
            return self.offers[0] if self.offers else None
        return None

    def all(self):
        if self.model is AssinaturaModulo:
            return self.modules
        if self.model is BillingOffer:
            return self.offers
        return []


class _Session:
    def __init__(self, *, tenant=None, offers=None, modules=None):
        self.tenant = tenant
        self.offers = offers or []
        self.modules = modules or []
        self.added = []
        self.commits = 0
        self.flushes = 0

    def query(self, model):
        return _Query(
            model,
            tenant=self.tenant,
            offers=self.offers,
            modules=self.modules,
        )

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1

    def refresh(self, _value):
        return None


def _offer(**overrides):
    values = {
        "offer_id": "aa48c5c9-bf40-49a8-b323-7b8fb8b3dc90",
        "tenant_reference": TENANT_ID,
        "title": "CorePet - Pet Venda Ativa",
        "plan_code": "pet-venda-ativa",
        "plan_name": "Pet Venda Ativa",
        "price_cents": 49_700,
        "currency": "BRL",
        "billing_cycle": "MONTHLY",
        "billing_type": "UNDEFINED",
        "first_due_date": date(2026, 8, 17),
        "extra_modules_json": '["veterinario"]',
        "status": "ready",
        "payment_status": None,
        "expires_at": datetime(2026, 9, 15, tzinfo=timezone.utc),
        "accepted_at": None,
        "representative_name": None,
        "representative_email": None,
        "representative_role": None,
        "provider": "asaas",
        "provider_environment": None,
        "provider_customer_id": None,
        "provider_subscription_id": None,
        "provider_payment_id": None,
        "checkout_url": None,
        "revoked": False,
        "created_at": datetime(2026, 8, 16, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_cria_proposta_de_300_reais_para_pet_venda_ativa():
    tenant = _tenant()
    db = _Session(tenant=tenant)

    offer, token = service.create_billing_offer(
        db,
        tenant_reference=TENANT_ID,
        created_by=SimpleNamespace(id=9),
        title="CorePet completo sem Vet e Banho e Tosa",
        plan_code="pet-venda-ativa",
        price_cents=30_000,
        first_due_date=date.today(),
        billing_type="UNDEFINED",
        extra_modules=[],
    )

    assert offer.plan_code == "pet-venda-ativa"
    assert offer.price_cents == 30_000
    assert offer.created_by_platform_admin_id == 9
    assert offer.created_by_user_id is None
    assert json.loads(offer.extra_modules_json) == []
    assert offer.token_sha256 == hashlib.sha256(token.encode()).hexdigest()
    assert len(token) >= 32
    assert db.added == [offer]


def test_aceite_publico_preserva_preco_personalizado_e_modulo_extra(monkeypatch):
    tenant = _tenant()
    offer = _offer()
    db = _Session(tenant=tenant, offers=[offer])
    monkeypatch.setattr(
        service,
        "AsaasClient",
        lambda: SimpleNamespace(environment="sandbox"),
    )
    monkeypatch.setattr(service, "_ensure_customer", lambda *_args: "cus_test")
    monkeypatch.setattr(
        service,
        "_create_or_update_subscription",
        lambda *_args, **_kwargs: (
            "sub_test",
            {
                "id": "pay_test",
                "status": "PENDING",
                "billingType": "UNDEFINED",
                "dueDate": "2026-08-17",
                "invoiceUrl": "https://sandbox.asaas.com/i/test",
            },
        ),
    )

    result = service.accept_billing_offer(
        db,
        offer=offer,
        tenant=tenant,
        representative_name="Maria Cliente",
        representative_email="maria@cliente.test",
        representative_role="Proprietaria",
        context=ContractAcceptanceContext(channel="public_offer"),
    )

    acceptance = next(
        item for item in db.added if isinstance(item, BillingContractAcceptance)
    )
    snapshot = json.loads(acceptance.snapshot_json)
    assert acceptance.user_id is None
    assert acceptance.price_cents == 49_700
    assert acceptance.billing_offer_id == offer.offer_id
    assert snapshot["offer"]["extra_modules"] == ["veterinario"]
    assert snapshot["representative"]["role"] == "Proprietaria"
    assert tenant.plan == "pet-start"
    assert result["checkout_url"] == "https://sandbox.asaas.com/i/test"
    assert db.commits == 1


def test_pagamento_confirmado_ativa_plano_e_extra(monkeypatch):
    tenant = _tenant(billing_status="active")
    offer = _offer(status="accepted")
    calls = []
    monkeypatch.setattr(
        service,
        "_sync_offer_modules",
        lambda _db, *, offer, tenant, active: calls.append(
            (offer.offer_id, tenant.id, active)
        ),
    )

    service.apply_offer_payment_event(
        _Session(tenant=tenant, offers=[offer]),
        offer=offer,
        tenant=tenant,
        event_type="PAYMENT_CONFIRMED",
        payment={"id": "pay_test", "status": "CONFIRMED"},
    )

    assert offer.status == "active"
    assert tenant.plan == "pet-venda-ativa"
    assert calls == [(offer.offer_id, tenant.id, True)]


def test_webhook_encontra_proposta_quando_assinatura_existente_mantem_referencia_do_tenant(
    monkeypatch,
):
    tenant = _tenant(
        billing_status="pending",
        billing_provider_subscription_id="sub_reutilizada",
    )
    offer = _offer(
        status="accepted",
        provider_subscription_id="sub_reutilizada",
        accepted_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )
    db = _Session(tenant=tenant, offers=[offer])
    module_calls = []
    monkeypatch.setattr(
        service,
        "_sync_offer_modules",
        lambda _db, *, offer, tenant, active: module_calls.append(active),
    )

    result = apply_payment_event(
        db,
        "PAYMENT_CONFIRMED",
        {
            "id": "pay_reutilizado",
            "subscription": "sub_reutilizada",
            "externalReference": TENANT_ID,
            "status": "CONFIRMED",
        },
    )

    assert result is tenant
    assert offer.status == "active"
    assert tenant.plan == "pet-venda-ativa"
    assert module_calls == [True]


def test_atraso_suspende_apenas_modulos_da_proposta(monkeypatch):
    tenant = _tenant(plan="pet-venda-ativa", billing_status="past_due")
    offer = _offer(status="active")
    calls = []
    monkeypatch.setattr(
        service,
        "_sync_offer_modules",
        lambda _db, *, offer, tenant, active: calls.append(active),
    )

    service.apply_offer_payment_event(
        _Session(tenant=tenant, offers=[offer]),
        offer=offer,
        tenant=tenant,
        event_type="PAYMENT_OVERDUE",
        payment={"id": "pay_test", "status": "OVERDUE"},
    )

    assert offer.status == "past_due"
    assert calls == [False]


def test_sincronizacao_cria_assinatura_do_modulo_veterinario():
    tenant = _tenant()
    offer = _offer()
    db = _Session(tenant=tenant, offers=[offer], modules=[])

    service._sync_offer_modules(db, offer=offer, tenant=tenant, active=True)

    module = next(item for item in db.added if isinstance(item, AssinaturaModulo))
    assert module.modulo == "veterinario"
    assert module.status == "ativo"
    assert module.gateway == "asaas_offer"
    assert module.payment_id == f"offer:{offer.offer_id}"
