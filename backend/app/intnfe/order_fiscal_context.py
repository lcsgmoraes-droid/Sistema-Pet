"""Fatos fiscais de pedidos, independentes do conector que recebeu a venda."""

from __future__ import annotations

import re
from typing import Any

MARKETPLACE_CHANNELS = {
    "amazon",
    "mercado_livre",
    "mercadolivre",
    "ml",
    "shopee",
    "tiktok",
    "tiktok_shop",
}


def _text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _digits(value: Any) -> str | None:
    normalized = re.sub(r"\D", "", str(value or ""))
    return normalized or None


def _dictionary(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _channel(value: Any) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")
    return normalized or None


def fiscal_order_context(order: dict) -> dict:
    """Extrai somente fatos comerciais; regras tributárias entram na emissão."""

    channel = _channel(order.get("canal") or order.get("origem_canal"))
    marketplace = bool(order.get("marketplace")) or channel in MARKETPLACE_CHANNELS
    intermediary = _dictionary(order.get("intermediador"))
    shipping = _dictionary(order.get("transporte"))
    carrier = _dictionary(shipping.get("transportadora") or order.get("transportadora"))
    payment = _dictionary(order.get("pagamento"))
    customer = _dictionary(order.get("cliente"))
    delivery = _dictionary(order.get("endereco_entrega"))
    additional = _dictionary(order.get("informacoes_adicionais"))

    intermediary_cnpj = _digits(intermediary.get("cnpj"))
    intermediary_id = _text(
        intermediary.get("identificacao") or intermediary.get("id_cadastro")
    )
    order_reference = _text(
        additional.get("numero_pedido_loja")
        or additional.get("numero_loja_virtual")
        or order.get("numero_pedido_loja")
        or order.get("referencia_externa")
    )
    destination_state = (
        _text(delivery.get("uf") or customer.get("uf")) or ""
    ).upper() or None
    payment_methods = [
        method
        for method in (
            _text(item.get("forma") or item.get("descricao"))
            for item in _list(payment.get("parcelas"))
            if isinstance(item, dict)
        )
        if method
    ]
    if not payment_methods:
        fallback_payment = _text(payment.get("forma") or payment.get("condicao"))
        if fallback_payment:
            payment_methods.append(fallback_payment)

    pending = []
    if marketplace and not order_reference:
        pending.append("Informe a referência do pedido no marketplace.")
    if marketplace and bool(intermediary_cnpj) != bool(intermediary_id):
        pending.append(
            "Informe juntos o CNPJ e o identificador de cadastro do intermediador."
        )
    if destination_state is None and int(order.get("modelo") or 55) == 55:
        pending.append("Informe a UF do destinatário da NF-e.")
    carrier_name = _text(carrier.get("nome") or carrier.get("razao_social"))
    carrier_document = _digits(
        carrier.get("cpf_cnpj") or carrier.get("cnpj") or carrier.get("documento")
    )
    if bool(carrier_name) != bool(carrier_document):
        pending.append(
            "Complete nome e CPF/CNPJ da transportadora ou remova o cadastro parcial."
        )

    return {
        "origem": _text(order.get("origem")) or "corepet",
        "canal": channel,
        "marketplace": marketplace,
        "referencia_externa": order_reference,
        "destino_uf": destination_state,
        "intermediador": (
            {"cnpj": intermediary_cnpj, "id_cadastro": intermediary_id}
            if intermediary_cnpj and intermediary_id
            else None
        ),
        "transporte": {
            "modalidade": _text(shipping.get("tipo")),
            "frete_por_conta": _text(shipping.get("frete_por_conta")),
            "transportadora": (
                {"nome": carrier_name, "cpf_cnpj": carrier_document}
                if carrier_name and carrier_document
                else None
            ),
        },
        "formas_pagamento": payment_methods,
        "pendencias": pending,
        "pronto_para_montagem": not pending,
    }
