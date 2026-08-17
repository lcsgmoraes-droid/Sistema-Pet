import asyncio
from datetime import datetime
from types import SimpleNamespace

from app.whatsapp.order_drafts import (
    ORDER_DRAFT_CONTEXT_KEY,
    build_order_draft_message,
    draft_product_media,
    extract_history_quantity_request,
    extract_multi_item_order,
    format_draft_item,
    is_generic_reorder_request,
)
from app.whatsapp.processor import (
    MessageProcessor,
    _customer_benefits_response,
    _delivery_status_response,
)


def test_reorder_phrases_use_history_without_confusing_a_repeated_photo():
    assert is_generic_reorder_request("Quero o de sempre") is True
    assert is_generic_reorder_request("Preciso novamente") is True
    assert is_generic_reorder_request("Repete o pedido") is True
    assert (
        is_generic_reorder_request("Queria repetir minha última compra, qual foi?")
        is True
    )
    assert is_generic_reorder_request("Pode mandar a foto de novo?") is False


def test_short_quantity_request_is_reserved_for_purchase_history():
    assert extract_history_quantity_request("3 pacotes") == {
        "quantity": 3.0,
        "unit": "pacotes",
    }
    assert extract_history_quantity_request("Quero 2 sacos") == {
        "quantity": 2.0,
        "unit": "sacos",
    }
    assert extract_history_quantity_request("2") is None


def test_multi_item_order_is_organized_with_quantities():
    items = extract_multi_item_order(
        "Quero 1 saco de ração Special Dog Gold 15kg, "
        "2 pacotes de areia para gato e 3 sachês de frango por favor"
    )

    assert items == [
        {
            "quantity": 1.0,
            "unit": "saco",
            "name": "ração Special Dog Gold 15kg",
        },
        {
            "quantity": 2.0,
            "unit": "pacotes",
            "name": "areia para gato",
        },
        {
            "quantity": 3.0,
            "unit": "sachês",
            "name": "frango",
        },
    ]
    message = build_order_draft_message(items, from_history=False)
    assert "1 saco de ração Special Dog Gold 15kg" in message
    assert "2 pacotes de areia para gato" in message
    assert "Responda sim" in message


def test_order_item_format_handles_fractional_and_unit_quantities():
    assert (
        format_draft_item({"quantity": 2, "unit": "x", "name": "Sachê"}) == "2x Sachê"
    )
    assert (
        format_draft_item({"quantity": 1.5, "unit": "kg", "name": "Petisco"})
        == "1,5 kg de Petisco"
    )


def test_draft_product_media_accepts_https_and_rejects_clear_text_http():
    media = draft_product_media(
        [
            {"name": "Seguro", "image_url": "https://img.example/seguro.webp"},
            {"name": "Inseguro", "image_url": "http://img.example/inseguro.webp"},
            {"name": "Inválido", "image_url": "sem-url"},
        ]
    )

    assert media == [
        {
            "image_url": "https://img.example/seguro.webp",
            "caption": "Seguro",
        }
    ]


def test_real_delivery_status_response_uses_registered_status():
    response = _delivery_status_response(
        {
            "number": "VEN-123",
            "status": "entregue",
            "delivered_at": datetime(2026, 8, 16, 14, 30),
        }
    )

    assert "VEN-123" in response
    assert "consta como entregue" in response
    assert "16/08/2026 às 14:30" in response
    assert _delivery_status_response({"status": "desconhecido"}) is None


def test_real_benefits_response_uses_brazilian_currency_and_coupon():
    response = _customer_benefits_response(
        {
            "store_credit": 1234.5,
            "cashback": 12.3,
            "loyalty_stamps": 4,
            "coupons": [
                {
                    "code": "CLIENTE10",
                    "type": "percent",
                    "discount_percent": 10,
                    "valid_until": datetime(2026, 8, 31),
                }
            ],
        },
        "Quais meus créditos e voucher?",
    )

    assert "R$ 1.234,50" in response
    assert "R$ 12,30" in response
    assert "CLIENTE10: 10% de desconto" in response
    assert "31/08/2026" in response


class _SessionQuery:
    def __init__(self, session):
        self.session = session

    def get(self, _session_id):
        return self.session


class _FakeDB:
    def __init__(self, session):
        self.session = session

    def query(self, _model):
        return _SessionQuery(self.session)


def test_multi_item_message_creates_draft_before_human_handoff():
    processor = object.__new__(MessageProcessor)
    session = SimpleNamespace(id="session-test", context="{}")
    processor.db = _FakeDB(session)
    saved_context = {}
    sent = {}

    def fake_save_session_context(_session, context):
        saved_context.update(context)

    async def fake_send_response(**kwargs):
        sent.update(kwargs)
        return {"action": "responded", "intent": kwargs["intent"]}

    processor._save_session_context = fake_save_session_context
    processor._send_response = fake_send_response

    result = asyncio.run(
        processor._handle_order_draft_flow(
            "session-test",
            "Quero 1 saco de ração, 2 pacotes de areia",
        )
    )

    assert result["action"] == "responded"
    assert ORDER_DRAFT_CONTEXT_KEY in saved_context
    assert len(saved_context[ORDER_DRAFT_CONTEXT_KEY]["items"]) == 2
    assert "Organizei seu pedido" in sent["response"]


def test_reorder_without_linked_customer_explains_missing_history():
    processor = object.__new__(MessageProcessor)
    session = SimpleNamespace(id="session-test", context="{}")
    processor.db = _FakeDB(session)
    sent = {}
    processor._resolve_customer_for_session = lambda _session: None

    async def fake_send_response(**kwargs):
        sent.update(kwargs)
        return {"action": "responded", "intent": kwargs["intent"]}

    async def fail_transfer(**kwargs):
        raise AssertionError("Não deve transferir quando apenas não existe vínculo")

    processor._send_response = fake_send_response
    processor._transfer_to_human = fail_transfer

    result = asyncio.run(
        processor._handle_order_draft_flow(
            "session-test",
            "Queria repetir minha última compra, qual foi?",
        )
    )

    assert result["action"] == "responded"
    assert "Não encontrei compras vinculadas a este número" in sent["response"]
    assert sent["intent"] == "recompra_cliente_nao_identificado"


def test_confirmed_draft_starts_checkout_instead_of_human_handoff(monkeypatch):
    pending = {
        ORDER_DRAFT_CONTEXT_KEY: {
            "source": "multi_item_message",
            "items": [
                {
                    "product_id": 10,
                    "quantity": 1,
                    "unit": "saco",
                    "name": "Ração",
                },
                {
                    "product_id": 20,
                    "quantity": 2,
                    "unit": "pacotes",
                    "name": "Areia",
                },
            ],
        }
    }
    processor = object.__new__(MessageProcessor)
    processor.tenant_id = "tenant-test"
    session = SimpleNamespace(
        id="session-test", context="ignored", phone_number="5518997401641"
    )
    processor.db = _FakeDB(session)
    sent = {}
    processor._load_session_context = lambda _session: pending
    processor._save_session_context = lambda _session, context: None

    monkeypatch.setattr(
        "app.whatsapp.processor.fetch_remote_order_preview",
        lambda *_args, **_kwargs: {
            "success": True,
            "customer": {"id": 1, "delivery_address": "Rua Teste, 10"},
            "items": [],
            "total": 100,
            "payment_methods": [{"key": "pix", "name": "PIX"}],
            "benefits": [],
        },
    )

    async def fake_send_response(**kwargs):
        sent.update(kwargs)
        return {"action": "responded", "intent": kwargs["intent"]}

    processor._send_response = fake_send_response

    result = asyncio.run(
        processor._handle_order_draft_flow(
            "session-test",
            "Quero repetir o pedido",
        )
    )

    assert result["action"] == "responded"
    assert sent["intent"] == "pedido_escolha_entrega"
    assert "Entrega" in sent["response"]
    assert "Retirada" in sent["response"]
