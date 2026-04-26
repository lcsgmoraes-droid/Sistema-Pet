"""
Regras de aplicacao de beneficios por canal/origem da venda.

As flags ficam em Campaign.params["benefit_channels"] para evitar migracao
estrutural: cada campanha pode escolher em quais origens a compra gera
beneficio.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


ALL_BENEFIT_CHANNELS = (
    "loja_fisica",
    "banho_tosa",
    "veterinario",
    "app",
    "ecommerce",
)

DEFAULT_VISIBLE_BENEFIT_CHANNELS = (
    "loja_fisica",
    "app",
    "ecommerce",
)

LEGACY_BLOCKED_SERVICE_CHANNELS = {"banho_tosa", "veterinario"}

PURCHASE_BENEFIT_CAMPAIGN_TYPES = {
    "loyalty_stamp",
    "cashback",
    "quick_repurchase",
}

CHANNEL_ALIASES = {
    "pdv": "loja_fisica",
    "loja": "loja_fisica",
    "loja_fisica": "loja_fisica",
    "loja-fisica": "loja_fisica",
    "balcao": "loja_fisica",
    "balcao_pdv": "loja_fisica",
    "banho_tosa": "banho_tosa",
    "banho-e-tosa": "banho_tosa",
    "banho e tosa": "banho_tosa",
    "bt": "banho_tosa",
    "veterinario": "veterinario",
    "veterinaria": "veterinario",
    "vet": "veterinario",
    "clinica": "veterinario",
    "app": "app",
    "aplicativo": "app",
    "mobile": "app",
    "ecommerce": "ecommerce",
    "e-commerce": "ecommerce",
    "site": "ecommerce",
    "web": "ecommerce",
}


def normalize_benefit_channel(channel: Any) -> str:
    value = str(channel or "loja_fisica").strip().lower().replace(" ", "_")
    return CHANNEL_ALIASES.get(value, value or "loja_fisica")


def campaign_type_value(campaign_type: Any) -> str:
    return str(getattr(campaign_type, "value", campaign_type) or "")


def is_purchase_benefit_campaign(campaign: Any) -> bool:
    return campaign_type_value(getattr(campaign, "campaign_type", campaign)) in PURCHASE_BENEFIT_CAMPAIGN_TYPES


def _extract_scope(params: Mapping[str, Any]) -> Any:
    for key in (
        "benefit_channels",
        "canais_beneficio",
        "aplicar_canais_venda",
        "benefit_channel_scope",
    ):
        if key in params:
            return params.get(key)
    return None


def _channels_from_scope(scope: Any) -> set[str] | None:
    if scope is None:
        return None

    if isinstance(scope, str):
        normalized = normalize_benefit_channel(scope)
        if scope.strip().lower() in {"all", "todos", "tudo"}:
            return set(ALL_BENEFIT_CHANNELS)
        return {normalized}

    if isinstance(scope, Mapping):
        if any(bool(scope.get(key)) for key in ("all", "todos", "tudo")):
            return set(ALL_BENEFIT_CHANNELS)
        return {
            normalize_benefit_channel(key)
            for key, enabled in scope.items()
            if bool(enabled)
        }

    if isinstance(scope, Sequence):
        raw_values = [str(item).strip().lower() for item in scope if item is not None]
        if any(item in {"all", "todos", "tudo"} for item in raw_values):
            return set(ALL_BENEFIT_CHANNELS)
        return {normalize_benefit_channel(item) for item in raw_values}

    return None


def campaign_allows_sale_channel(campaign_or_params: Any, sale_channel: Any) -> bool:
    params = getattr(campaign_or_params, "params", campaign_or_params) or {}
    if not isinstance(params, Mapping):
        return True

    channel = normalize_benefit_channel(sale_channel)
    configured_channels = _channels_from_scope(_extract_scope(params))

    if configured_channels is None:
        # Compatibilidade: campanhas antigas continuam nos canais legados, mas
        # os novos centros de custo precisam de opt-in explicito.
        return channel not in LEGACY_BLOCKED_SERVICE_CHANNELS

    return channel in configured_channels
