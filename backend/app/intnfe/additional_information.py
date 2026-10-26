"""Informações comerciais existentes na venda para o complemento fiscal.

Não infere pedidos, rastreamento, intermediadores ou tributos a partir do
cliente. Esses dados só aparecem quando foram registrados na própria venda.
"""

import re
import unicodedata


CHANNEL_LABELS = {
    "amazon": "Amazon",
    "mercado_livre": "Mercado Livre",
    "mercadolivre": "Mercado Livre",
    "ml": "Mercado Livre",
    "shopee": "Shopee",
    "tiktok": "TikTok Shop",
    "tiktok_shop": "TikTok Shop",
    "site": "Site",
    "ecommerce": "E-commerce",
    "e_commerce": "E-commerce",
    "instagram": "Instagram",
    "whatsapp": "WhatsApp",
    "ifood": "iFood",
}
LOCAL_CHANNELS = {"", "pdv", "loja_fisica", "fisica"}


def _text(value):
    return " ".join(str(value or "").split())


def _normalized(value):
    plain = unicodedata.normalize("NFKD", _text(value).casefold())
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", plain).strip("_")


def sale_context_lines(venda, *, include_channel=True):
    channel = _normalized(getattr(venda, "canal", None))
    channel_label = CHANNEL_LABELS.get(channel) or _text(getattr(venda, "canal", None))
    store = _text(getattr(venda, "loja_origem", None))
    delivery_notes = _text(getattr(venda, "observacoes_entrega", None))
    lines = []
    if include_channel and channel not in LOCAL_CHANNELS:
        lines.append(f"Canal de venda: {channel_label}")
    if store and _normalized(store) not in LOCAL_CHANNELS | {
        channel,
        _normalized(channel_label),
    }:
        lines.append(f"Loja de origem: {store}")
    if delivery_notes:
        lines.append(f"Observacoes de entrega: {delivery_notes}")
    seen_product_notes = set()
    for item in getattr(venda, "itens", None) or []:
        product = getattr(item, "produto", None)
        notes = _text(getattr(product, "informacoes_adicionais_nf", None))
        if not notes:
            continue
        identifier = _text(
            getattr(product, "codigo", None) or getattr(product, "nome", None)
        )
        key = (identifier, notes)
        if key in seen_product_notes:
            continue
        seen_product_notes.add(key)
        label = (
            f"Dados adicionais do produto {identifier}"
            if identifier
            else "Dados adicionais do produto"
        )
        lines.append(f"{label}: {notes}")
    return lines
