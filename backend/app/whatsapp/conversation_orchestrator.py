"""Interpretação contextual e estruturada das mensagens no checkout do WhatsApp."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional


CHECKOUT_ACTIONS = {
    "choose_delivery",
    "choose_pickup",
    "ask_registered_address",
    "provide_address",
    "choose_payment",
    "cash_change",
    "no_cash_change",
    "change_quantity",
    "ask_total",
    "ask_items",
    "ask_benefits",
    "modify_order",
    "confirm",
    "reject",
    "new_request",
    "other",
}

STAGE_ACTIONS = {
    "fulfillment": {"choose_delivery", "choose_pickup"},
    "delivery_address": {"ask_registered_address", "provide_address"},
    "delivery_address_confirmation": {"confirm", "reject", "provide_address"},
    "payment": {"choose_payment"},
    "cash_change": {"cash_change", "no_cash_change"},
    "confirmation": {
        "confirm",
        "reject",
        "change_quantity",
        "modify_order",
        "choose_delivery",
        "choose_pickup",
        "choose_payment",
    },
}

GLOBAL_ACTIONS = {
    "ask_registered_address",
    "ask_total",
    "ask_items",
    "ask_benefits",
    "new_request",
    "other",
}


@dataclass(frozen=True)
class CheckoutDecision:
    action: str
    value: Any = None
    confidence: float = 0.0


def _checkout_prompt_context(checkout: dict[str, Any]) -> dict[str, Any]:
    preview = checkout.get("preview") or {}
    items = preview.get("items") or checkout.get("items") or []
    return {
        "stage": str(checkout.get("stage") or "fulfillment"),
        "items": [
            {
                "name": item.get("name") or item.get("nome") or "Produto",
                "quantity": item.get("quantity") or item.get("quantidade") or 0,
            }
            for item in items[:5]
            if isinstance(item, dict)
        ],
        "total": preview.get("total") or preview.get("subtotal"),
        "fulfillment": checkout.get("fulfillment"),
        "has_delivery_address": bool(
            checkout.get("delivery_address")
            or checkout.get("delivery_address_partial")
            or (preview.get("customer") or {}).get("delivery_address")
        ),
        "payment_methods": [
            {
                "key": method.get("key"),
                "name": method.get("name") or method.get("nome"),
            }
            for method in (preview.get("payment_methods") or [])
            if isinstance(method, dict)
        ],
        "payment_selected": checkout.get("payment_method"),
        "has_benefits": bool(preview.get("benefits")),
        "has_loyalty_opportunity": bool(preview.get("loyalty_opportunity")),
    }


def _parse_json_object(content: Any) -> Optional[dict[str, Any]]:
    text = str(content or "").strip()
    if not text:
        return None
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        text = match.group(0)
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


async def interpret_checkout_message(
    llm_client,
    *,
    message: str,
    checkout: dict[str, Any],
) -> Optional[CheckoutDecision]:
    """Classifica a intenção em uma ação permitida; nunca executa a ação."""
    stage = str(checkout.get("stage") or "fulfillment")
    allowed_actions = sorted(GLOBAL_ACTIONS | STAGE_ACTIONS.get(stage, set()))
    context = _checkout_prompt_context(checkout)
    response = await llm_client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "Você interpreta mensagens de clientes durante um checkout de pet shop. "
                    "Não converse com o cliente e não invente dados. Escolha somente uma ação "
                    "permitida. Perguntas sobre valor, itens, benefícios ou endereço cadastrado "
                    "devem ser classificadas como ask_total, ask_items, ask_benefits ou "
                    "ask_registered_address. Texto que realmente contém um endereço é "
                    "provide_address. Pedido para trocar quantidade é change_quantity e value "
                    "deve ser numérico. Forma de pagamento é choose_payment e value deve ser a "
                    "chave da forma. Se for outro assunto ou um novo produto, use new_request. "
                    "Se não houver certeza, use other. Retorne somente JSON no formato "
                    '{"action":"...","value":null,"confidence":0.0}.'
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "checkout_context": context,
                        "allowed_actions": allowed_actions,
                        "customer_message": message,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0,
        max_tokens=120,
    )
    payload = _parse_json_object(response.get("content"))
    if not payload:
        return None
    action = str(payload.get("action") or "").strip()
    if action not in CHECKOUT_ACTIONS or action not in allowed_actions:
        return None
    try:
        confidence = float(payload.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < 0.65:
        return None
    return CheckoutDecision(
        action=action,
        value=payload.get("value"),
        confidence=min(confidence, 1.0),
    )
