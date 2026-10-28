"""Aplica a evidencia Financial atual sobre custos congelados, sem escrita/rede."""

from decimal import Decimal, InvalidOperation
from typing import Any

PENDING_IFOOD_FINANCIAL = "pending_ifood_financial"
PENDENCIA_IFOOD = (
    "Aguardando a conciliacao das cobrancas do iFood para calcular lucro e margem."
)


def venda_aguarda_financial_ifood(venda: Any) -> bool:
    canal = str(getattr(venda, "canal", "") or "").strip().lower()
    if canal == "ifood":
        return True
    return any(
        str(getattr(pagamento, "gateway_provider", "") or "").strip().lower() == "ifood"
        for pagamento in list(getattr(venda, "pagamentos", []) or [])
    )


def _money(value):
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _round(value):
    return round(float(value), 2)


def _taxa_local(venda, snapshot):
    if "taxa_cartao_local" in snapshot:
        return _money(snapshot["taxa_cartao_local"])
    pagamentos = list(getattr(venda, "pagamentos", []) or [])
    if not pagamentos and _money(snapshot.get("taxa_cartao")) not in (
        None,
        Decimal("0"),
    ):
        # O total legado nao separa adquirente local e plataforma. Uma taxa
        # externa que chegou depois nao pode ser subtraida dessa fotografia.
        return None
    total = Decimal("0")
    for pagamento in pagamentos:
        if str(getattr(pagamento, "gateway_provider", "") or "").lower() == "ifood":
            continue
        valor = getattr(pagamento, "gateway_fee_amount", None)
        if valor is None:
            valor = getattr(pagamento, "valor_taxa_prevista", None)
        if valor is None and str(
            getattr(pagamento, "forma_pagamento", "") or ""
        ).lower() in {"dinheiro", "cash"}:
            valor = 0
        taxa = _money(valor)
        if taxa is None:
            return None
        total += taxa
    return total


def _component(charges, code):
    valores = [
        _money(charge.get("amount"))
        for charge in charges
        if charge.get("code") == code and charge.get("classification") != "unclassified"
    ]
    return (
        sum(valores, Decimal("0"))
        if valores and all(v is not None for v in valores)
        else None
    )


def aplicar_pendencia_ifood(venda: Any, snapshot: dict, *, financial=None) -> dict:
    if not (
        venda_aguarda_financial_ifood(venda)
        or str(snapshot.get("gateway_provider") or "").strip().lower() == "ifood"
        or snapshot.get("taxas_ifood_pendentes")
    ):
        return snapshot

    dados = dict(financial or {})
    charges = list(dados.get("charges") or [])
    pending = [dict(p) for p in dados.get("pending_components") or []]
    if not dados:
        pending = [
            {
                "code": code,
                "label": label,
                "reason": "Cobrança ainda não recebida no Financial.",
            }
            for code, label in (
                ("ORDER_COMMISSION", "Comissão iFood"),
                ("PAYMENT_TRANSACTION_FEE", "Taxa de pagamento iFood"),
            )
        ]
        dados.update(
            charges=[],
            complete=False,
            fee_total=None,
            fee_known_total=0,
            simulated=False,
        )
    payment_fee = _component(charges, "PAYMENT_TRANSACTION_FEE")
    marketplace = _component(charges, "ORDER_COMMISSION")
    local_fee = _taxa_local(venda, snapshot)
    if local_fee is None:
        pending.append(
            {
                "code": "ERP_PAYMENT_FEE",
                "label": "Taxa do pagamento local",
                "reason": "Taxa histórica do pagamento local ainda não comprovada.",
            }
        )
    required = (
        "venda_bruta",
        "taxa_loja",
        "desconto",
        "taxa_entrega",
        "taxa_operacional",
        "comissao",
        "imposto",
        "custo_campanha",
        "custo_produtos",
    )
    base = {campo: _money(snapshot.get(campo)) for campo in required}
    if any(value is None for value in base.values()):
        pending.append(
            {
                "code": "ERP_COSTS",
                "label": "Base histórica da venda",
                "reason": "Há componentes históricos da venda ainda não comprovados.",
            }
        )
    total_fee = _money(dados.get("fee_total"))
    complete = (
        bool(dados.get("complete"))
        and not pending
        and not dados.get("simulated")
        and total_fee is not None
    )
    dados["pending_components"] = pending
    dados["complete"] = complete
    metadados = {
        "rentabilidade_status": "complete" if complete else PENDING_IFOOD_FINANCIAL,
        "taxas_ifood_pendentes": not complete,
        "pendencias_rentabilidade": [f"{p['label']}: {p['reason']}" for p in pending]
        or ([] if complete else [PENDENCIA_IFOOD]),
    }
    protegido = {
        **snapshot,
        **metadados,
        "ifood_financial": dados,
        "taxa_cartao_local": _round(local_fee) if local_fee is not None else None,
        "taxa_ifood": _round(marketplace) if marketplace is not None else None,
        "taxa_cartao": _round(local_fee + payment_fee)
        if local_fee is not None and payment_fee is not None
        else None,
        "taxa_gateway": _round(payment_fee) if payment_fee is not None else None,
        "valor_liquido_gateway": None,
    }
    net = None
    if complete:
        net = (
            base["venda_bruta"]
            + base["taxa_loja"]
            - sum(
                (
                    base[key]
                    for key in (
                        "desconto",
                        "taxa_entrega",
                        "taxa_operacional",
                        "comissao",
                        "imposto",
                        "custo_campanha",
                    )
                ),
                Decimal("0"),
            )
            - local_fee
            - total_fee
        )
    lucro = net - base["custo_produtos"] if net is not None else None
    protegido.update(
        venda_liquida=_round(net) if net is not None else None,
        lucro=_round(lucro) if lucro is not None else None,
        margem_sobre_venda=round(float(lucro / base["venda_bruta"] * 100), 1)
        if lucro is not None and base["venda_bruta"]
        else 0.0
        if complete
        else None,
        margem_sobre_custo=round(float(lucro / base["custo_produtos"] * 100), 1)
        if lucro is not None and base["custo_produtos"]
        else 0.0
        if complete
        else None,
    )
    protegido["itens"] = []
    bruto_itens = sum(
        (
            _money(item.get("venda_bruta")) or Decimal("0")
            for item in snapshot.get("itens") or []
        ),
        Decimal("0"),
    )
    itens = list(snapshot.get("itens") or [])
    remaining_card = (
        local_fee + payment_fee
        if local_fee is not None and payment_fee is not None
        else None
    )
    remaining_market = marketplace
    remaining_deduction = local_fee + total_fee if complete else None
    for indice, item in enumerate(itens):
        copia = {**item, **metadados}
        peso = (
            (_money(item.get("venda_bruta")) or Decimal("0")) / bruto_itens
            if bruto_itens
            else Decimal("0")
        )
        ultimo = indice == len(itens) - 1
        card_item = (
            (
                remaining_card
                if ultimo
                else _money(_round((local_fee + payment_fee) * peso))
            )
            if remaining_card is not None
            else None
        )
        market_item = (
            (remaining_market if ultimo else _money(_round(marketplace * peso)))
            if remaining_market is not None
            else None
        )
        deduction_item = (
            (
                remaining_deduction
                if ultimo
                else _money(_round((local_fee + total_fee) * peso))
            )
            if remaining_deduction is not None
            else None
        )
        if card_item is not None:
            remaining_card -= card_item
        if market_item is not None:
            remaining_market -= market_item
        if deduction_item is not None:
            remaining_deduction -= deduction_item
        copia["taxa_cartao"] = _round(card_item) if card_item is not None else None
        copia["taxa_ifood"] = _round(market_item) if market_item is not None else None
        item_net = None
        campos_item = (
            "venda_bruta",
            "taxa_loja",
            "desconto",
            "taxa_entrega",
            "taxa_operacional",
            "comissao",
            "imposto",
            "campanha",
            "custo_total",
            "quantidade",
        )
        values = {key: _money(item.get(key)) for key in campos_item}
        if complete and all(value is not None for value in values.values()):
            item_net = (
                values["venda_bruta"]
                + values["taxa_loja"]
                - sum(
                    (
                        values[key]
                        for key in (
                            "desconto",
                            "taxa_entrega",
                            "taxa_operacional",
                            "comissao",
                            "imposto",
                            "campanha",
                        )
                    ),
                    Decimal("0"),
                )
                - deduction_item
            )
        item_lucro = item_net - values["custo_total"] if item_net is not None else None
        copia.update(
            valor_liquido=_round(item_net) if item_net is not None else None,
            lucro=_round(item_lucro) if item_lucro is not None else None,
            lucro_unitario=_round(item_lucro / values["quantidade"])
            if item_lucro is not None and values["quantidade"]
            else None,
            margem_sobre_venda=round(float(item_lucro / values["venda_bruta"] * 100), 1)
            if item_lucro is not None and values["venda_bruta"]
            else 0.0
            if item_lucro is not None
            else None,
            margem_sobre_custo=round(float(item_lucro / values["custo_total"] * 100), 1)
            if item_lucro is not None and values["custo_total"]
            else 0.0
            if item_lucro is not None
            else None,
        )
        protegido["itens"].append(copia)
    return protegido


def resumir_financial_ifood(financeiros):
    """Agrupa evidencias sem transformar subtotal conhecido em custo final."""
    dados = [value for value in financeiros if value]
    if not dados:
        return None
    charges, pendencias = {}, {}
    for value in dados:
        counted = set()
        for charge in value.get("charges") or []:
            key = (charge["code"], charge["label"], charge.get("status"))
            group = charges.setdefault(
                key,
                {
                    **charge,
                    "amount": 0.0 if charge.get("amount") is not None else None,
                    "signed_amount": 0.0,
                    "orders": 0,
                },
            )
            if group["amount"] is not None:
                group["amount"] = _round(
                    Decimal(str(group["amount"]))
                    + (_money(charge.get("amount")) or Decimal("0"))
                )
            group["signed_amount"] = _round(
                Decimal(str(group["signed_amount"]))
                + (_money(charge.get("signed_amount")) or Decimal("0"))
            )
            if key not in counted:
                group["orders"] += 1
                counted.add(key)
        for pending in value.get("pending_components") or []:
            key = (pending["code"], pending["label"], pending["reason"])
            group = pendencias.setdefault(key, {**pending, "orders": 0})
            group["orders"] += 1
    complete = all(value.get("complete") for value in dados)
    return {
        "charges": list(charges.values()),
        "pending_components": list(pendencias.values()),
        "fee_known_total": _round(
            sum(
                (Decimal(str(value.get("fee_known_total") or 0)) for value in dados),
                Decimal("0"),
            )
        ),
        "fee_total": _round(
            sum((Decimal(str(value["fee_total"])) for value in dados), Decimal("0"))
        )
        if complete
        else None,
        "complete": complete,
        "simulated": any(value.get("simulated") for value in dados),
        "simulation_complete": all(
            value.get("simulation_complete") or value.get("complete") for value in dados
        ),
        "orders": len(dados),
    }
