import asyncio
from types import SimpleNamespace

from app.whatsapp import processor as processor_module
from app.whatsapp.processor import (
    GOLD_CLARIFICATION_MESSAGE,
    MAX_PRODUCT_IMAGES_PER_RESPONSE,
    MessageProcessor,
    _clean_response_image_links,
    _confirmation_reply,
    _build_catalog_response,
    _extract_product_media,
    _gold_catalog_query,
    _gold_brand_matches_product_caption,
    _image_identification_response,
    _image_catalog_query,
    _preserve_explicit_measurements,
    _product_query_from_choice_phrase,
    _gold_brand_from_reply,
    _is_generic_gold_query,
    _replace_generic_gold,
    _recent_purchase_confirmation_message,
    _tool_choice_for_intent,
)


def test_extract_product_media_builds_caption_with_price():
    result = {
        "success": True,
        "data": {
            "produtos": [
                {
                    "nome": "Ração Gold 15kg",
                    "preco": 189.9,
                    "imagem_url": "https://img.example/gold.webp",
                },
                {"nome": "Sem foto", "preco": 10, "imagem_url": ""},
            ]
        },
    }

    assert _extract_product_media(result) == [
        {
            "image_url": "https://img.example/gold.webp",
            "caption": "Ração Gold 15kg — R$ 189,90",
        }
    ]


def test_clean_response_removes_markdown_and_raw_image_urls():
    media = [
        {
            "image_url": "https://img.example/gold.webp",
            "caption": "Ração Gold",
        }
    ]
    response = (
        "Temos esta opção:\n"
        "- ![Imagem](https://img.example/gold.webp)\n"
        "Veja também https://img.example/gold.webp"
    )

    cleaned = _clean_response_image_links(response, media)

    assert "![Imagem]" not in cleaned
    assert "https://" not in cleaned
    assert "Temos esta opção:" in cleaned


def test_generic_gold_query_requires_brand_clarification():
    assert _is_generic_gold_query("Quero uma ração gold de 15kg") is True
    assert _is_generic_gold_query("Quero Special Dog Gold de 15kg") is False
    assert _is_generic_gold_query("Tem Golden de 15kg?") is False
    assert "1. Special Dog Gold" in GOLD_CLARIFICATION_MESSAGE


def test_short_product_choice_becomes_a_catalog_query():
    assert _product_query_from_choice_phrase("Quero a Royal") == "Royal"
    assert _product_query_from_choice_phrase("prefiro Golden") == "Golden"
    assert _product_query_from_choice_phrase("Pode ser a Premier") == "Premier"


def test_operational_choice_does_not_become_a_catalog_query():
    assert _product_query_from_choice_phrase("quero fechar o pedido") is None
    assert _product_query_from_choice_phrase("quero um atendente") is None
    assert _product_query_from_choice_phrase("quero pagar no pix") is None


def test_short_product_choice_forces_catalog_lookup_before_intent_classifier():
    captured = {}
    processor = object.__new__(MessageProcessor)
    processor.config = SimpleNamespace(
        auto_response_enabled=True, bot_name="Assistente"
    )
    processor.ai_enabled = True
    processor.router = SimpleNamespace(
        get_quick_response=lambda *_args, **_kwargs: None
    )

    async def no_order_draft(**_kwargs):
        return None

    async def no_clarification(**kwargs):
        return None, kwargs["message_content"], False

    async def build_context(*_args, **_kwargs):
        return {}

    async def fail_intent_classifier(*_args, **_kwargs):
        raise AssertionError("A escolha de produto não deve chegar ao classificador")

    async def no_transfer(**_kwargs):
        return None

    async def capture_catalog_lookup(**kwargs):
        captured.update(kwargs)
        return {"action": "catalog_lookup"}

    async def no_metric(*_args, **_kwargs):
        return None

    processor._handle_order_draft_flow = no_order_draft
    processor._handle_product_clarification = no_clarification
    processor._build_context = build_context
    processor._detect_intent = fail_intent_classifier
    processor._maybe_transfer_to_human = no_transfer
    processor._process_with_ai = capture_catalog_lookup
    processor._save_detected_intent = lambda *_args, **_kwargs: None
    processor._log_metric = no_metric

    result = asyncio.run(
        processor._process_message_with_context(
            session_id="session-test",
            message_id="message-test",
            message_content="Quero a Royal",
        )
    )

    assert result == {"action": "catalog_lookup"}
    assert captured["message_content"] == "Royal"
    assert captured["intent"] == "consulta_produto"
    assert captured["catalog_query_override"] == "Royal"


def test_gold_reply_resolves_brand_and_preserves_original_details():
    assert _gold_brand_from_reply("1") == "Special Dog Gold"
    assert _gold_brand_from_reply("Golden") == "Golden"
    assert _gold_brand_from_reply("bob dog") == "Bob Dog Gold"
    assert (
        _replace_generic_gold("ração gold de 15kg", "Special Dog Gold")
        == "ração Special Dog Gold de 15kg"
    )


def test_purchase_history_confirmation_understands_yes_and_no():
    assert _confirmation_reply("Sim") is True
    assert _confirmation_reply("É essa") is True
    assert _confirmation_reply("não, é outra") is False
    assert _confirmation_reply("2") is None
    assert "histórico de compras" in _recent_purchase_confirmation_message(
        "Special Dog Gold Adultos 15kg"
    )
    assert (
        _gold_catalog_query("Quero ração Gold de 15 kg", "Special Dog Gold")
        == "Racao Special Dog Gold 15kg"
    )
    assert _gold_catalog_query("Quero Gold de 15 kg", "Golden") == "Golden 15kg"


def test_product_intents_force_catalog_lookup():
    expected = {"type": "function", "function": {"name": "buscar_produto"}}
    assert _tool_choice_for_intent("consulta_produto") == expected
    assert _tool_choice_for_intent("consulta_preco") == expected
    assert _tool_choice_for_intent("consulta_estoque") == expected
    assert _tool_choice_for_intent("saudacao") == "auto"


def test_gold_clarification_uses_catalog_images_with_choice_caption():
    async def fake_execute_function(**kwargs):
        term = kwargs["arguments"]["termo"]
        if "Special Dog" not in term:
            return {"found": 0, "produtos": []}
        return {
            "found": 1,
            "produtos": [
                {
                    "nome": "Ração Special Dog Gold 15kg",
                    "preco": 189.9,
                    "imagem_url": "https://img.example/special-dog.webp",
                }
            ],
        }

    processor = object.__new__(MessageProcessor)
    processor._execute_function = fake_execute_function

    media = asyncio.run(
        processor._get_gold_clarification_media(
            "session-test", "Quero ração Gold de 15kg"
        )
    )

    assert media == [
        {
            "image_url": "https://img.example/special-dog.webp",
            "caption": "1. Special Dog Gold",
        }
    ]


def test_gold_clarification_rejects_image_from_another_brand():
    assert not _gold_brand_matches_product_caption(
        "Special Dog Gold",
        "Racao Bob Dog Gold Premium Special 15kg — R$ 149,90",
    )
    assert _gold_brand_matches_product_caption(
        "Bob Dog Gold",
        "Racao Bob Dog Gold Premium Special 15kg — R$ 149,90",
    )


def test_generic_gold_prefers_recent_customer_purchase_and_photo():
    captured = {}
    session = SimpleNamespace(
        id="session-test",
        cliente_id=42,
        context="{}",
    )

    class FakeQuery:
        def get(self, _session_id):
            return session

    class FakeDB:
        def query(self, *_args):
            return FakeQuery()

        def commit(self):
            pass

    async def fake_get_media(_session_id, product_name):
        return [
            {
                "image_url": "https://img.example/recent.webp",
                "caption": product_name,
            }
        ]

    async def fake_send_response(**kwargs):
        captured.update(kwargs)
        return {"action": "responded"}

    processor = object.__new__(MessageProcessor)
    processor.db = FakeDB()
    processor.tenant_id = "569aa16d-f13c-422f-b23e-a15fa9bbfd68"
    processor._find_recent_gold_purchase = lambda _session, _query: (
        "Special Dog Gold Adultos 15kg"
    )
    processor._get_recent_purchase_media = fake_get_media
    processor._send_response = fake_send_response

    result, _, resolved = asyncio.run(
        processor._handle_product_clarification(
            "session-test", "Quero uma ração Gold de 15kg"
        )
    )

    assert result == {"action": "responded"}
    assert resolved is False
    assert "Special Dog Gold Adultos 15kg" in captured["response"]
    assert captured["product_media"][0]["image_url"].endswith("recent.webp")
    pending = processor._load_session_context(session)["pending_product_clarification"]
    assert pending["type"] == "recent_gold_confirmation"


def test_recent_purchase_yes_resolves_exact_product_without_llm():
    session = SimpleNamespace(
        id="session-test",
        cliente_id=42,
        context=(
            '{"pending_product_clarification": {'
            '"type": "recent_gold_confirmation", '
            '"original_query": "ração Gold 15kg", '
            '"product_name": "Special Dog Gold Adultos 15kg"}}'
        ),
    )

    class FakeQuery:
        def get(self, _session_id):
            return session

    class FakeDB:
        def query(self, *_args):
            return FakeQuery()

        def commit(self):
            pass

    processor = object.__new__(MessageProcessor)
    processor.db = FakeDB()

    result, query, resolved = asyncio.run(
        processor._handle_product_clarification("session-test", "sim")
    )

    assert result is None
    assert query == "Special Dog Gold Adultos 15kg"
    assert resolved is True
    assert "pending_product_clarification" not in processor._load_session_context(
        session
    )


def test_recent_purchase_no_falls_back_to_brand_choices():
    captured = {}
    session = SimpleNamespace(
        id="session-test",
        cliente_id=42,
        context=(
            '{"pending_product_clarification": {'
            '"type": "recent_gold_confirmation", '
            '"original_query": "ração Gold 15kg", '
            '"product_name": "Special Dog Gold Adultos 15kg"}}'
        ),
    )

    class FakeQuery:
        def get(self, _session_id):
            return session

    class FakeDB:
        def query(self, *_args):
            return FakeQuery()

        def commit(self):
            pass

    async def fake_send_brand_clarification(session_id, original_query):
        captured["session_id"] = session_id
        captured["original_query"] = original_query
        return {"action": "responded"}

    processor = object.__new__(MessageProcessor)
    processor.db = FakeDB()
    processor._send_gold_brand_clarification = fake_send_brand_clarification

    result, _, resolved = asyncio.run(
        processor._handle_product_clarification("session-test", "não, outra")
    )

    assert result == {"action": "responded"}
    assert resolved is False
    assert captured["original_query"] == "ração Gold 15kg"
    pending = processor._load_session_context(session)["pending_product_clarification"]
    assert pending["type"] == "gold_brand"


def test_resolved_product_query_bypasses_llm_argument_generation():
    captured = {}

    class FailIfCalledLLM:
        async def chat_completion(self, **_kwargs):
            raise AssertionError("A primeira chamada de IA não deve ocorrer")

    async def fake_handle_product_lookup(**kwargs):
        captured.update(kwargs)
        return {"action": "responded"}

    processor = object.__new__(MessageProcessor)
    processor.llm_client = FailIfCalledLLM()
    processor._handle_deterministic_product_lookup = fake_handle_product_lookup

    result = asyncio.run(
        processor._process_with_ai(
            session_id="session-test",
            message_content="Special Dog Gold 15kg",
            context={},
            intent="consulta_produto",
            catalog_query_override="Special Dog Gold 15kg",
        )
    )

    assert result == {"action": "responded"}
    assert captured["catalog_query"] == "Special Dog Gold 15kg"


def test_deterministic_product_lookup_lists_options_without_assuming_purchase():
    captured = {}

    async def fake_execute_function(**_kwargs):
        return {
            "success": True,
            "data": {
                "produtos": [
                    {
                        "nome": "Special Dog Gold Adultos 15kg",
                        "preco": 189.9,
                        "imagem_url": "https://img.example/gold.webp",
                    },
                    {
                        "nome": "Special Dog Gold Life Adultos 15kg",
                        "preco": 169.9,
                        "imagem_url": "https://img.example/gold-life.webp",
                    },
                ]
            },
        }

    async def fake_send_response(**kwargs):
        captured.update(kwargs)
        return {"action": "responded"}

    processor = object.__new__(MessageProcessor)
    processor._execute_function = fake_execute_function
    processor._send_response = fake_send_response

    result = asyncio.run(
        processor._handle_deterministic_product_lookup(
            "session-test", "Special Dog Gold 15kg", {}
        )
    )

    assert result == {"action": "responded"}
    assert "Encontrei estas opções" in captured["response"]
    assert "Qual delas você quis dizer?" in captured["response"]
    assert "endereço" not in captured["response"]
    assert len(captured["product_media"]) == 2


def test_catalog_response_and_media_share_the_same_three_product_limit():
    result = {
        "data": {
            "produtos": [
                {
                    "nome": f"Produto {index}",
                    "preco": 10.0 + index,
                    "imagem_url": f"https://img.example/{index}.webp",
                }
                for index in range(5)
            ]
        }
    }

    response = _build_catalog_response(result, "ração teste")

    assert "Produto 0" in response
    assert "Produto 2" in response
    assert "Produto 3" not in response


def test_catalog_response_does_not_repeat_question_for_single_product():
    response = _build_catalog_response(
        {
            "produtos": [
                {
                    "nome": "Special Dog Gold Adultos 15kg",
                    "preco": 189.9,
                }
            ]
        },
        "Special Dog Gold Adultos 15kg",
    )

    assert "Encontrei esta opção" in response
    assert "Qual delas" not in response


def test_product_tool_query_preserves_weight_from_customer_message():
    messages = [
        {"role": "system", "content": "Atendimento"},
        {
            "role": "user",
            "content": "[Imagem] Pergunta do cliente: Tem dessa de 15 kg?",
        },
    ]

    assert (
        _preserve_explicit_measurements("Ração Special Dog Gold", messages)
        == "Ração Special Dog Gold 15kg"
    )
    assert (
        _preserve_explicit_measurements("Ração Special Dog Gold 15kg", messages)
        == "Ração Special Dog Gold 15kg"
    )


def test_prompt_does_not_ask_pet_profile_or_add_variation_disclaimer():
    from app.ai.llm_client import PromptBuilder

    prompt = PromptBuilder.build_system_prompt({})

    assert "Sempre pergunte sobre o pet" not in prompt
    assert "consulte disponibilidade atual" not in prompt
    assert "Não peça nome, idade, porte ou raça do pet" in prompt


def test_image_without_question_only_identifies_and_asks_customer_intent():
    response = _image_identification_response(
        "[Imagem recebida sem pergunta]\n"
        "Produto: Ração para cães\nMarca: Special Dog\nLinha: Gold Performance\n"
        "Se precisar de mais informações, não hesite em perguntar!"
    )

    assert "Marca: Special Dog" in response
    assert "Gold Performance" in response
    assert "O que você gostaria de saber" in response
    assert "Se precisar" not in response
    assert "disponível" not in response


def test_image_question_builds_catalog_query_from_brand_line_and_weight():
    content = (
        "[Imagem recebida] Pergunta do cliente: Tem dessa de 15 kg?. "
        "Leitura visual provisoria: Produto: Alimento para cães\n"
        "Marca: Special Dog\nLinha: Gold\nSabor: Carne e Frango\n"
        "Peso/Tamanho: nao identificado"
    )

    assert _image_catalog_query(content) == "Special Dog Gold 15kg"


def test_send_response_sends_text_and_limits_real_image_attachments(monkeypatch):
    calls = []

    async def fake_send_whatsapp_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            id=f"message-{len(calls)}",
            model_used=None,
            tokens_input=None,
            tokens_output=None,
            processing_time_ms=None,
        )

    class FakeDB:
        def commit(self):
            pass

    async def fake_log_metric(_metric_type, _value):
        return None

    monkeypatch.setattr(
        processor_module, "send_whatsapp_message", fake_send_whatsapp_message
    )
    processor = object.__new__(MessageProcessor)
    processor.db = FakeDB()
    processor.tenant_id = "tenant-test"
    processor._log_metric = fake_log_metric
    media = [
        {
            "image_url": f"https://img.example/product-{index}.webp",
            "caption": f"Produto {index}",
        }
        for index in range(MAX_PRODUCT_IMAGES_PER_RESPONSE + 2)
    ]

    result = asyncio.run(
        processor._send_response(
            session_id="session-test",
            response="Opções encontradas.",
            intent="function_executed",
            model_used="test-model",
            tokens_input=10,
            tokens_output=5,
            processing_time_ms=12,
            product_media=media,
        )
    )

    assert calls[0]["message"] == "Opções encontradas."
    assert "image_url" not in calls[0]
    assert len(calls) == 1 + MAX_PRODUCT_IMAGES_PER_RESPONSE
    assert all(call["message_type"] == "image" for call in calls[1:])
    assert result["images_sent"] == MAX_PRODUCT_IMAGES_PER_RESPONSE


def test_function_call_forwards_catalog_images_to_response_sender():
    captured = {}

    class FakeLLMClient:
        async def chat_completion(self, **_kwargs):
            return {
                "content": "Encontrei a ração.",
                "model_used": "test-model",
                "tokens_input": 20,
                "tokens_output": 8,
                "processing_time_ms": 15,
            }

    async def fake_execute_function(**_kwargs):
        return {
            "success": True,
            "data": {
                "produtos": [
                    {
                        "nome": "Ração Gold 15kg",
                        "preco": 189.9,
                        "imagem_url": "https://img.example/gold.webp",
                    }
                ]
            },
        }

    async def fake_send_response(**kwargs):
        captured.update(kwargs)
        return {"action": "responded"}

    processor = object.__new__(MessageProcessor)
    processor.llm_client = FakeLLMClient()
    processor._execute_function = fake_execute_function
    processor._send_response = fake_send_response
    messages = [{"role": "system", "content": "Você é um atendente."}]

    result = asyncio.run(
        processor._handle_function_calls(
            session_id="session-test",
            tool_calls=[
                {
                    "id": "call-1",
                    "function": "buscar_produto",
                    "arguments": {"termo": "ração gold"},
                }
            ],
            context={},
            messages=messages,
            response={
                "content": "",
                "tokens_input": 10,
                "tokens_output": 4,
                "processing_time_ms": 7,
            },
        )
    )

    assert result == {"action": "responded"}
    assert captured["product_media"] == [
        {
            "image_url": "https://img.example/gold.webp",
            "caption": "Ração Gold 15kg — R$ 189,90",
        }
    ]
    assert "Ração Gold 15kg" in captured["response"]
    assert "https://" not in captured["response"]
