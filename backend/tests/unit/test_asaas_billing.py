from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config import settings
from app.routes.asaas_billing_routes import _validate_webhook_token
from app.services.asaas_billing_service import (
    AsaasBillingError,
    AsaasClient,
    _first_due_date,
    apply_payment_event,
)


class _TenantQuery:
    def __init__(self, tenant):
        self.tenant = tenant

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.tenant


class _FakeSession:
    def __init__(self, tenant):
        self.tenant = tenant

    def query(self, _model):
        return _TenantQuery(self.tenant)


def _tenant(**overrides):
    values = {
        "id": "tenant-test",
        "billing_status": "pending",
        "trial_ends_at": None,
        "billing_provider_payment_id": None,
        "billing_provider_subscription_id": None,
        "billing_provider_customer_id": None,
        "billing_payment_status": None,
        "billing_type": None,
        "billing_next_due_date": None,
        "billing_checkout_url": None,
        "subscription_source": None,
        "subscription_activated_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_primeiro_vencimento_respeita_os_trinta_dias_de_trial():
    trial_end = datetime.now(timezone.utc) + timedelta(days=30)
    tenant = _tenant(billing_status="trial", trial_ends_at=trial_end)

    assert _first_due_date(tenant) == trial_end.date()


def test_pagamento_confirmado_ativa_assinatura():
    tenant = _tenant()
    payment = {
        "id": "pay_test",
        "externalReference": tenant.id,
        "status": "CONFIRMED",
        "billingType": "BOLETO",
        "dueDate": "2026-08-18",
        "invoiceUrl": "https://sandbox.asaas.com/i/test",
    }

    result = apply_payment_event(
        _FakeSession(tenant), "PAYMENT_CONFIRMED", payment
    )

    assert result is tenant
    assert tenant.billing_status == "active"
    assert tenant.billing_payment_status == "CONFIRMED"
    assert tenant.billing_provider_payment_id == "pay_test"
    assert tenant.subscription_source == "asaas"


def test_atraso_nao_interrompe_trial_ainda_ativo():
    tenant = _tenant(
        billing_status="trial",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=10),
    )

    apply_payment_event(
        _FakeSession(tenant),
        "PAYMENT_OVERDUE",
        {"id": "pay_test", "externalReference": tenant.id, "status": "OVERDUE"},
    )

    assert tenant.billing_status == "trial"


def test_pagamento_antecipado_nao_remove_os_trinta_dias_completos():
    tenant = _tenant(
        billing_status="active",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=10),
    )

    assert _first_due_date(tenant) == tenant.trial_ends_at.date()


def test_webhook_rejeita_token_incorreto(monkeypatch):
    monkeypatch.setenv("ASAAS_WEBHOOK_TOKEN", "token-esperado")
    monkeypatch.setattr(settings, "ASAAS_WEBHOOK_TOKEN", "token-esperado")

    with pytest.raises(HTTPException) as exc_info:
        _validate_webhook_token("token-incorreto")

    assert exc_info.value.status_code == 401


def test_cliente_asaas_separa_sandbox_de_producao(monkeypatch):
    monkeypatch.setenv("ASAAS_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("ASAAS_API_KEY", "chave-de-teste")
    monkeypatch.setattr(settings, "ASAAS_ENVIRONMENT", "sandbox")
    monkeypatch.setattr(settings, "ASAAS_API_KEY", "chave-de-teste")

    client = AsaasClient()

    assert client.base_url == "https://api-sandbox.asaas.com/v3"


def test_cliente_asaas_exige_chave(monkeypatch):
    monkeypatch.setenv("ASAAS_ENVIRONMENT", "sandbox")
    monkeypatch.delenv("ASAAS_API_KEY", raising=False)
    monkeypatch.setattr(settings, "ASAAS_ENVIRONMENT", "sandbox")
    monkeypatch.setattr(settings, "ASAAS_API_KEY", "")

    with pytest.raises(AsaasBillingError) as exc_info:
        AsaasClient()

    assert exc_info.value.status_code == 503
