import asyncio
from types import SimpleNamespace

from app.whatsapp.order_checkout import (
    ORDER_CHECKOUT_CONTEXT_KEY,
    build_checkout_summary,
    delivery_address_missing_fields,
    is_final_order_confirmation,
    is_order_checkout_request,
    merge_delivery_address,
    parse_cash_change,
    parse_fulfillment_choice,
    parse_payment_choice,
    parse_quantity_change,
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


def test_checkout_understands_contextual_changes_address_and_cash_change():
    assert parse_quantity_change("Altera pra 2 unidades") == 2
    assert parse_quantity_change("Pode mudar para duas unidades?") == 2
    assert delivery_address_missing_fields("Rua Antônio de Maria, 44") == [
        "bairro",
        "CEP",
    ]
    full_address = merge_delivery_address(
        "Rua Antônio de Maria, 44", "Centro, 19000-000"
    )
    assert delivery_address_missing_fields(full_address) == []
    assert parse_cash_change("não precisa", total=97.8) == {
        "needs_change": False,
        "amount": None,
    }
    assert parse_cash_change("troco pra 100", total=97.8) == {
        "needs_change": True,
        "amount": 100,
        "valid": True,
    }


def test_summary_uses_real_preview_values_and_campaign_benefits():
    checkout = _checkout_context()[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout["fulfillment"] = "pickup"
    checkout["payment_method"] = {"key": "pix", "name": "PIX"}

    summary = build_checkout_summary(checkout)

    assert "Ração Bob Dog Gold 3kg" in summary
    assert "R$ 48,90" in summary
    assert "Cashback da loja: R$ 2,45" in summary
    assert "CONFIRMAR" in summary


def test_summary_suggests_missing_value_for_next_loyalty_stamp():
    checkout = _checkout_context()[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout["fulfillment"] = "pickup"
    checkout["payment_method"] = {"key": "pix", "name": "PIX"}
    checkout["preview"]["benefits"] = []
    checkout["preview"]["loyalty_opportunity"] = {
        "name": "Cartão Fidelidade",
        "missing_amount": 1.1,
    }

    summary = build_checkout_summary(checkout)

    assert "Faltam só R$ 1,10" in summary
    assert "1 carimbo no Cartão Fidelidade" in summary
    assert "Nenhum benefício" not in summary


def test_current_chat_flow_changes_quantity_completes_address_and_asks_change(
    monkeypatch,
):
    processor, sent = _processor_and_messages()
    processor._loyalty_opportunity = lambda _total: {
        "name": "Cartão Fidelidade",
        "missing_amount": 2.2,
    }
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout.update(
        {
            "stage": "confirmation",
            "fulfillment": "delivery",
            "delivery_address": "Rua Antônio de Maria, 44",
            "payment_method": {"key": "dinheiro", "name": "Dinheiro"},
        }
    )

    monkeypatch.setattr(
        "app.whatsapp.processor.fetch_remote_order_preview",
        lambda *_args, **_kwargs: {
            "success": True,
            "customer": {"id": 1, "delivery_address": ""},
            "items": [
                {
                    "product_id": 10,
                    "name": "Ração Bob Dog Gold 3kg",
                    "quantity": 2,
                    "subtotal": 97.8,
                }
            ],
            "total": 97.8,
            "payment_methods": checkout["preview"]["payment_methods"],
            "benefits": [
                {
                    "type": "loyalty",
                    "title": "Cartão Fidelidade",
                    "quantity": 1,
                }
            ],
        },
    )

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="Altera pra 2 unidades",
        )
    )
    assert checkout["items"][0]["quantity"] == 2
    assert checkout["stage"] == "delivery_address"
    assert "alterei para 2 unidade" in sent[-1]["response"]
    assert "falta bairro e CEP" in sent[-1]["response"]

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="Centro, 19000-000",
        )
    )
    assert checkout["stage"] == "cash_change"
    assert "precisar de troco" in sent[-1]["response"]

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="troco pra 100",
        )
    )
    assert checkout["stage"] == "confirmation"
    assert checkout["cash_change_for"] == 100
    assert "Troco para: R$ 100,00" in sent[-1]["response"]
    assert "Cartão Fidelidade: 1 carimbo(s)" in sent[-1]["response"]


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


def test_checkout_explains_stock_conflict_and_transfers_to_human(monkeypatch):
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = {}
    transferred = {}

    async def fake_transfer(**kwargs):
        transferred.update(kwargs)
        return {
            "action": "transferred_to_human",
            "reason": kwargs["reason"],
        }

    processor._transfer_to_human = fake_transfer

    monkeypatch.setattr(
        "app.whatsapp.processor.fetch_remote_order_preview",
        lambda *_args, **_kwargs: {
            "success": False,
            "status_code": 409,
            "detail": "Estoque insuficiente para Racao Special Dog Carne Adultos 15kg.",
        },
    )

    result = asyncio.run(
        processor._start_order_checkout(
            session=session,
            session_context=context,
            items=[
                {
                    "product_id": 5866,
                    "name": "Racao Special Dog Carne Adultos 15kg",
                    "quantity": 3,
                }
            ],
            source="purchase_history",
        )
    )

    assert result["action"] == "transferred_to_human"
    assert transferred["reason"] == "order_preview_rejected"
    assert "Estoque insuficiente" in transferred["customer_message"]
    assert "Nenhuma venda foi lançada" in transferred["customer_message"]
    assert "atendente humano" in transferred["customer_message"]
    assert "problema técnico" not in transferred["customer_message"]
    assert sent == []
