import pytest
from fastapi import HTTPException
from types import SimpleNamespace

from app.api import whatsapp_data_internal_routes as data_routes
from app.api.whatsapp_data_internal_routes import (
    WhatsAppOrderCreateData,
    _phone_digits,
    _validate_internal_write_token,
)
from app.api.whatsapp_orchestrator_internal_routes import _validate_internal_token
from app.whatsapp.order_checkout_service import register_customer_delivery_address


def test_phone_digits_normalizes_whatsapp_number():
    assert _phone_digits("+55 (18) 99740-1641") == "5518997401641"


def test_internal_data_token_is_required(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")

    with pytest.raises(HTTPException) as exc:
        _validate_internal_token("token-errado")

    assert exc.value.status_code == 401


def test_internal_write_token_is_separate_and_required(monkeypatch):
    monkeypatch.delenv("WHATSAPP_ORCHESTRATOR_WRITE_TOKEN", raising=False)
    with pytest.raises(HTTPException) as missing:
        _validate_internal_write_token(None)
    assert missing.value.status_code == 503

    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_WRITE_TOKEN", "token-escrita")
    with pytest.raises(HTTPException) as invalid:
        _validate_internal_write_token("token-leitura")
    assert invalid.value.status_code == 401


def test_internal_read_only_data_routes_are_registered():
    from app.main import app

    paths = set(app.openapi()["paths"])

    assert "/internal/whatsapp-orchestrator/{tenant_id}/catalog-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/customer-context-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/store-context-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/order-preview-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/order-create-data" in paths


class _FakeQuery:
    def __init__(self, *, rows=None, first=None):
        self.rows = rows or []
        self.first_row = first

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def limit(self, _limit):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.first_row


class _OrderCreateFakeDB:
    def __init__(self):
        self.registry = None
        self.seller = SimpleNamespace(id=7)
        self.sale = SimpleNamespace(
            id=99,
            tipo_retirada=None,
            loja_origem=None,
        )
        self.customer = SimpleNamespace(
            id=10563,
            endereco_entrega=None,
            endereco_entrega_2=None,
            enderecos_adicionais=None,
        )
        self.commits = 0

    def query(self, model):
        model_name = model.__name__
        if model_name == "IdempotencyKey":
            return _FakeQuery(first=self.registry)
        if model_name == "User":
            return _FakeQuery(first=self.seller)
        if model_name == "Venda":
            return _FakeQuery(first=self.sale)
        if model_name == "Cliente":
            return _FakeQuery(first=self.customer)
        return _FakeQuery()

    def add(self, row):
        if row.__class__.__name__ == "IdempotencyKey":
            row.id = 1
            self.registry = row

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None


def test_catalog_data_serializes_real_product_shape(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")
    product = SimpleNamespace(
        id=10,
        nome="Racao Royal Canin 2,5kg",
        codigo="1139",
        codigo_barras="7896181297925",
        preco_venda=149.90,
        estoque_atual=2,
        descricao_curta="",
        imagem_principal="https://img.corepet.com.br/royal.webp",
    )
    db = SimpleNamespace(query=lambda _model: _FakeQuery(rows=[product]))

    result = data_routes.get_catalog_data(
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        query="Royal",
        categoria=None,
        limit=5,
        x_internal_token="token-correto",
        db=db,
    )

    assert result["total"] == 1
    assert result["produtos"][0]["nome"] == "Racao Royal Canin 2,5kg"
    assert result["produtos"][0]["estoque_disponivel"] is True


def test_customer_context_returns_latest_purchase(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")
    customer = SimpleNamespace(
        id=10563,
        nome="Lucas Guerra",
        celular="18997401641",
        telefone="",
        credito=0,
    )
    db = SimpleNamespace(query=lambda _model: _FakeQuery(first=customer))
    monkeypatch.setattr(
        data_routes,
        "_latest_purchase",
        lambda *_args: {
            "number": "202608160001",
            "items": [{"name": "Racao Special Dog Carne Adultos 15kg"}],
        },
    )
    monkeypatch.setattr(data_routes, "_latest_delivery", lambda *_args: None)

    result = data_routes.get_customer_context_data(
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        phone=None,
        customer_id=10563,
        x_internal_token="token-correto",
        db=db,
    )

    assert result["customer"]["name"] == "Lucas Guerra"
    assert result["latest_purchase"]["number"] == "202608160001"


def test_confirmed_order_is_idempotent_and_creates_open_sale_once(monkeypatch):
    from app.vendas import VendaService

    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_WRITE_TOKEN", "token-escrita")
    preview = {
        "success": True,
        "customer": {
            "id": 10563,
            "name": "Lucas Guerra",
            "delivery_address": "Rua Teste, 10",
        },
        "items": [
            {
                "product_id": 10,
                "name": "Racao Bob Dog Gold 3kg",
                "quantity": 1,
                "unit_price": 48.9,
                "subtotal": 48.9,
            }
        ],
        "subtotal": 48.9,
        "total": 48.9,
        "payment_methods": [{"key": "pix", "name": "PIX"}],
        "benefits": [],
        "delivery": {"default_delivery_person_id": 3},
    }
    monkeypatch.setattr(data_routes, "_build_order_preview", lambda *_a, **_k: preview)
    calls = []

    def fake_create_sale(*, payload, user_id, db):
        calls.append({"payload": payload, "user_id": user_id})
        return {"id": 99, "numero_venda": "VEN-0099", "total": 48.9}

    monkeypatch.setattr(VendaService, "criar_venda", fake_create_sale)
    db = _OrderCreateFakeDB()
    data = WhatsAppOrderCreateData(
        phone="5518997401641",
        items=[{"product_id": 10, "quantity": 1}],
        fulfillment="pickup",
        payment_method={"key": "pix", "name": "PIX"},
    )

    first = data_routes.create_order_data(
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        data=data,
        x_internal_token="token-correto",
        x_internal_write_token="token-escrita",
        idempotency_key="checkout-test-1234567890",
        db=db,
    )
    second = data_routes.create_order_data(
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        data=data,
        x_internal_token="token-correto",
        x_internal_write_token="token-escrita",
        idempotency_key="checkout-test-1234567890",
        db=db,
    )

    assert first == second
    assert first["status"] == "aberta"
    assert len(calls) == 1
    assert calls[0]["payload"]["canal"] == "whatsapp"
    assert calls[0]["payload"]["loja_origem"] == "whatsapp"
    assert "Forma de pagamento informada: PIX" in calls[0]["payload"]["observacoes"]
    assert db.sale.tipo_retirada == "proprio"


def test_delivery_order_registers_customer_address(monkeypatch):
    from app.vendas import VendaService

    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_WRITE_TOKEN", "token-escrita")
    preview = {
        "success": True,
        "customer": {"id": 10563, "name": "Lucas Guerra", "delivery_address": ""},
        "items": [
            {
                "product_id": 10,
                "name": "Racao Bob Dog Gold 3kg",
                "quantity": 1,
                "unit_price": 48.9,
                "subtotal": 48.9,
            }
        ],
        "subtotal": 48.9,
        "total": 48.9,
        "payment_methods": [{"key": "pix", "name": "PIX"}],
        "benefits": [],
        "delivery": {"default_delivery_person_id": 3},
    }
    monkeypatch.setattr(data_routes, "_build_order_preview", lambda *_a, **_k: preview)
    monkeypatch.setattr(
        VendaService,
        "criar_venda",
        lambda **_kwargs: {"id": 99, "numero_venda": "VEN-0099", "total": 48.9},
    )
    db = _OrderCreateFakeDB()
    address = "Rua Antonio de Maria, 44, CEP 19024-433, Presidente Prudente"

    result = data_routes.create_order_data(
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        data=WhatsAppOrderCreateData(
            phone="5518997401641",
            items=[{"product_id": 10, "quantity": 1}],
            fulfillment="delivery",
            payment_method={"key": "pix", "name": "PIX"},
            delivery_address=address,
        ),
        x_internal_token="token-correto",
        x_internal_write_token="token-escrita",
        idempotency_key="checkout-delivery-1234567890",
        db=db,
    )

    assert result["delivery_address_registered"] is True
    assert db.customer.endereco_entrega == address


def test_customer_delivery_address_is_deduplicated_and_keeps_previous_addresses():
    customer = SimpleNamespace(
        endereco_entrega="Rua Antiga, 10",
        endereco_entrega_2="Rua Mais Antiga, 20",
        enderecos_adicionais=None,
    )

    assert register_customer_delivery_address(customer, " rua antiga 10 ") is False
    assert register_customer_delivery_address(customer, "Rua Nova, 30") is True
    assert customer.endereco_entrega == "Rua Nova, 30"
    assert customer.endereco_entrega_2 == "Rua Antiga, 10"
    assert customer.enderecos_adicionais == [
        {
            "tipo": "entrega",
            "apelido": "Endereço anterior",
            "endereco_completo": "Rua Mais Antiga, 20",
        }
    ]
