# ruff: noqa: F401
"""Rotas de relatorios de produtos.

Mantem os mesmos caminhos publicados por ``produtos_routes.py`` e isola a
parte de relatorios para reduzir o tamanho do roteador principal.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.partner_utils import get_all_accessible_tenant_ids
from app.produtos.core import _produto_sku_value
from app.produtos.listagem import (
    _departamento_id_produto,
    _fornecedor_nome_produto,
    _mapa_reservas_ativas_multitenant,
    _nome_area_produto,
    _normalizar_paginacao_produtos,
    _palavras_busca_produto,
    _resolver_metricas_valorizacao_produto,
)
from app.produtos.relatorios import (
    _calcular_janelas_vendas_produto,
    _calcular_totais_validade_proxima,
    _detectar_promocao_venda_item,
    _mapear_promocoes_movimentacoes,
    _parse_relatorio_datetime,
    _serializar_movimentacao_relatorio,
)
from app.produtos.schemas import (
    RelatorioValidadeProximaItem,
    RelatorioValidadeProximaResponse,
    RelatorioValidadeProximaTotais,
    RelatorioValorizacaoEstoqueAreaResumo,
    RelatorioValorizacaoEstoqueItem,
    RelatorioValorizacaoEstoqueResponse,
    RelatorioValorizacaoEstoqueTotais,
)
from app.produtos.validade import (
    _calcular_faixa_campanha_validade,
    _calcular_status_validade,
)
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import (
    Categoria,
    EstoqueMovimentacao,
    Produto,
    ProdutoFornecedor,
    ProdutoLote,
)
from app.security.permissions_decorator import require_permission
from app.services.validade_campanha_service import (
    construir_oferta_validade,
    obter_configs_campanha_validade,
    obter_mapas_exclusao_validade,
)
from app.vendas_models import Venda, VendaItem

router = APIRouter()
PRODUTO_SKU_COLUMN = getattr(Produto, "sku", None)


@router.get(
    "/relatorio/valorizacao-estoque",
    response_model=RelatorioValorizacaoEstoqueResponse,
)
@require_permission("produtos.visualizar")
def relatorio_valorizacao_estoque(
    page: int = 1,
    page_size: int = 50,
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    departamento_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    incluir_kits_virtuais: bool = False,
    ativo: Optional[bool] = True,
    apenas_com_estoque: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Relatorio de valorizacao do estoque com totais agregados.

    Retorna os produtos filtrados com:
    - custo total em estoque
    - potencial de venda do estoque
    - margem potencial consolidada
    """
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    termo_busca = (busca or "").strip()
    page, page_size, offset = _normalizar_paginacao_produtos(
        page,
        page_size,
        max_page_size=200,
    )

    access_ids = get_all_accessible_tenant_ids(db, tenant_id)

    query = db.query(Produto).filter(
        Produto.tenant_id.in_(access_ids),
        or_(
            Produto.tipo_produto.is_(None),
            Produto.tipo_produto.in_(["SIMPLES", "KIT", "VARIACAO"]),
        ),
    )

    if not incluir_kits_virtuais:
        query = query.filter(
            or_(
                Produto.tipo_produto.is_(None),
                Produto.tipo_produto == "SIMPLES",
                and_(
                    Produto.tipo_produto.in_(["KIT", "VARIACAO"]),
                    or_(Produto.tipo_kit.is_(None), Produto.tipo_kit != "VIRTUAL"),
                ),
            )
        )

    if ativo is not None:
        if ativo:
            query = query.filter(or_(Produto.ativo.is_(True), Produto.ativo.is_(None)))
        else:
            query = query.filter(Produto.ativo.is_(False))

    if termo_busca:
        for palavra in _palavras_busca_produto(termo_busca):
            busca_pattern = f"%{palavra}%"
            if PRODUTO_SKU_COLUMN is None:
                query = query.filter(
                    or_(
                        Produto.nome.ilike(busca_pattern),
                        Produto.codigo.ilike(busca_pattern),
                        Produto.codigo_barras.ilike(busca_pattern),
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Produto.nome.ilike(busca_pattern),
                        Produto.codigo.ilike(busca_pattern),
                        PRODUTO_SKU_COLUMN.ilike(busca_pattern),
                        Produto.codigo_barras.ilike(busca_pattern),
                    )
                )

    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)

    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)

    if departamento_id:
        query = query.filter(
            or_(
                Produto.departamento_id == departamento_id,
                Produto.categoria.has(Categoria.departamento_id == departamento_id),
            )
        )

    if fornecedor_id:
        query = query.filter(
            or_(
                Produto.fornecedor_id == fornecedor_id,
                Produto.fornecedores_alternativos.any(
                    and_(
                        ProdutoFornecedor.fornecedor_id == fornecedor_id,
                        ProdutoFornecedor.ativo.is_(True),
                    )
                ),
            )
        )

    query = query.options(
        joinedload(Produto.categoria).joinedload(Categoria.departamento),
        joinedload(Produto.marca),
        joinedload(Produto.departamento),
        joinedload(Produto.fornecedor),
        joinedload(Produto.fornecedores_alternativos).joinedload(
            ProdutoFornecedor.fornecedor
        ),
    )

    reservas_por_produto = _mapa_reservas_ativas_multitenant(db, access_ids)
    produtos_filtrados = query.order_by(Produto.nome.asc()).all()

    resumo_areas: dict[str, dict] = {}
    itens_processados: list[dict] = []
    totais = {
        "total_produtos": 0,
        "total_itens_estoque": 0.0,
        "total_itens_reservados": 0.0,
        "total_itens_disponiveis": 0.0,
        "valor_custo_total": 0.0,
        "valor_venda_total": 0.0,
    }

    for produto in produtos_filtrados:
        if departamento_id and _departamento_id_produto(produto) != departamento_id:
            continue

        metricas = _resolver_metricas_valorizacao_produto(
            db,
            produto,
            reservas_por_produto=reservas_por_produto,
        )

        if apenas_com_estoque and metricas["estoque_atual"] <= 0:
            continue

        area_nome = _nome_area_produto(produto)
        fornecedor_nome = _fornecedor_nome_produto(produto)

        totais["total_produtos"] += 1
        totais["total_itens_estoque"] += metricas["estoque_atual"]
        totais["total_itens_reservados"] += metricas["estoque_reservado"]
        totais["total_itens_disponiveis"] += metricas["estoque_disponivel"]
        totais["valor_custo_total"] += metricas["valor_custo_total"]
        totais["valor_venda_total"] += metricas["valor_venda_total"]

        resumo_area = resumo_areas.setdefault(
            area_nome,
            {
                "area_nome": area_nome,
                "total_produtos": 0,
                "total_itens_estoque": 0.0,
                "total_itens_disponiveis": 0.0,
                "valor_custo_total": 0.0,
                "valor_venda_total": 0.0,
            },
        )
        resumo_area["total_produtos"] += 1
        resumo_area["total_itens_estoque"] += metricas["estoque_atual"]
        resumo_area["total_itens_disponiveis"] += metricas["estoque_disponivel"]
        resumo_area["valor_custo_total"] += metricas["valor_custo_total"]
        resumo_area["valor_venda_total"] += metricas["valor_venda_total"]

        itens_processados.append(
            {
                "id": produto.id,
                "codigo": produto.codigo,
                "sku": _produto_sku_value(produto),
                "nome": produto.nome,
                "categoria_nome": produto.categoria.nome if produto.categoria else None,
                "marca_nome": produto.marca.nome if produto.marca else None,
                "departamento_nome": area_nome if area_nome != "Sem setor" else None,
                "fornecedor_nome": fornecedor_nome,
                "tipo_produto": produto.tipo_produto,
                "tipo_kit": produto.tipo_kit,
                **metricas,
            }
        )

    itens_processados.sort(
        key=lambda item: (
            -float(item["valor_custo_total"] or 0.0),
            str(item["nome"] or "").lower(),
        )
    )

    total = len(itens_processados)
    pages = (total + page_size - 1) // page_size if total else 0
    pagina_items = itens_processados[offset : offset + page_size]

    areas = sorted(
        resumo_areas.values(),
        key=lambda area: (-float(area["valor_custo_total"] or 0.0), area["area_nome"]),
    )

    return RelatorioValorizacaoEstoqueResponse(
        items=[RelatorioValorizacaoEstoqueItem(**item) for item in pagina_items],
        areas=[RelatorioValorizacaoEstoqueAreaResumo(**area) for area in areas],
        totais=RelatorioValorizacaoEstoqueTotais(
            total_produtos=int(totais["total_produtos"]),
            total_itens_estoque=float(totais["total_itens_estoque"]),
            total_itens_reservados=float(totais["total_itens_reservados"]),
            total_itens_disponiveis=float(totais["total_itens_disponiveis"]),
            valor_custo_total=float(totais["valor_custo_total"]),
            valor_venda_total=float(totais["valor_venda_total"]),
            margem_potencial_total=float(
                totais["valor_venda_total"] - totais["valor_custo_total"]
            ),
            total_areas=len(areas),
        ),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
