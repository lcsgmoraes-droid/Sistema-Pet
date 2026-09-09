"""Rascunho comercial de créditos CorePet; não é uma tabela de custo de IA.

A ativação exige modo e lista explícita de empresas. Não há compra, bônus ou
mensalidade automática neste primeiro incremento.
"""

from __future__ import annotations

import os
from uuid import UUID


class CreditosError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 409):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


TARIFF_VERSION = "corepet-draft-2026-09-09-v1"
CREDIT_UNIT_CENTS = 2
SERVICES = (
    ("produto.descricao_fiscal", "Descrição e sugestão fiscal assistida", 125, True),
    ("oferta.imagem", "Imagem de oferta com IA", 150, True),
    ("produto.descricao", "Descrição de produto", None, False),
    ("produto.fiscal", "Sugestão fiscal assistida", None, False),
)


def normalize_tenant_id(tenant_id) -> str:
    try:
        return str(UUID(str(tenant_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise CreditosError("invalid_tenant", "Empresa inválida.", 400) from exc


def get_creditos_mode(tenant_id) -> str:
    tenant = normalize_tenant_id(tenant_id)
    mode = os.getenv("COREPET_CREDITOS_MODE", "off").strip().lower()
    if mode not in {"off", "shadow", "enforced"}:
        raise CreditosError(
            "creditos_configuration_invalid",
            "O modo de créditos precisa ser corrigido pelo administrador.",
            503,
        )
    if mode == "off":
        return "off"
    try:
        allowed = {
            str(UUID(value.strip()))
            for value in os.getenv("COREPET_CREDITOS_TENANT_ALLOWLIST", "").split(",")
            if value.strip()
        }
    except ValueError as exc:
        raise CreditosError(
            "creditos_configuration_invalid",
            "A lista de empresas habilitadas para créditos é inválida.",
            503,
        ) from exc
    return mode if tenant in allowed else "off"


def get_service(service_code: str) -> dict:
    for code, title, credits, enabled in SERVICES:
        if code == service_code:
            if not enabled:
                raise CreditosError(
                    "credit_service_disabled",
                    "Este serviço ainda não está habilitado.",
                    400,
                )
            return {
                "service_code": code,
                "title": title,
                "credits": credits,
                "price_cents": credits * CREDIT_UNIT_CENTS,
                "tariff_version": TARIFF_VERSION,
                "enabled": True,
            }
    raise CreditosError(
        "credit_service_unknown", "Serviço de créditos desconhecido.", 400
    )


def get_catalog(tenant_id) -> dict:
    return {
        "mode": get_creditos_mode(tenant_id),
        "currency": "BRL",
        "credit_unit_cents": CREDIT_UNIT_CENTS,
        "tariff_version": TARIFF_VERSION,
        "draft": True,
        "checkout_enabled": False,
        "services": [
            {
                "service_code": code,
                "title": title,
                "credits": credits,
                "price_cents": credits * CREDIT_UNIT_CENTS if credits else None,
                "enabled": enabled,
            }
            for code, title, credits, enabled in SERVICES
        ],
    }
