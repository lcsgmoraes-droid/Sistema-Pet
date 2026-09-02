"""Regra unica de publicacao e saude do catalogo online."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, or_

from app.produtos_models import Produto
from app.services.sales_channel import normalize_online_sales_channel


ISSUE_LABELS = {
    "inativo": "Produto inativo",
    "nao_vendavel": "Produto não vendável",
    "nao_publicado": "Não publicado no canal",
    "servico_oculto": "Serviço oculto pela configuração",
    "sem_preco": "Preço de venda zerado ou ausente",
    "estoque_oculto": "Esgotado e oculto pela configuração",
    "sem_imagem_bloqueante": "Sem imagem e oculto pela configuração",
    "sem_imagem": "Sem imagem",
    "sem_descricao": "Sem descrição",
    "sem_categoria": "Sem categoria",
    "sem_marca": "Sem marca",
}


def catalog_channel(channel: str | None) -> str:
    return normalize_online_sales_channel(channel)


def catalog_stock_expression(tenant: Any):
    source = (
        Produto.estoque_ecommerce
        if bool(getattr(tenant, "ecommerce_usar_estoque_canal", False))
        else Produto.estoque_atual
    )
    return func.coalesce(source, 0)


def catalog_price_expression(channel: str | None):
    if catalog_channel(channel) == "app":
        return func.coalesce(Produto.preco_app, Produto.preco_venda, 0)
    return func.coalesce(Produto.preco_ecommerce, Produto.preco_venda, 0)


def catalog_published_expression(channel: str | None):
    return (
        Produto.anunciar_app.is_(True)
        if catalog_channel(channel) == "app"
        else Produto.anunciar_ecommerce.is_(True)
    )


def catalog_has_image_expression():
    return or_(
        and_(
            Produto.imagem_principal.is_not(None),
            func.length(func.trim(Produto.imagem_principal)) > 0,
        ),
        Produto.imagens.any(),
    )


def catalog_has_description_expression():
    return or_(
        and_(
            Produto.descricao_curta.is_not(None),
            func.length(func.trim(Produto.descricao_curta)) > 0,
        ),
        and_(
            Produto.descricao_completa.is_not(None),
            func.length(func.trim(Produto.descricao_completa)) > 0,
        ),
    )


def catalog_base_filters():
    return [
        Produto.ativo.is_(True),
        Produto.situacao.is_not(False),
        Produto.is_sellable.is_not(False),
        Produto.tipo_produto.in_(("SIMPLES", "VARIACAO", "KIT")),
    ]


def catalog_public_visibility_filters(tenant: Any, channel: str | None):
    """Filtros usados pelo catalogo publico e pela saude do catalogo."""
    stock = catalog_stock_expression(tenant)
    service = func.lower(func.coalesce(Produto.tipo, "produto")) == "servico"
    filters = [
        *catalog_base_filters(),
        catalog_published_expression(channel),
        catalog_price_expression(channel) > 0,
    ]
    if bool(getattr(tenant, "ecommerce_ocultar_servicos", True)):
        filters.append(~service)
    if bool(getattr(tenant, "ecommerce_ocultar_sem_estoque", False)):
        filters.append(or_(service, stock > 0))
    if bool(getattr(tenant, "ecommerce_ocultar_sem_imagem", False)):
        filters.append(catalog_has_image_expression())
    return filters


def catalog_health_filter_expression(tenant: Any, channel: str | None, situation: str):
    """Expressão do filtro operacional usado também na lista geral de produtos."""
    published = catalog_published_expression(channel)
    stock = catalog_stock_expression(tenant)
    has_image = catalog_has_image_expression()
    has_description = catalog_has_description_expression()
    service = func.lower(func.coalesce(Produto.tipo, "produto")) == "servico"
    hard_blocks = [catalog_price_expression(channel) <= 0]
    if bool(getattr(tenant, "ecommerce_ocultar_servicos", True)):
        hard_blocks.append(service)
    if bool(getattr(tenant, "ecommerce_ocultar_sem_imagem", False)):
        hard_blocks.append(~has_image)
    hard_block = or_(*hard_blocks)
    warning = or_(
        ~has_image,
        ~has_description,
        Produto.categoria_id.is_(None),
        Produto.marca_id.is_(None),
    )

    if situation == "publicado":
        return published
    if situation == "nao_publicado":
        return ~published
    if situation == "bloqueado":
        return and_(published, hard_block)
    if situation == "esgotado":
        return and_(published, ~hard_block, stock <= 0)
    if situation == "pendencias":
        return and_(published, ~hard_block, stock > 0, warning)
    if situation == "pronto":
        return and_(published, ~hard_block, stock > 0, ~warning)
    return None


def catalog_stock_value(tenant: Any, product: Any) -> float:
    value = (
        getattr(product, "estoque_ecommerce", None)
        if bool(getattr(tenant, "ecommerce_usar_estoque_canal", False))
        else getattr(product, "estoque_atual", None)
    )
    return float(value or 0)


def catalog_price_value(product: Any, channel: str | None) -> float:
    specific = (
        getattr(product, "preco_app", None)
        if catalog_channel(channel) == "app"
        else getattr(product, "preco_ecommerce", None)
    )
    value = specific if specific is not None else getattr(product, "preco_venda", None)
    return float(value or 0)


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _has_image(product: Any) -> bool:
    if _has_text(getattr(product, "imagem_principal", None)):
        return True
    return bool(getattr(product, "imagens", None) or [])


def _is_published(product: Any, channel: str) -> bool:
    field = "anunciar_app" if channel == "app" else "anunciar_ecommerce"
    return bool(getattr(product, field, False))


def classify_catalog_product(
    product: Any,
    tenant: Any,
    channel: str | None = "ecommerce",
    *,
    waitlist_count: int = 0,
) -> dict[str, Any]:
    """Classifica um produto sem duplicar as regras do catalogo publico."""
    normalized_channel = catalog_channel(channel)
    stock = catalog_stock_value(tenant, product)
    price = catalog_price_value(product, normalized_channel)
    has_image = _has_image(product)
    is_service = (
        str(getattr(product, "tipo", "produto") or "produto").lower() == "servico"
    )
    published = _is_published(product, normalized_channel)

    blockers: list[str] = []
    if (
        not bool(getattr(product, "ativo", False))
        or getattr(product, "situacao", True) is False
    ):
        blockers.append("inativo")
    if (
        getattr(product, "tipo_produto", "SIMPLES")
        not in {"SIMPLES", "VARIACAO", "KIT"}
        or getattr(product, "is_sellable", True) is False
    ):
        blockers.append("nao_vendavel")
    if not published:
        blockers.append("nao_publicado")
    if is_service and bool(getattr(tenant, "ecommerce_ocultar_servicos", True)):
        blockers.append("servico_oculto")
    if price <= 0:
        blockers.append("sem_preco")
    if not has_image and bool(getattr(tenant, "ecommerce_ocultar_sem_imagem", False)):
        blockers.append("sem_imagem_bloqueante")

    hidden_out_of_stock = stock <= 0 and bool(
        getattr(tenant, "ecommerce_ocultar_sem_estoque", False)
    )
    configuration_blocks = [*blockers]
    if hidden_out_of_stock:
        configuration_blocks.append("estoque_oculto")

    warnings: list[str] = []
    if not has_image and "sem_imagem_bloqueante" not in blockers:
        warnings.append("sem_imagem")
    if not (
        _has_text(getattr(product, "descricao_curta", None))
        or _has_text(getattr(product, "descricao_completa", None))
    ):
        warnings.append("sem_descricao")
    if getattr(product, "categoria_id", None) is None:
        warnings.append("sem_categoria")
    if getattr(product, "marca_id", None) is None:
        warnings.append("sem_marca")

    if blockers:
        status = "bloqueado"
    elif stock <= 0:
        status = "esgotado"
    elif warnings:
        status = "pendencias"
    else:
        status = "pronto"

    visible = not blockers and not hidden_out_of_stock
    purchasable = visible and (is_service or stock > 0) and price > 0
    return {
        "produto_id": int(product.id),
        "canal": normalized_channel,
        "publicado": published,
        "status": status,
        "visivel": visible,
        "compravel": purchasable,
        "estoque": stock,
        "preco": price,
        "avise_me_pendentes": int(waitlist_count or 0),
        "bloqueios": [
            {"codigo": code, "label": ISSUE_LABELS[code]}
            for code in configuration_blocks
        ],
        "pendencias": [
            {"codigo": code, "label": ISSUE_LABELS[code]} for code in warnings
        ],
    }
