import pytest
from fastapi import HTTPException
from types import SimpleNamespace

from app.api import whatsapp_data_internal_routes as data_routes
from app.api.whatsapp_data_internal_routes import _phone_digits
from app.api.whatsapp_orchestrator_internal_routes import _validate_internal_token


def test_phone_digits_normalizes_whatsapp_number():
    assert _phone_digits("+55 (18) 99740-1641") == "5518997401641"


def test_internal_data_token_is_required(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-correto")

    with pytest.raises(HTTPException) as exc:
        _validate_internal_token("token-errado")

    assert exc.value.status_code == 401


def test_internal_read_only_data_routes_are_registered():
    from app.main import app

    paths = set(app.openapi()["paths"])

    assert "/internal/whatsapp-orchestrator/{tenant_id}/catalog-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/customer-context-data" in paths
    assert "/internal/whatsapp-orchestrator/{tenant_id}/store-context-data" in paths


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
