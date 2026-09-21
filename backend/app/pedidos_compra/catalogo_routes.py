"""Catalogo paginado para montar pedidos diretamente pelos produtos."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.pedidos_compra.catalogo_produtos import (
    DIAS_RISCO_ESTOQUE,
    calcular_situacao_estoque_catalogo,
    montar_metricas_giro_catalogo,
)
from app.pedidos_compra.sugestao_queries import (
    _carregar_vendas_sugestao,
    _filtro_ativo_ou_legado_sugestao,
    _obter_estoque_atual_sugestao,
)
from app.produtos.core import _produto_sku_value
from app.produtos.listagem import _palavras_busca_produto
from app.produtos.search import (
    _build_produto_search_order_clause,
    _produto_search_conditions,
)
from app.produtos_models import Marca, Produto
from app.security.permissions_decorator import require_permission
from app.vendas_models import Venda, VendaItem


router = APIRouter()


def _subquery_vendas_30_dias(db: Session, tenant_id, data_fim: datetime):
    data_inicio = data_fim - timedelta(days=30)
    venda_data = func.coalesce(
        Venda.data_finalizacao,
        Venda.data_venda,
        Venda.created_at,
    )
    return (
        db.query(
            VendaItem.produto_id.label("produto_id"),
            func.coalesce(func.sum(VendaItem.quantidade), 0).label("vendas_30d"),
        )
        .join(Venda, VendaItem.venda_id == Venda.id)
        .filter(
            Venda.tenant_id == tenant_id,
            VendaItem.tipo == "produto",
            Venda.status.notin_(["cancelada", "devolvida"]),
            venda_data >= data_inicio,
            venda_data <= data_fim,
        )
        .group_by(VendaItem.produto_id)
        .subquery()
    )


def _serializar_produto_catalogo(
    db: Session,
    *,
    produto: Produto,
    marca_nome: Optional[str],
    tenant_id,
    vendas_stats: dict | None,
) -> dict:
    estoque_atual, _estoque_info = _obter_estoque_atual_sugestao(
        db,
        produto,
        tenant_id,
    )
    metricas = montar_metricas_giro_catalogo(vendas_stats)
    situacao = calcular_situacao_estoque_catalogo(
        estoque_atual=estoque_atual,
        estoque_minimo=produto.estoque_minimo,
        vendas_30d=metricas["vendas_30d"],
    )
    return {
        "id": produto.id,
        "nome": produto.nome,
        "codigo": produto.codigo,
        "sku": _produto_sku_value(produto),
        "codigo_barras": produto.codigo_barras,
        "marca_nome": marca_nome,
        "tipo_produto": produto.tipo_produto,
        "estoque_atual": estoque_atual,
        "estoque_minimo": float(produto.estoque_minimo or 0),
        "preco_custo": float(produto.preco_custo or 0),
        **metricas,
        **situacao,
    }


@router.get("/catalogo-produtos")
@require_permission("produtos.visualizar")
def listar_catalogo_produtos_pedido(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=10, le=100),
    busca: Optional[str] = None,
    filtro: Literal["estoque_baixo", "todos"] = "estoque_baixo",
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Pesquisa todo o catalogo e devolve giro e risco com paginacao real."""
    _current_user, tenant_id = user_and_tenant
    termo_busca = (busca or "").strip()
    data_fim = datetime.now()
    vendas_30 = _subquery_vendas_30_dias(db, tenant_id, data_fim)
    vendas_30_expr = func.coalesce(vendas_30.c.vendas_30d, 0.0)
    estoque_atual_expr = func.coalesce(Produto.estoque_atual, 0.0)
    estoque_minimo_expr = func.coalesce(Produto.estoque_minimo, 0.0)
    limite_risco_expr = estoque_minimo_expr + (
        (vendas_30_expr / 30.0) * DIAS_RISCO_ESTOQUE
    )

    query = (
        db.query(
            Produto,
            Marca.nome.label("marca_nome"),
        )
        .outerjoin(Marca, Produto.marca_id == Marca.id)
        .outerjoin(vendas_30, vendas_30.c.produto_id == Produto.id)
        .filter(
            Produto.tenant_id == tenant_id,
            _filtro_ativo_ou_legado_sugestao(Produto.ativo),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            or_(Produto.tipo.is_(None), func.lower(Produto.tipo) != "servico"),
            or_(Produto.e_granel.is_(False), Produto.e_granel.is_(None)),
        )
    )

    for palavra in _palavras_busca_produto(termo_busca):
        query = query.filter(_produto_search_conditions(palavra))

    if filtro == "estoque_baixo":
        query = query.filter(estoque_atual_expr <= limite_risco_expr)
        query = query.order_by(
            (estoque_atual_expr - limite_risco_expr).asc(),
            Produto.nome.asc(),
        )
    else:
        query = query.order_by(*_build_produto_search_order_clause(termo_busca))

    total = query.count()
    pages = ceil(total / page_size) if total else 0
    pagina_atual = min(page, pages) if pages else 1
    rows = query.offset((pagina_atual - 1) * page_size).limit(page_size).all()
    produtos = [produto for produto, _marca_nome in rows]
    vendas_por_produto = _carregar_vendas_sugestao(
        db,
        tenant_id,
        [produto.id for produto in produtos],
        90,
        data_fim,
    )

    items = [
        _serializar_produto_catalogo(
            db,
            produto=produto,
            marca_nome=marca_nome,
            tenant_id=tenant_id,
            vendas_stats=vendas_por_produto.get(produto.id),
        )
        for produto, marca_nome in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": pagina_atual,
        "page_size": page_size,
        "pages": pages,
        "filtro": filtro,
        "dias_risco": DIAS_RISCO_ESTOQUE,
    }
