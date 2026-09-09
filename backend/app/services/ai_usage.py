"""Coleta somente contadores do fornecedor, nunca prompts/chaves/respostas brutas."""

from typing import Any


def _value(source: Any, key: str, default=None):
    return (
        source.get(key, default)
        if isinstance(source, dict)
        else getattr(source, key, default)
    )


def _count(source: Any, key: str):
    value = _value(source, key)
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else None
    )


def record_openai_usage(target: dict | None, response: Any, *, model: str) -> None:
    if target is None:
        return
    usage = _value(response, "usage")
    target.update(
        {
            "provider": "openai",
            "model": str(_value(response, "model") or model)[:100],
            "response_received": True,
            "provider_cost": None,
            "cost_status": "not_reconciled",
        }
    )
    for name, field in (
        ("provider_response_id", "id"),
        ("provider_request_id", "_request_id"),
    ):
        value = _value(response, field)
        if isinstance(value, str):
            target[name] = value[:160]
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = _count(usage, key)
        if value is not None:
            target[key] = value
    details = _value(usage, "input_tokens_details")
    for key in ("cached_tokens", "image_tokens", "text_tokens"):
        value = _count(details, key)
        if value is not None:
            target[key] = value
    output = _value(response, "output", []) or []
    target["web_search_calls"] = sum(
        _value(item, "type") == "web_search_call" for item in output
    )
