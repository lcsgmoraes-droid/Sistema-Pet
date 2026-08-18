import asyncio

from app.whatsapp.conversation_orchestrator import interpret_checkout_message


class _FakeLLM:
    def __init__(self, content):
        self.content = content
        self.calls = []

    async def chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        return {"content": self.content}


def _checkout(stage="delivery_address"):
    return {
        "stage": stage,
        "items": [{"product_id": 5050, "quantity": 2}],
        "preview": {
            "items": [{"name": "Bob Dog Gold 3kg", "quantity": 2}],
            "total": 97.8,
            "payment_methods": [
                {"key": "pix", "name": "PIX"},
                {"key": "dinheiro", "name": "Dinheiro"},
            ],
        },
    }


def test_orchestrator_understands_question_about_registered_address():
    llm = _FakeLLM(
        '{"action":"ask_registered_address","value":null,"confidence":0.98}'
    )
    decision = asyncio.run(
        interpret_checkout_message(
            llm,
            message="Você já não tem meu endereço aí?",
            checkout=_checkout(),
        )
    )

    assert decision.action == "ask_registered_address"
    assert llm.calls[0]["temperature"] == 0


def test_orchestrator_rejects_action_not_allowed_for_current_stage():
    llm = _FakeLLM(
        '{"action":"cash_change","value":100,"confidence":0.99}'
    )
    decision = asyncio.run(
        interpret_checkout_message(
            llm,
            message="troco para 100",
            checkout=_checkout(stage="fulfillment"),
        )
    )

    assert decision is None


def test_orchestrator_accepts_json_inside_code_fence():
    llm = _FakeLLM(
        '```json\n{"action":"ask_total","value":null,"confidence":0.9}\n```'
    )
    decision = asyncio.run(
        interpret_checkout_message(
            llm,
            message="Quanto ficou mesmo?",
            checkout=_checkout(stage="payment"),
        )
    )

    assert decision.action == "ask_total"
