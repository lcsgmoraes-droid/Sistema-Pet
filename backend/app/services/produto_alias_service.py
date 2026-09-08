"""Aliases identificam itens/pedidos; nunca autorizam importacao de saldo ou preco."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from sqlalchemy import text

from app.produto_identity_models import ProdutoSkuAlias
from app.produtos_models import Produto


def aliases_do_tenant(db, tenant_id):
    return (
        db.query(ProdutoSkuAlias).filter(ProdutoSkuAlias.tenant_id == tenant_id).all()
    )


def aliases_por_produto(db, tenant_id):
    result = defaultdict(list)
    for alias in aliases_do_tenant(db, tenant_id):
        result[alias.produto_id].append(alias.sku)
    return dict(result)


def validar_chaves_sem_alias_alheio(db, *, tenant_id, chaves, produto_id=None):
    from app.services.produto_sku_service import normalizar_sku

    _lock_alias_namespace(db, tenant_id)
    normalized = {normalizar_sku(key) for key in chaves if normalizar_sku(key)}
    if not normalized:
        return
    query = db.query(ProdutoSkuAlias).filter(
        ProdutoSkuAlias.tenant_id == tenant_id,
        ProdutoSkuAlias.sku_normalizado.in_(normalized),
    )
    if produto_id is not None:
        query = query.filter(ProdutoSkuAlias.produto_id != produto_id)
    if query.first():
        raise ValueError(
            "SKU ou codigo reservado como alias de outro produto neste tenant."
        )


def _lock_alias_namespace(db, tenant_id):
    # Serialize alias creation/merges per company, including a currently absent alias.
    if db.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(
            hashlib.sha256(f"produto-alias:{tenant_id}".encode()).digest()[:8],
            "big",
            signed=True,
        )
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def validar_alias(db, *, tenant_id, produto_id, sku, absorvido_id=None):
    from app.services.produto_sku_service import chaves_sku_produto, normalizar_sku

    value = str(sku or "").strip()
    normalized = normalizar_sku(value)
    if not value or len(value) > 100 or len(normalized) > 200:
        raise ValueError("Alias SKU invalido (1 a 100 caracteres).")
    target = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.id == produto_id)
        .first()
    )
    if not target or target.deleted_at is not None:
        raise ValueError("Produto de destino nao encontrado ou arquivado neste tenant.")
    allowed = {produto_id, absorvido_id}
    for product in (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.deleted_at.is_(None))
        .all()
    ):
        if product.id not in allowed and normalized in {
            normalizar_sku(key) for key in chaves_sku_produto(product)
        }:
            raise ValueError("Alias SKU ja identifica outro produto neste tenant.")
    existing = (
        db.query(ProdutoSkuAlias)
        .filter(
            ProdutoSkuAlias.tenant_id == tenant_id,
            ProdutoSkuAlias.sku_normalizado == normalized,
        )
        .first()
    )
    if existing and existing.produto_id not in allowed:
        raise ValueError("Alias SKU ja cadastrado para outro produto neste tenant.")
    return target, existing, value, normalized


def registrar_alias(
    db,
    *,
    tenant_id,
    produto_id,
    sku,
    user_id,
    motivo,
    origem="confirmacao_manual",
    absorvido_id=None,
):
    _lock_alias_namespace(db, tenant_id)
    target, existing, value, normalized = validar_alias(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        sku=sku,
        absorvido_id=absorvido_id,
    )
    if not str(motivo or "").strip():
        raise ValueError("Informe a evidencia que confirma a identidade do SKU.")
    if existing:
        if existing.produto_id != target.id:
            existing.produto_id = target.id
        return existing
    alias = ProdutoSkuAlias(
        tenant_id=tenant_id,
        produto_id=target.id,
        sku=value,
        sku_normalizado=normalized,
        user_id=user_id,
        origem=origem,
        motivo=motivo.strip(),
    )
    db.add(alias)
    db.flush()
    return alias


def preview_alias(db, *, tenant_id, produto_id, sku):
    product, existing, value, normalized = validar_alias(
        db, tenant_id=tenant_id, produto_id=produto_id, sku=sku
    )
    state = {
        "produto_id": product.id,
        "sku_canonico": product.codigo,
        "sku_alias": value,
        "normalizado": normalized,
        "updated_at": str(product.updated_at),
        "alias_id": existing.id if existing else None,
    }
    token = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return {
        **state,
        "preview_token": token,
        "altera_estoque": False,
        "altera_reservas": False,
    }


def aplicar_alias(db, *, tenant_id, produto_id, sku, preview_token, user_id, motivo):
    _lock_alias_namespace(db, tenant_id)
    db.query(Produto).filter(
        Produto.tenant_id == tenant_id, Produto.id == produto_id
    ).with_for_update().populate_existing().all()
    preview = preview_alias(db, tenant_id=tenant_id, produto_id=produto_id, sku=sku)
    if preview["preview_token"] != preview_token:
        raise ValueError("Cadastro alterado desde o preview; revise novamente o alias.")
    alias = registrar_alias(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        sku=sku,
        user_id=user_id,
        motivo=motivo,
    )
    db.commit()
    return {
        "success": True,
        "alias_id": alias.id,
        "produto_id": produto_id,
        "sku": alias.sku,
    }
