"""Estado e mensagens do fechamento guiado de pedidos pelo WhatsApp."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

ORDER_CHECKOUT_CONTEXT_KEY = "pending_order_checkout"
ORDER_ITEM_SELECTION_CONTEXT_KEY = "pending_order_item_selection"
CEP_PATTERN = re.compile(r"\b\d{5}-?\d{3}\b")


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def is_order_checkout_request(message: str) -> bool:
    text = _normalize(message)
    if not text or "foto" in text:
        return False
    patterns = (
        r"\b(enviar|envia|mandar|manda) (a |essa |esta )?(compra|pedido)\b",
        r"\b(fechar|fecha|finalizar|finaliza|concluir|conclui) (a |essa |esta )?(compra|pedido)\b",
        r"\b(pode|pode sim) (enviar|mandar|fechar|finalizar)\b",
        r"\bquero (comprar|levar|fechar) (esse|essa|este|esta|isso)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def parse_fulfillment_choice(message: str) -> Optional[str]:
    text = _normalize(message)
    compact_number = re.sub(r"\D", "", text)
    if compact_number == "1" and len(text) <= 10:
        return "delivery"
    if compact_number == "2" and len(text) <= 10:
        return "pickup"
    if re.search(r"\b(entrega|entregar|mandar|enviar)\b", text):
        return "delivery"
    if re.search(r"\b(retirada|retirar|buscar|pegar|loja)\b", text):
        return "pickup"
    return None


def parse_payment_choice(
    message: str, payment_methods: list[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    text = _normalize(message)
    compact_number = re.sub(r"\D", "", text)
    if compact_number and len(text) <= 12:
        index = int(compact_number) - 1
        if 0 <= index < len(payment_methods):
            return payment_methods[index]

    aliases = {
        "pix": ("pix",),
        "dinheiro": ("dinheiro", "especie"),
        "debito": ("debito", "cartao de debito"),
        "credito": ("credito", "cartao de credito"),
    }
    for method in payment_methods:
        key = _normalize(str(method.get("key") or ""))
        name = _normalize(str(method.get("name") or method.get("nome") or ""))
        candidates = aliases.get(key, (key, name))
        if any(
            candidate and re.search(rf"\b{re.escape(candidate)}\b", text)
            for candidate in candidates
        ):
            return method
    return None


def parse_quantity_change(message: str) -> Optional[float]:
    """Entende alterações como 'muda para 2 unidades' no pedido em andamento."""
    text = _normalize(message)
    if not re.search(r"\b(altera|alterar|muda|mudar|troca|trocar|coloca|ajusta)\b", text):
        return None

    number_words = {
        "um": 1.0,
        "uma": 1.0,
        "dois": 2.0,
        "duas": 2.0,
        "tres": 3.0,
        "quatro": 4.0,
        "cinco": 5.0,
        "seis": 6.0,
        "sete": 7.0,
        "oito": 8.0,
        "nove": 9.0,
        "dez": 10.0,
    }
    numeric = re.search(
        r"\b(?:para|pra|por|quantidade(?: de)?|coloca(?:r)?(?: em)?)\s+"
        r"(\d+(?:[.,]\d+)?)\b",
        text,
    )
    if numeric:
        value = float(numeric.group(1).replace(",", "."))
        return value if value > 0 else None

    words = "|".join(number_words)
    word_match = re.search(
        rf"\b(?:para|pra|por|quantidade(?: de)?|coloca(?:r)?(?: em)?)\s+({words})\b",
        text,
    )
    return number_words.get(word_match.group(1)) if word_match else None


def delivery_address_missing_fields(address: str) -> list[str]:
    """Aponta os campos mínimos ausentes sem tentar adivinhar endereço."""
    text = re.sub(r"\s+", " ", address or "").strip(" ,")
    if not text:
        return ["rua", "número", "bairro", "CEP"]

    missing: list[str] = []
    normalized = _normalize(text)
    if not re.search(r"\b(rua|avenida|av|travessa|alameda|estrada|rodovia|praca)\b", normalized):
        missing.append("rua")

    without_cep = CEP_PATTERN.sub("", text)
    if not re.search(r"\b\d{1,6}[a-zA-Z]?\b", without_cep):
        missing.append("número")

    comma_parts = [part.strip() for part in text.split(",") if part.strip()]
    if "bairro" not in normalized and len(comma_parts) < 3:
        missing.append("bairro")
    if not CEP_PATTERN.search(text):
        missing.append("CEP")
    return missing


def merge_delivery_address(existing: str, complement: str) -> str:
    existing_clean = re.sub(r"\s+", " ", existing or "").strip(" ,")
    complement_clean = re.sub(r"\s+", " ", complement or "").strip(" ,")
    if not existing_clean:
        return complement_clean
    if not complement_clean:
        return existing_clean
    if _normalize(complement_clean) in _normalize(existing_clean):
        return existing_clean
    return f"{existing_clean}, {complement_clean}"


def parse_cash_change(message: str, *, total: float) -> Optional[dict[str, Any]]:
    """Interpreta se precisa de troco e, quando informado, para qual valor."""
    text = _normalize(message)
    if re.search(r"\b(nao|sem troco|nao precisa|valor exato|dinheiro contado)\b", text):
        return {"needs_change": False, "amount": None}

    amount_match = re.search(
        r"\b(?:para|pra|de)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\b",
        text,
    )
    if amount_match:
        amount = float(amount_match.group(1).replace(",", "."))
        return {
            "needs_change": True,
            "amount": amount,
            "valid": amount > float(total or 0),
        }
    if re.search(r"\b(sim|preciso|vai precisar|com troco)\b", text):
        return {"needs_change": True, "amount": None}
    return None


def is_final_order_confirmation(message: str) -> bool:
    text = re.sub(r"[^a-z0-9 ]", " ", _normalize(message))
    text = re.sub(r"\s+", " ", text).strip()
    return text in {
        "ok",
        "sim",
        "confirmar",
        "confirmo",
        "ok confirmar",
        "sim confirmar",
        "pode confirmar",
        "pode lancar",
        "pode criar",
        "pode fechar",
    }


def is_order_cancellation(message: str) -> bool:
    text = _normalize(message)
    return text in {
        "cancelar",
        "cancela",
        "cancelar pedido",
        "nao quero mais",
        "desistir",
        "desisti",
    }


def is_new_conversation_greeting(message: str) -> bool:
    """Reconhece uma saudação isolada que inicia um novo atendimento."""
    text = re.sub(r"[^a-z0-9 ]", " ", _normalize(message))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return False
    return bool(
        re.fullmatch(
            r"(?:(?:oi+|ola+|opa|e ai|eai|bom dia|boa tarde|boa noite)\s*)+"
            r"(?:(?:tudo bem|como vai)\s*)?",
            text,
        )
    )


def payment_methods_message(payment_methods: list[dict[str, Any]]) -> str:
    lines = ["Qual será a forma de pagamento?"]
    lines.extend(
        f"{index}. {method.get('name') or method.get('nome') or method.get('key')}"
        for index, method in enumerate(payment_methods, start=1)
    )
    lines.append("Responda com o número ou com o nome da forma de pagamento.")
    return "\n\n".join(lines)


def benefits_lines(benefits: list[dict[str, Any]]) -> list[str]:
    if not benefits:
        return ["- Nenhum benefício adicional previsto nas campanhas ativas."]

    lines: list[str] = []
    for benefit in benefits:
        benefit_type = str(benefit.get("type") or benefit.get("tipo") or "")
        title = str(benefit.get("title") or benefit.get("titulo") or "Benefício")
        if benefit_type == "cashback" and benefit.get("value") is not None:
            description = _format_brl(benefit["value"])
        elif benefit_type in {"loyalty", "fidelidade"}:
            quantity = int(benefit.get("quantity") or benefit.get("quantidade") or 0)
            description = f"{quantity} carimbo(s)"
        elif benefit_type in {"coupon", "cupom"}:
            value = float(benefit.get("value") or benefit.get("valor") or 0)
            percent = float(benefit.get("percent") or benefit.get("percentual") or 0)
            description = (
                _format_brl(value)
                if value > 0
                else f"{percent:g}%"
                if percent > 0
                else "cupom de recompra"
            )
        else:
            description = str(
                benefit.get("description") or benefit.get("descricao") or ""
            )
        lines.append(f"- {title}: {description}".rstrip(": "))
    return lines


def _format_brl(value: Any) -> str:
    formatted = f"{float(value or 0):,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def build_checkout_summary(checkout: dict[str, Any]) -> str:
    preview = checkout.get("preview") or {}
    items = preview.get("items") or checkout.get("items") or []
    lines = ["Confira seu pedido:"]
    for index, item in enumerate(items, start=1):
        quantity = float(item.get("quantity") or 0)
        quantity_text = (
            str(int(quantity))
            if quantity.is_integer()
            else str(quantity).replace(".", ",")
        )
        name = item.get("name") or item.get("nome") or "Item"
        subtotal = item.get("subtotal")
        suffix = f" — {_format_brl(subtotal)}" if subtotal is not None else ""
        lines.append(f"{index}. {quantity_text}x {name}{suffix}")

    fulfillment = checkout.get("fulfillment")
    if fulfillment == "delivery":
        lines.append(
            f"Entrega: {checkout.get('delivery_address') or 'endereço não informado'}"
        )
    else:
        lines.append("Retirada na loja")

    payment = checkout.get("payment_method") or {}
    lines.append(
        f"Pagamento informado: {payment.get('name') or payment.get('nome') or payment.get('key')}"
    )
    if str(payment.get("key") or "").lower() == "dinheiro":
        if checkout.get("cash_change_for") is not None:
            lines.append(f"Troco para: {_format_brl(checkout['cash_change_for'])}")
        elif checkout.get("cash_change_answered"):
            lines.append("Troco: não precisa")
    lines.append(
        f"Total dos produtos: {_format_brl(preview.get('total') or preview.get('subtotal'))}"
    )
    benefits = preview.get("benefits") or []
    opportunity = preview.get("loyalty_opportunity") or {}
    lines.append("Benefícios previstos após a finalização no CorePet:")
    if benefits:
        lines.extend(benefits_lines(benefits))
    elif float(opportunity.get("missing_amount") or 0) > 0:
        lines.append(
            "💡 Faltam só "
            f"{_format_brl(opportunity['missing_amount'])} para você ganhar "
            f"1 carimbo no {opportunity.get('name') or 'Clube Fidelidade'}."
        )
        lines.append(
            "Se quiser aproveitar, peça para adicionar outro produto antes de confirmar."
        )
    else:
        lines.extend(benefits_lines([]))
    lines.append(
        "Se estiver tudo certo, responda OK ou CONFIRMAR. A venda só será lançada depois dessa confirmação."
    )
    return "\n\n".join(lines)
