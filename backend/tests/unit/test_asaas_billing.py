import hashlib
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request

from app.config import settings
from app.routes.asaas_billing_routes import (
    SubscriptionCreateRequest,
    _validate_webhook_token,
    subscribe,
)
from app.billing_models import BillingContractAcceptance
from app.services.asaas_billing_service import (
    AsaasBillingError,
    AsaasClient,
    _first_due_date,
    apply_payment_event,
    create_subscription,
)
from app.services.billing_contract_service import (
    CONTRACT_DOCUMENT_SHA256,
    CONTRACT_VERSION,
    ContractAcceptanceContext,
    build_contract_acceptance,
    validate_contract_acceptance,
)
from app.services.plan_catalog import get_plan


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

    result = apply_payment_event(_FakeSession(tenant), "PAYMENT_CONFIRMED", payment)

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


def test_aceite_contratual_e_obrigatorio_e_versionado():
    with pytest.raises(ValueError, match="Confirme o aceite"):
        validate_contract_acceptance(
            accepted=False,
            contract_version=CONTRACT_VERSION,
            contract_document_sha256=CONTRACT_DOCUMENT_SHA256,
        )

    with pytest.raises(RuntimeError, match="contrato foi atualizado"):
        validate_contract_acceptance(
            accepted=True,
            contract_version="versao-antiga",
            contract_document_sha256=CONTRACT_DOCUMENT_SHA256,
        )


def test_rota_de_assinatura_recusa_requisicao_sem_aceite():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/billing/asaas/subscriptions",
            "headers": [],
        }
    )
    admin = SimpleNamespace(is_admin=True)

    with pytest.raises(HTTPException, match="Confirme o aceite") as exc_info:
        subscribe(
            SubscriptionCreateRequest(plan_code="pet-start"),
            request,
            auth=(admin, "4c48c5c9-bf40-49a8-b323-7b8fb8b3dc8f"),
            db=object(),
        )

    assert exc_info.value.status_code == 422


def test_snapshot_do_aceite_tem_hash_e_dados_comerciais():
    tenant = SimpleNamespace(
        id="4c48c5c9-bf40-49a8-b323-7b8fb8b3dc8f",
        name="Clinica Teste",
        razao_social="Clinica Teste LTDA",
        cnpj="12.345.678/0001-90",
    )
    user = SimpleNamespace(
        id=42,
        nome="Administrador Teste",
        email="admin@example.com",
        cpf_cnpj=None,
    )

    acceptance = build_contract_acceptance(
        tenant=tenant,
        current_user=user,
        plan=get_plan("pet-start"),
        billing_type="UNDEFINED",
        first_due_date=date(2026, 9, 13),
        provider_environment="sandbox",
        provider_subscription_id="sub_test",
        context=ContractAcceptanceContext(
            ip_address="203.0.113.10",
            user_agent="pytest",
            client_timezone="America/Sao_Paulo",
            request_id="request-test",
        ),
    )

    assert acceptance.contract_version == CONTRACT_VERSION
    assert acceptance.document_sha256 == CONTRACT_DOCUMENT_SHA256
    assert acceptance.plan_code == "pet-start"
    assert acceptance.price_cents == 4_990
    assert acceptance.first_due_date == date(2026, 9, 13)
    assert (
        acceptance.snapshot_sha256
        == hashlib.sha256(acceptance.snapshot_json.encode("utf-8")).hexdigest()
    )


class _SubscriptionSession:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def refresh(self, _value):
        return None


class _AsaasSubscriptionClient:
    environment = "sandbox"

    def request(self, method, path, *, payload=None, params=None):
        if method == "POST" and path == "/subscriptions":
            assert payload["nextDueDate"] == "2026-09-13"
            return {"id": "sub_test"}
        if method == "GET" and path == "/subscriptions/sub_test/payments":
            return {
                "data": [
                    {
                        "id": "pay_test",
                        "status": "PENDING",
                        "billingType": "UNDEFINED",
                        "dueDate": "2026-09-13",
                        "invoiceUrl": "https://sandbox.asaas.com/i/test",
                    }
                ]
            }
        raise AssertionError((method, path, payload, params))


def test_criacao_da_assinatura_persiste_comprovante_do_aceite(monkeypatch):
    tenant = _tenant(
        id="4c48c5c9-bf40-49a8-b323-7b8fb8b3dc8f",
        name="Clinica Teste",
        razao_social="Clinica Teste LTDA",
        cnpj="12.345.678/0001-90",
        email="financeiro@example.com",
        telefone=None,
        plan="pet-start",
        billing_status="trial",
        trial_ends_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
        billing_provider_environment="sandbox",
        billing_provider_customer_id="cus_test",
    )
    user = SimpleNamespace(
        id=42,
        nome="Administrador Teste",
        email="admin@example.com",
        cpf_cnpj=None,
        telefone=None,
    )
    db = _SubscriptionSession()
    monkeypatch.setattr(
        "app.services.asaas_billing_service.AsaasClient",
        _AsaasSubscriptionClient,
    )

    result = create_subscription(
        db,
        tenant=tenant,
        current_user=user,
        plan_code="pet-start",
        billing_type="UNDEFINED",
        acceptance_context=ContractAcceptanceContext(
            ip_address="203.0.113.10",
            user_agent="pytest",
            client_timezone="America/Sao_Paulo",
            request_id="request-test",
        ),
    )

    acceptance = next(
        item for item in db.added if isinstance(item, BillingContractAcceptance)
    )
    assert db.commits == 1
    assert acceptance.provider_subscription_id == "sub_test"
    assert result["contract_acceptance"]["acceptance_id"] == acceptance.acceptance_id
