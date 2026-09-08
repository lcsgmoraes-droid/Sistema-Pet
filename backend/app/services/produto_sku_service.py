"""Resolucao centralizada de SKU, codigo de barras e codigos alternativos."""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.produtos_models import Produto
from app.produto_identity_models import ProdutoSkuAlias


def normalizar_sku(valor: object) -> str:
    return str(valor or "").strip().casefold()


def codigos_alternativos_produto(produto: Produto) -> list[str]:
    valor = getattr(produto, "codigos_barras_alternativos", None)
    if not valor:
        return []

    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (TypeError, ValueError):
            valor = [valor]

    if not isinstance(valor, (list, tuple, set)):
        return []

    codigos: list[str] = []
    vistos: set[str] = set()
    for item in valor:
        texto = str(item or "").strip()
        chave = normalizar_sku(texto)
        if texto and chave not in vistos:
            codigos.append(texto)
            vistos.add(chave)
    return codigos


def chaves_sku_produto(produto: Produto) -> list[str]:
    chaves: list[str] = []
    vistos: set[str] = set()
    for valor in (
        getattr(produto, "codigo", None),
        getattr(produto, "codigo_barras", None),
        *codigos_alternativos_produto(produto),
    ):
        texto = str(valor or "").strip()
        chave = normalizar_sku(texto)
        if texto and chave not in vistos:
            chaves.append(texto)
            vistos.add(chave)
    return chaves


def _candidatos_codigo_alternativo(
    db: Session,
    *,
    tenant_id,
    skus: Iterable[str],
) -> list[Produto]:
    termos = [str(sku or "").strip() for sku in skus if str(sku or "").strip()]
    if not termos:
        return []

    filtros = [
        Produto.codigos_barras_alternativos.ilike(f"%{termo}%") for termo in termos
    ]
    return (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.codigos_barras_alternativos.isnot(None),
            or_(*filtros),
        )
        .all()
    )


def buscar_produtos_por_skus(
    db: Session,
    *,
    tenant_id,
    skus: Iterable[str],
) -> dict[str, Produto]:
    entradas = list(
        dict.fromkeys(str(sku or "").strip() for sku in skus if str(sku or "").strip())
    )
    if not entradas:
        return {}

    normalizados = {normalizar_sku(sku) for sku in entradas}
    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            or_(
                func.lower(func.trim(Produto.codigo)).in_(normalizados),
                func.lower(func.trim(Produto.codigo_barras)).in_(normalizados),
            ),
        )
        .all()
    )
    produtos.extend(
        produto
        for produto in _candidatos_codigo_alternativo(
            db,
            tenant_id=tenant_id,
            skus=entradas,
        )
        if produto not in produtos
    )

    explicit_aliases = (
        db.query(ProdutoSkuAlias, Produto)
        .join(
            Produto,
            (Produto.id == ProdutoSkuAlias.produto_id)
            & (Produto.tenant_id == ProdutoSkuAlias.tenant_id),
        )
        .filter(
            ProdutoSkuAlias.tenant_id == tenant_id,
            ProdutoSkuAlias.sku_normalizado.in_(normalizados),
            Produto.deleted_at.is_(None),
        )
        .all()
    )
    por_chave: dict[str, Produto] = {}
    for produto in produtos:
        if produto.deleted_at is not None:
            continue
        for chave in chaves_sku_produto(produto):
            normalized = normalizar_sku(chave)
            if (
                normalized in normalizados
                and normalized in por_chave
                and por_chave[normalized].id != produto.id
            ):
                raise ValueError("Identidade SKU ambigua neste tenant.")
            por_chave.setdefault(normalized, produto)
    for alias, produto in explicit_aliases:
        existing = por_chave.get(alias.sku_normalizado)
        if existing and existing.id != produto.id:
            raise ValueError("Alias SKU em conflito com outro produto neste tenant.")
        por_chave[alias.sku_normalizado] = produto

    return {
        sku: por_chave[chave]
        for sku in entradas
        if (chave := normalizar_sku(sku)) in por_chave
    }


def buscar_produto_por_sku(db: Session, *, tenant_id, sku: str) -> Produto | None:
    sku_limpo = str(sku or "").strip()
    if not sku_limpo:
        return None
    return buscar_produtos_por_skus(
        db,
        tenant_id=tenant_id,
        skus=[sku_limpo],
    ).get(sku_limpo)
