import asyncio
from types import SimpleNamespace

from app.whatsapp.order_checkout import (
    ORDER_CHECKOUT_CONTEXT_KEY,
    build_checkout_summary,
    delivery_address_missing_fields,
    is_final_order_confirmation,
    is_new_conversation_greeting,
    is_order_checkout_request,
    is_registered_address_question,
    merge_delivery_address,
    parse_cash_change,
    parse_fulfillment_choice,
    parse_payment_choice,
    parse_quantity_change,
)
from app.whatsapp.conversation_orchestrator import CheckoutDecision
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
    assert is_final_order_confirmation("Sim, está tudo certo. Pode confirmar") is True
    assert is_final_order_confirmation("Não, quero alterar") is False
    assert is_new_conversation_greeting("Ola boa tarde") is True
    assert is_new_conversation_greeting("boa tarde, quero a Royal") is False
    assert is_registered_address_question("Já tem meu endereço no cadastro não tem?")
    assert not is_registered_address_question("Rua das Flores, 44, Centro, 19000-000")


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


def test_checkout_answers_registered_address_question_without_saving_it_as_address():
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout.update({"stage": "delivery_address", "fulfillment": "delivery"})
    processor._registered_delivery_address = lambda _session, _preview: ""

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="Já tem meu endereço no cadastro não tem?",
        )
    )

    assert checkout["stage"] == "delivery_address"
    assert "delivery_address_partial" not in checkout
    assert "sem endereço de entrega preenchido" in sent[-1]["response"]


def test_contextual_checkout_finds_registered_address_without_exact_keywords():
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout.update({"stage": "delivery_address", "fulfillment": "delivery"})
    processor._registered_delivery_address = lambda _session, _preview: ""

    async def contextual_decision(**_kwargs):
        return CheckoutDecision("ask_registered_address", confidence=0.97)

    processor._checkout_context_decision = contextual_decision
    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="vê onde vocês costumam entregar pra mim",
        )
    )

    assert checkout["stage"] == "delivery_address"
    assert "delivery_address_partial" not in checkout
    assert "sem endereço de entrega preenchido" in sent[-1]["response"]


def test_contextual_checkout_answers_total_without_losing_current_stage():
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout["stage"] = "payment"

    async def contextual_decision(**_kwargs):
        return CheckoutDecision("ask_total", confidence=0.96)

    processor._checkout_context_decision = contextual_decision
    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="antes de escolher, quanto deu tudo?",
        )
    )

    assert checkout["stage"] == "payment"
    assert "R$ 48,90" in sent[-1]["response"]
    assert "forma de pagamento" in sent[-1]["response"]


def test_contextual_checkout_does_not_save_unrelated_text_as_address():
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout.update({"stage": "delivery_address", "fulfillment": "delivery"})

    async def contextual_decision(**_kwargs):
        return CheckoutDecision("other", confidence=0.93)

    processor._checkout_context_decision = contextual_decision
    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="preciso ver isso depois",
        )
    )

    assert "delivery_address_partial" not in checkout
    assert "rua, número, bairro e CEP" in sent[-1]["response"]


def test_checkout_confirms_complete_registered_address_then_moves_to_payment():
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout.update({"stage": "delivery_address", "fulfillment": "delivery"})
    registered = "Rua das Flores, 44, Centro, 19000-000"
    processor._registered_delivery_address = lambda _session, _preview: registered

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="Meu endereço já está cadastrado?",
        )
    )
    assert checkout["stage"] == "delivery_address_confirmation"
    assert registered in sent[-1]["response"]

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="Sim, pode usar esse mesmo",
        )
    )
    assert checkout["delivery_address"] == registered
    assert checkout["stage"] == "payment"
    assert "forma de pagamento" in sent[-1]["response"]


def test_registered_address_falls_back_to_latest_delivery(monkeypatch):
    processor, _sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    preview = {"customer": {"id": 1, "delivery_address": ""}}
    previous_address = "Rua das Palmeiras, 75, Centro, 19000-000"
    monkeypatch.setattr(
        "app.whatsapp.processor.fetch_remote_customer_context",
        lambda *_args, **_kwargs: {
            "success": True,
            "customer": {"id": 1, "delivery_address": ""},
            "latest_delivery": {"delivery_address": previous_address},
        },
    )

    address = processor._registered_delivery_address(session, preview)

    assert address == previous_address


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


def test_contextual_confirmation_never_replaces_explicit_customer_confirmation(
    monkeypatch,
):
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout.update(
        {
            "stage": "confirmation",
            "fulfillment": "pickup",
            "payment_method": {"key": "pix", "name": "PIX"},
        }
    )
    created_calls = []

    async def contextual_decision(**_kwargs):
        return CheckoutDecision("confirm", confidence=0.99)

    processor._checkout_context_decision = contextual_decision
    monkeypatch.setattr(
        "app.whatsapp.processor.create_remote_order",
        lambda *_args, **kwargs: created_calls.append(kwargs),
    )

    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="beleza, entendi",
        )
    )

    assert created_calls == []
    assert ORDER_CHECKOUT_CONTEXT_KEY in context
    assert "diga CONFIRMAR" in sent[-1]["response"]


def test_contextual_fulfillment_understands_natural_delivery_request():
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]

    async def contextual_decision(**_kwargs):
        return CheckoutDecision("choose_delivery", confidence=0.95)

    processor._checkout_context_decision = contextual_decision
    asyncio.run(
        processor._handle_pending_checkout(
            session=session,
            session_context=context,
            checkout=checkout,
            message_content="manda aqui em casa pra mim",
        )
    )

    assert checkout["fulfillment"] == "delivery"
    assert checkout["stage"] == "delivery_address"
    assert "falta bairro e CEP" in sent[-1]["response"]


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


def test_greeting_at_confirmation_starts_clean_service_without_creating_sale(
    monkeypatch,
):
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    checkout = context[ORDER_CHECKOUT_CONTEXT_KEY]
    checkout.update(
        {
            "stage": "confirmation",
            "fulfillment": "pickup",
            "payment_method": {"key": "pix", "name": "PIX"},
        }
    )

    def fail_create(*_args, **_kwargs):
        raise AssertionError("Saudação não pode criar a venda anterior")

    monkeypatch.setattr("app.whatsapp.processor.create_remote_order", fail_create)
    result = asyncio.run(
        processor._handle_order_checkout_flow(
            session=session,
            session_context=context,
            message_content="Ola boa tarde",
        )
    )

    assert result["intent"] == "novo_atendimento_apos_checkout"
    assert ORDER_CHECKOUT_CONTEXT_KEY not in context
    assert "nenhuma venda foi lançada" in sent[-1]["response"]
    assert "Como posso ajudar agora?" in sent[-1]["response"]


def test_new_product_request_replaces_checkout_and_continues_same_message():
    processor, sent = _processor_and_messages()
    session = SimpleNamespace(id="session-test", phone_number="5518997401641")
    context = _checkout_context()
    context[ORDER_CHECKOUT_CONTEXT_KEY]["stage"] = "confirmation"

    result = asyncio.run(
        processor._handle_order_checkout_flow(
            session=session,
            session_context=context,
            message_content="quero a Royal",
        )
    )

    assert result is None
    assert ORDER_CHECKOUT_CONTEXT_KEY not in context
    assert sent == []


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
