import json
from types import SimpleNamespace
from uuid import UUID

from app.services.asaas_billing_service import _ensure_customer


class _RecordingAsaasClient:
    environment = "production"
    tenant_id = "4c48c5c9-bf40-49a8-b323-7b8fb8b3dc8f"

    def __init__(self):
        self.calls = []

    def request(self, method, path, *, payload=None, params=None):
        self.calls.append((method, path, payload, params))
        if method == "GET" and path == "/customers":
            assert params["externalReference"] == self.tenant_id
            return {"data": []}
        if method == "POST" and path == "/customers":
            # Reproduz a serializacao feita pelo httpx antes de enviar ao Asaas.
            json.dumps(payload)
            assert payload["externalReference"] == self.tenant_id
            return {"id": "cus_test"}
        raise AssertionError((method, path, payload, params))


def test_cliente_asaas_serializa_tenant_uuid_como_texto():
    tenant = SimpleNamespace(
        id=UUID("4c48c5c9-bf40-49a8-b323-7b8fb8b3dc8f"),
        name="Pet Shop Teste",
        razao_social="Pet Shop Teste LTDA",
        cnpj="12.345.678/0001-90",
        email="financeiro@petshop.test",
        telefone="11999990000",
        billing_provider_environment=None,
        billing_provider_customer_id=None,
        billing_provider_subscription_id=None,
        billing_provider_payment_id=None,
        billing_payment_status=None,
        billing_checkout_url=None,
        billing_next_due_date=None,
    )
    user = SimpleNamespace(
        nome="Responsavel Teste",
        email="responsavel@petshop.test",
        cpf_cnpj="12345678909",
        telefone="11988880000",
    )
    client = _RecordingAsaasClient()

    customer_id = _ensure_customer(client, tenant, user)

    assert customer_id == "cus_test"
    assert tenant.billing_provider_customer_id == "cus_test"
    assert tenant.billing_provider_environment == "production"
