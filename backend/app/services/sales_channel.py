from typing import Any


CANAL_APP = "app"
CANAL_ECOMMERCE = "ecommerce"
CANAL_LOJA_FISICA = "loja_fisica"

_CHANNEL_ALIASES = {
    "pdv": CANAL_LOJA_FISICA,
    "loja": CANAL_LOJA_FISICA,
    "loja_fisica": CANAL_LOJA_FISICA,
    "balcao": CANAL_LOJA_FISICA,
    "caixa": CANAL_LOJA_FISICA,
    "app": CANAL_APP,
    "aplicativo": CANAL_APP,
    "mobile": CANAL_APP,
    "app_movel": CANAL_APP,
    "ecommerce": CANAL_ECOMMERCE,
    "e_commerce": CANAL_ECOMMERCE,
    "loja_virtual": CANAL_ECOMMERCE,
    "site": CANAL_ECOMMERCE,
    "web": CANAL_ECOMMERCE,
    "app_funcionario": "app_funcionario",
    "banho_tosa": "banho_tosa",
    "banho_e_tosa": "banho_tosa",
    "veterinario": "veterinario",
    "veterinaria": "veterinario",
}


def _channel_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def normalize_sales_channel(value: Any, default: str = CANAL_ECOMMERCE) -> str:
    key = _channel_key(value)
    if not key:
        return default
    return _CHANNEL_ALIASES.get(key, key)


def normalize_online_sales_channel(value: Any, default: str = CANAL_ECOMMERCE) -> str:
    channel = normalize_sales_channel(value, default=default)
    return CANAL_APP if channel == CANAL_APP else CANAL_ECOMMERCE


def is_online_sales_channel(value: Any) -> bool:
    return normalize_sales_channel(value) in {CANAL_APP, CANAL_ECOMMERCE}


def benefit_channel_from_sales_channel(value: Any) -> str:
    channel = normalize_sales_channel(value, default=CANAL_LOJA_FISICA)
    if channel in {CANAL_APP, CANAL_ECOMMERCE, CANAL_LOJA_FISICA, "banho_tosa", "veterinario"}:
        return channel
    return CANAL_LOJA_FISICA


def resolve_checkout_sales_channel(payload: Any, request: Any) -> str:
    headers = getattr(request, "headers", {}) or {}
    candidates = (
        getattr(payload, "origem", None),
        headers.get("X-Client-Channel"),
        headers.get("X-Canal-Venda"),
    )
    for candidate in candidates:
        if str(candidate or "").strip():
            return normalize_online_sales_channel(candidate)
    return normalize_online_sales_channel(None)
