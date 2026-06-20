from __future__ import annotations

from typing import Any

from app.services.sales_channel import normalize_sales_channel


CHANNEL_LABELS = {
    "ecommerce": "Ecommerce",
    "app": "App mobile",
    "loja_fisica": "Loja fisica / ERP",
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "amazon": "Amazon",
}


def channel_label_for(channel: Any) -> str:
    normalized = normalize_sales_channel(channel, default="ecommerce")
    if normalized in CHANNEL_LABELS:
        return CHANNEL_LABELS[normalized]
    return normalized.replace("_", " ").strip().capitalize() or "Ecommerce"
