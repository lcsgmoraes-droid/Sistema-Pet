"""Uma fonte de verdade para o cadastro e a central iFood, apenas local."""

from decimal import Decimal
from typing import Any

from app.integrations.ifood.pricing import (
    decimal_value,
    monetary_value,
    money,
    resolve_ifood_prices,
)

MARGIN_CONFIG_FIELDS = (
    "commission_merchant_percent",
    "commission_ifood_percent",
    "payment_fee_percent",
    "tax_percent",
    "additional_unit_cost",
    "target_margin_percent",
)


def calculate_margin(
    product: Any, config: Any, price: float | None, modality: str
) -> dict:
    commission_field = (
        "commission_ifood_percent"
        if modality == "IFOOD"
        else "commission_merchant_percent"
    )
    inputs = {
        "price": (monetary_value(price), "Preço de venda válido"),
        "cost": (
            monetary_value(getattr(product, "preco_custo", None)),
            "Custo do produto",
        ),
        "commission": (
            decimal_value(getattr(config, commission_field, None)),
            "Comissão de entrega iFood"
            if modality == "IFOOD"
            else "Comissão de entrega própria",
        ),
        "payment_fee": (
            decimal_value(getattr(config, "payment_fee_percent", None)),
            "Taxa de pagamento",
        ),
        "tax": (
            decimal_value(getattr(config, "tax_percent", None)),
            "Tributos estimados",
        ),
        "additional_cost": (
            monetary_value(getattr(config, "additional_unit_cost", None)),
            "Despesa adicional por unidade",
        ),
    }
    # O ERP usa zero como custo inicial: nao assumir custo gratis por omissao.
    missing = [
        label
        for key, (value, label) in inputs.items()
        if value is None
        or value < 0
        or (key in ("price", "cost") and value <= 0)
        or (key in ("commission", "payment_fee", "tax") and value > 100)
    ]
    target = decimal_value(getattr(config, "target_margin_percent", None))
    result = {
        "calculated": not missing,
        "contribution": None,
        "percent": None,
        "price": price,
        "cost": float(inputs["cost"][0]) if inputs["cost"][0] is not None else None,
        "commission": None,
        "payment_fee": None,
        "tax": None,
        "additional_cost": float(inputs["additional_cost"][0])
        if inputs["additional_cost"][0] is not None
        else None,
        "target_percent": float(target) if target is not None else None,
        "below_target": False,
        "missing": missing,
        "assumption": "Percentuais sobre o preço vigente do item; entrega, embalagem por pedido e custos fixos não incluídos.",
    }
    if missing:
        return result
    revenue = inputs["price"][0]
    commission = Decimal(str(money(revenue * inputs["commission"][0] / 100)))
    payment = Decimal(str(money(revenue * inputs["payment_fee"][0] / 100)))
    tax = Decimal(str(money(revenue * inputs["tax"][0] / 100)))
    contribution = (
        revenue
        - inputs["cost"][0]
        - commission
        - payment
        - tax
        - inputs["additional_cost"][0]
    )
    percentage = contribution / revenue * 100
    result.update(
        contribution=money(contribution),
        percent=money(percentage),
        commission=money(commission),
        payment_fee=money(payment),
        tax=money(tax),
        below_target=target is not None and percentage < target,
    )
    return result


def product_identifier(product: Any) -> str:
    return str(
        getattr(product, "codigo_barras", None)
        or getattr(product, "gtin_ean", None)
        or getattr(product, "codigo", None)
        or ""
    ).strip()


def build_management_item(
    product: Any,
    config: Any,
    *,
    available_stock: float | None,
    duplicate_identifier=False,
    now=None,
) -> dict:
    prices = resolve_ifood_prices(
        product, getattr(config, "default_markup_percent", 0), now
    )
    pending = []

    def add(code, message, kind, field):
        pending.append({"code": code, "message": message, "kind": kind, "field": field})

    selected = bool(getattr(product, "anunciar_ifood", False))
    paused = bool(getattr(product, "ifood_pausado", False))
    name = str(getattr(product, "nome", "") or "").strip()
    identifier = product_identifier(product)
    if not name:
        add("nome", "Informe o nome do produto.", "bloqueio", "nome")
    if not identifier or any(ord(char) < 32 for char in identifier):
        add(
            "identificador",
            "Informe um EAN ou código interno válido.",
            "bloqueio",
            "codigo_barras",
        )
    if duplicate_identifier:
        add(
            "identificador_duplicado",
            "Outro produto selecionado usa o mesmo identificador iFood. Revise o vínculo.",
            "bloqueio",
            "codigo_barras",
        )
    if (
        not getattr(product, "ativo", True)
        or getattr(product, "situacao", True) is False
        or getattr(product, "deleted_at", None)
    ):
        add("inativo", "Produto inativo ou excluído no ERP.", "bloqueio", "ativo")
    if (
        getattr(product, "tipo_produto", "SIMPLES") == "PAI"
        or getattr(product, "is_parent", False)
        or not getattr(product, "is_sellable", True)
    ):
        add(
            "agrupador",
            "Selecione a variação vendável, em vez do produto agrupador.",
            "bloqueio",
            "tipo_produto",
        )
    if str(getattr(product, "tipo", "produto")).lower() == "servico":
        add(
            "servico",
            "Serviços não são suportados pelo catálogo iFood.",
            "bloqueio",
            "tipo",
        )
    if getattr(product, "e_granel", False):
        add(
            "granel",
            "Publicação de granel requer validar conversão de unidade e será habilitada em outra etapa.",
            "bloqueio",
            "e_granel",
        )
    if not str(getattr(product, "unidade", "") or "").strip():
        add(
            "unidade",
            "Informe a unidade da apresentação vendida.",
            "bloqueio",
            "unidade",
        )
    if prices["regular_price"] is None or prices["regular_price"] <= 0:
        add(
            "preco",
            "Informe um preço iFood maior que zero ou ajuste a regra da loja.",
            "bloqueio",
            "preco_ifood",
        )
    for code, message, field in prices.pop("promotion_errors"):
        add(code, message, "bloqueio", field)
    if available_stock is None:
        add(
            "estoque_desconhecido",
            "Estoque disponível será confirmado após salvar; se persistir, revise as reservas.",
            "operacional",
            "estoque_atual",
        )
    elif available_stock <= 0:
        add(
            "sem_estoque",
            "Temporariamente indisponível por falta de estoque livre.",
            "operacional",
            "estoque_atual",
        )
    if paused:
        add(
            "pausa_manual",
            "Pausa manual mantida mesmo após reposição de estoque.",
            "operacional",
            "ifood_pausado",
        )
    if not getattr(product, "imagem_principal", None):
        add(
            "foto",
            "Adicione uma foto para melhorar a oferta.",
            "recomendacao",
            "imagem_principal",
        )
    if not (
        getattr(product, "descricao_completa", None)
        or getattr(product, "descricao_curta", None)
    ):
        add(
            "descricao",
            "Adicione uma descrição do produto.",
            "recomendacao",
            "descricao_curta",
        )
    margins = {
        modality: calculate_margin(product, config, prices["effective_price"], modality)
        for modality in ("MERCHANT", "IFOOD")
    }
    if any(not margin["calculated"] for margin in margins.values()):
        add(
            "margem_incompleta",
            "Informe custo e premissas de taxas para calcular a margem em cada modalidade.",
            "rentabilidade",
            "preco_custo",
        )
    if any(margin["below_target"] for margin in margins.values()):
        add(
            "margem_abaixo_meta",
            "A contribuição estimada está abaixo da meta em uma modalidade.",
            "rentabilidade",
            "preco_ifood",
        )
    eligible = not any(item["kind"] == "bloqueio" for item in pending)
    status = (
        "nao_selecionado"
        if not selected
        else "pausado"
        if paused
        else "pendente"
        if not eligible or available_stock is None
        else "sem_estoque"
        if available_stock <= 0
        else "pronto_para_envio"
    )
    return {
        "product_id": getattr(product, "id", None),
        "sku": str(getattr(product, "codigo", "") or ""),
        "name": name,
        "identifier": identifier,
        "selected": selected,
        "paused": paused,
        "saved_specific_price": getattr(
            product, "ifood_saved_specific_price", getattr(product, "preco_ifood", None)
        ),
        **prices,
        "available_stock": available_stock,
        "status": status,
        "eligible": eligible,
        "pending": pending,
        "margins": margins,
        "sync_status": "nao_enviado",
        "last_confirmed_price": None,
    }
