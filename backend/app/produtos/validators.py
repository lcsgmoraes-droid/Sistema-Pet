"""Validadores e buscas 404 usados pelas rotas de produtos."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.produtos.core import _normalizar_sku_produto
from app.produtos_models import Categoria, Marca, Produto


def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant."""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_produto_ou_404(db: Session, produto_id: int, tenant_id: int):
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    return produto


def _obter_categoria_ou_404(db: Session, categoria_id: int, tenant_id: int):
    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.tenant_id == tenant_id,
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")

    return categoria


def _obter_marca_ou_404(db: Session, marca_id: int, tenant_id: int):
    marca = (
        db.query(Marca)
        .filter(
            Marca.id == marca_id,
            Marca.tenant_id == tenant_id,
        )
        .first()
    )

    if not marca:
        raise HTTPException(status_code=404, detail="Marca nao encontrada")

    return marca


def _validar_sku_unico(
    db: Session,
    sku: str,
    tenant_id: int,
    produto_id: Optional[int] = None,
):
    sku_normalizado = _normalizar_sku_produto(sku)

    query = db.query(Produto).filter(
        func.lower(func.trim(Produto.codigo)) == sku_normalizado.lower(),
        Produto.tenant_id == tenant_id,
    )

    if produto_id:
        query = query.filter(Produto.id != produto_id)

    if query.first():
        raise HTTPException(
            status_code=400,
            detail=f"SKU '{sku}' ja esta em uso",
        )


def _validar_codigo_barras_unico(
    db: Session,
    codigo_barras: str,
    tenant_id: int,
    produto_id: Optional[int] = None,
):
    query = db.query(Produto).filter(
        Produto.codigo_barras == codigo_barras,
        Produto.tenant_id == tenant_id,
    )

    if produto_id:
        query = query.filter(Produto.id != produto_id)

    if query.first():
        raise HTTPException(
            status_code=400,
            detail=f"Codigo de barras '{codigo_barras}' ja esta em uso",
        )


def _validar_pode_inativar_produto(db: Session, produto: Produto, tenant_id):
    """Bloqueia inativacao de produto pai com variacoes ativas."""
    if not produto.is_parent:
        return

    variacoes_ativas = (
        db.query(Produto)
        .filter(
            Produto.produto_pai_id == produto.id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .count()
    )

    if variacoes_ativas > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Produto '{produto.nome}' possui {variacoes_ativas} variacao(oes) ativa(s) "
                "e nao pode ser desativado. Desative primeiro todas as variacoes."
            ),
        )
