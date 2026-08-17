"""Reconhecimento e formatação de rascunhos de pedido do WhatsApp."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional
from urllib.parse import urlsplit


ORDER_DRAFT_CONTEXT_KEY = "pending_order_draft"
HISTORY_ITEM_SELECTION_CONTEXT_KEY = "pending_history_item_selection"


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).lower()


def is_generic_reorder_request(message: str) -> bool:
    text = re.sub(r"\s+", " ", _normalize(message)).strip()
    patterns = (
        r"\b(o|a) de sempre\b",
        r"\bpedido de sempre\b",
        r"\bmesmo pedido\b",
        r"\brepetir (o )?pedido\b",
        r"\brepetir (minha |a minha |a |meu |o meu )?(ultima|ultimo) (compra|pedido)\b",
        r"\brepete (o )?pedido\b",
        r"\b(minha|meu) (ultima|ultimo) (compra|pedido)\b",
        r"\bquero novamente\b",
        r"\bpreciso novamente\b",
        r"\bmanda novamente\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def extract_history_quantity_request(message: str) -> Optional[dict[str, Any]]:
    text = re.sub(r"\s+", " ", _normalize(message)).strip(" .!?")
    match = re.fullmatch(
        r"(?:(?:quero|preciso|manda|mandar|vou querer)\s+)?"
        r"(?P<quantity>\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>pacotes?|sacos?|latas?|caixas?|unidades?|saches?)",
        text,
    )
    if not match:
        return None
    return {
        "quantity": float(match.group("quantity").replace(",", ".")),
        "unit": match.group("unit"),
    }


def extract_multi_item_order(message: str) -> list[dict[str, Any]]:
    """Extrai listas explícitas como '1 saco de ração, 2 pacotes de areia'."""
    cleaned = re.sub(
        r"(?i)^\s*(?:quero|preciso|manda|mandar|gostaria de|vou querer|pedido)\s*:?[ ]*",
        "",
        message or "",
    )
    parts = re.split(r"(?:[,;\n]+|\s+e\s+(?=\d+(?:[.,]\d+)?\s))", cleaned)
    items: list[dict[str, Any]] = []
    item_pattern = re.compile(
        r"(?i)^\s*(?P<quantity>\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>x|un(?:idade)?s?|pct|pacotes?|sacos?|latas?|caixas?|sach[eê]s?)?\s+"
        r"(?P<product>.+?)\s*$"
    )
    for part in parts:
        match = item_pattern.match(part.strip())
        if not match:
            continue
        product = re.sub(
            r"(?i)^(?:de|da|do)\s+",
            "",
            match.group("product").strip(),
        )
        product = re.sub(r"(?i)\s+(?:por favor|pfv)$", "", product).strip()
        if len(product) < 2:
            continue
        items.append(
            {
                "quantity": float(match.group("quantity").replace(",", ".")),
                "unit": (match.group("unit") or "x").lower(),
                "name": product,
            }
        )

    return items if len(items) >= 2 else []


def extract_single_item_order(message: str) -> Optional[dict[str, Any]]:
    """Extrai um pedido explícito com quantidade e produto identificável."""
    cleaned = re.sub(
        r"(?i)^\s*(?:quero|preciso|manda|mandar|gostaria de|vou querer|pedido)\s*:?[ ]*",
        "",
        message or "",
    )
    cleaned = re.sub(r"(?i)\s+(?:por favor|pfv)\s*[.!?]*$", "", cleaned).strip()
    match = re.fullmatch(
        r"(?i)\s*(?P<quantity>\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>x|un(?:idade)?s?|pct|pacotes?|sacos?|latas?|caixas?|sach[eê]s?)?\s+"
        r"(?P<product>.+?)\s*",
        cleaned,
    )
    if not match:
        return None

    product = re.sub(
        r"(?i)^(?:de|da|do)\s+",
        "",
        match.group("product").strip(),
    )
    if len(product) < 2 or not re.search(r"[A-Za-zÀ-ÿ]", product):
        return None

    catalog_query = re.sub(r"(?i)\bbobdog\b", "Bob Dog", product)
    catalog_query = re.sub(r"(?i)\bgolde\b", "Gold", catalog_query)
    catalog_query = re.sub(r"(?i)\bde\s+(?=\d+(?:[.,]\d+)?\s*(?:kg|g|ml|l)\b)", "", catalog_query)
    catalog_query = re.sub(r"\s+", " ", catalog_query).strip()

    return {
        "quantity": float(match.group("quantity").replace(",", ".")),
        "unit": (match.group("unit") or "x").lower(),
        "name": product,
        "catalog_query": catalog_query,
    }


def format_quantity(value: Any) -> str:
    quantity = float(value or 0)
    if quantity.is_integer():
        return str(int(quantity))
    return str(quantity).replace(".", ",")


def format_draft_item(item: dict[str, Any]) -> str:
    quantity = format_quantity(item.get("quantity"))
    unit = str(item.get("unit") or "x")
    name = str(item.get("name") or "Item")
    if unit == "x":
        return f"{quantity}x {name}"
    if unit in {"un", "uns", "unidade", "unidades"}:
        return f"{quantity}x {name}"
    return f"{quantity} {unit} de {name}"


def build_order_draft_message(
    items: list[dict[str, Any]],
    *,
    from_history: bool,
    retry: bool = False,
) -> str:
    if retry:
        opening = "Não entendi sua resposta. Confira novamente o pedido:"
    else:
        opening = (
            "Encontrei esta compra no seu histórico:"
            if from_history
            else "Organizei seu pedido assim:"
        )
    lines = [opening]
    lines.extend(
        f"{index}. {format_draft_item(item)}"
        for index, item in enumerate(items, start=1)
    )
    lines.append("Está certo?\n\n1. Sim, está certo\n\n2. Não, quero alterar")
    return "\n\n".join(lines)


def draft_reason_details(items: list[dict[str, Any]], source: str) -> str:
    item_summary = "; ".join(format_draft_item(item) for item in items)
    return f"Rascunho confirmado ({source}): {item_summary}"


def purchase_items_as_draft(purchase: dict) -> list[dict[str, Any]]:
    return [
        {
            "product_id": item.get("product_id"),
            "name": item.get("name") or "Item",
            "quantity": float(item.get("quantity") or 0),
            "unit": "x",
            "unit_price": item.get("unit_price"),
            "image_url": item.get("image_url") or "",
        }
        for item in purchase.get("items") or []
    ]


def is_safe_product_image_url(value: Any) -> bool:
    """Aceita somente imagens externas transmitidas com HTTPS."""
    parsed = urlsplit(str(value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def draft_product_media(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "image_url": str(item.get("image_url") or item.get("imagem_url") or ""),
            "caption": str(item.get("name") or item.get("nome") or "Produto"),
        }
        for item in items
        if is_safe_product_image_url(
            item.get("image_url") or item.get("imagem_url") or ""
        )
    ]
