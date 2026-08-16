import asyncio
from types import SimpleNamespace

from app.ai.llm_client import LLMClient


def test_gpt56_chat_completion_uses_supported_parameters():
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="consulta_produto",
                            role="assistant",
                            tool_calls=None,
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=SimpleNamespace(
                    prompt_tokens=5,
                    completion_tokens=2,
                    total_tokens=7,
                ),
            )

    client = LLMClient("test-key", default_model="gpt-5.6-terra")
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    result = asyncio.run(
        client.chat_completion(
            messages=[{"role": "user", "content": "Tem ração de 3 kg?"}],
            temperature=0.3,
            max_tokens=150,
        )
    )

    assert result["model_used"] == "gpt-5.6-terra"
    assert captured["max_completion_tokens"] == 150
    assert captured["reasoning_effort"] == "none"
    assert "max_tokens" not in captured
    assert "temperature" not in captured


def test_legacy_chat_model_keeps_temperature_and_max_tokens():
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="ok",
                            role="assistant",
                            tool_calls=None,
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=SimpleNamespace(
                    prompt_tokens=1,
                    completion_tokens=1,
                    total_tokens=2,
                ),
            )

    client = LLMClient("test-key", default_model="gpt-4o-mini")
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    asyncio.run(
        client.chat_completion(
            messages=[{"role": "user", "content": "oi"}],
            temperature=0.3,
            max_tokens=25,
        )
    )

    assert captured["temperature"] == 0.3
    assert captured["max_tokens"] == 25
    assert "reasoning_effort" not in captured
