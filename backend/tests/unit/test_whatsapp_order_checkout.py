import asyncio
from types import SimpleNamespace

from app.whatsapp.order_checkout import (
    ORDER_CHECKOUT_CONTEXT_KEY,
    build_checkout_summary,
    is_final_order_confirmation,
    is_order_checkout_request,
    parse_fulfillment_choice,
    parse_payment_choice,
)
from app.whatsapp.processor import MessageProcessor


def _checkout_context():
    return {
        ORDER_CHECKOUT_CONTEXT_KEY: {
            "stage": "fulfillment",
            "items": [{"product_id": 10, "quantity": 1}],
            "preview": {
                "customer": {
                    "id": 1,
                    "delivery_address": "Rua das Flores, 100",
                },
                "items": [
                    {
                        "product_id": 10,
                        "name": "Ração Bob Dog Gold 3kg",
                        "quantity": 1,
                        "subtotal": 48.9,
                    }
                ],
                "total": 48.9,
                "payment_methods": [
                    {"key": "pix", "name": "PIX"},
                    {"key": "dinheiro", "name": "Dinheiro"},
                ],
                "benefits": [
                    {
                        "type": "cashback",
                        "title": "Cashback da loja",
                        "value": 2.45,
                    }
                ],
            },
            "idempotency_key": "checkout-test-1234567890",
        }
    }


def _processor_and_messages():
    processor = object.__new__(MessageProcessor)
    processor.tenant_id = "tenant-test"
    processor._save_session_context = lambda _session, _context: None
    sent = []

    async def fake_send_response(**kwargs):
        sent.append(kwargs)
        return {"action": "responded", "intent": kwargs["intent"]}

    processor._send_response = fake_send_response
    return processor, sent


def test_checkout_language_is_deterministic_and_requires_explicit_confirmation():
    methods = [
        {"key": "pix", "name": "PIX"},
        {"key": "credito", "name": "Cartão de crédito"},
    ]

    assert is_order_checkout_request("Pode enviar a compra") is True
    assert is_order_checkout_request("manda foto") is False
    assert parse_fulfillment_choice("1") == "delivery"
    assert parse_fulfillment_choice("retirada") == "pickup"
    assert parse_payment_choice("cartão de crédito", methods)["key"] == "credito"
    assert is_final_order_confirmation("ok") is True
    assert is_final_order_confirmation("CONFIRMAR") is True


def test_summary_uses_real_preview_values_and_campaign_benefits():
    checkout = _checkout_context()[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout["fulfillment"] = "pickup"
    checkout["payment_method"] = {"key": "pix", "name": "PIX"}

    summary = build_checkout_summary(checkout)

    assert "Ração Bob Dog Gold 3kg" in summary
    assert "R$ 48,90" in summary
    assert "Cashback da loja: R$ 2,45" in summary
    assert "CONFIRMAR" in summary


def test_full_checkout_simulation_creates_once_only_after_confirm(monkeypatch):
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    created_calls = []

    def fake_create(*_args, **kwargs):
        created_calls.append(kwargs)
        return {
            "success": True,
            "sale_id": 99,
            "number": "VEN-20260816-0099",
            "status": "aberta",
            "total": 48.9,
            "fulfillment": "pickup",
            "payment_method": {"key": "pix", "name": "PIX"},
            "benefits": checkout["preview"]["benefits"],
        }

    monkeypatch.setattr("app.whatsapp.processor.create_remote_order", fake_create)

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="2",
        )
    )
    assert checkout["stage"] == "payment"
    assert created_calls == []

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="PIX",
        )
    )
    assert checkout["stage"] == "confirmation"
    assert "CONFIRMAR" in sent[-1]["response"]
    assert created_calls == []

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="beleza",
        )
    )
    assert "ainda não foi lançada" in sent[-1]["response"]
    assert created_calls == []

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="CONFIRMAR",
        )
    )
    assert len(created_calls) == 1
    assert ORDER_CHECKOUT_CONTEXT_KEY not in context
    assert "foi lançada no CorePet" in sent[-1]["response"]
    assert "aberta para conferência" in sent[-1]["response"]

    result = asyncio.run(
        processor._handle_order_checkout_flow(
            session=session,
            session_context=context,
            message_content="CONFIRMAR",
        )
    )
    assert result is None
    assert len(created_calls) == 1


def test_checkout_cancellation_never_creates_sale(monkeypatch):
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]

    def fail_create(*_args, **_kwargs):
        raise AssertionError("Venda não pode ser criada após cancelamento")

    monkeypatch.setattr("app.whatsapp.processor.create_remote_order", fail_create)
    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="cancelar",
        )
    )

    assert ORDER_CHECKOUT_CONTEXT_KEY not in context
    assert "Nenhuma venda foi lançada" in sent[-1]["response"]
