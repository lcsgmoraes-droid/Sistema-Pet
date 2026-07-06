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
from app.produtos.search import _produto_search_conditions
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


@router.get(
    "/relatorio/validade-proxima",
    response_model=RelatorioValidadeProximaResponse,
)
@require_permission("produtos.visualizar")
def relatorio_validade_proxima(
    page: int = 1,
    page_size: int = 20,
    dias: int = 60,
    status_validade: str = "proximos",
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    departamento_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    apenas_com_estoque: bool = True,
    ordenacao: str = "validade_asc",
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Relatorio operacional de lotes com validade proxima.

    A resposta e paginada por lote para facilitar a conferencia comercial:
    - ordenacao padrao pela validade mais proxima
    - resumo consolidado dos lotes em risco
    - sugestao de faixa comercial (60/30/7 dias)
    """
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)
    termo_busca = (busca or "").strip()
    page, page_size, offset = _normalizar_paginacao_produtos(
        page,
        page_size,
        max_page_size=200,
    )
    dias = max(dias, 0)
    agora = datetime.utcnow()
    data_limite = agora + timedelta(days=dias)
    status_validade = (status_validade or "proximos").strip().lower()
    ordenacao = (ordenacao or "validade_asc").strip().lower()

    query_base = (
        db.query(ProdutoLote, Produto)
        .join(Produto, Produto.id == ProdutoLote.produto_id)
        .filter(
            Produto.tenant_id.in_(access_ids),
            ProdutoLote.data_validade.isnot(None),
            or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
        )
    )

    if apenas_com_estoque:
        query_base = query_base.filter(
            func.coalesce(ProdutoLote.quantidade_disponivel, 0) > 0
        )

    if termo_busca:
        for palavra in _palavras_busca_produto(termo_busca):
            busca_pattern = f"%{palavra}%"
            query_base = query_base.filter(
                or_(
                    _produto_search_conditions(palavra),
                    ProdutoLote.nome_lote.ilike(busca_pattern),
                )
            )

    if categoria_id:
        query_base = query_base.filter(Produto.categoria_id == categoria_id)

    if marca_id:
        query_base = query_base.filter(Produto.marca_id == marca_id)

    if departamento_id:
        query_base = query_base.filter(Produto.departamento_id == departamento_id)

    if fornecedor_id:
        query_base = query_base.filter(Produto.fornecedor_id == fornecedor_id)

    if status_validade == "vencidos":
        query_base = query_base.filter(ProdutoLote.data_validade < agora)
    elif status_validade == "todos":
        query_base = query_base.filter(ProdutoLote.data_validade <= data_limite)
    else:
        query_base = query_base.filter(
            ProdutoLote.data_validade >= agora,
            ProdutoLote.data_validade <= data_limite,
        )

    total = query_base.count()

    query = query_base.options(
        joinedload(Produto.categoria),
        joinedload(Produto.marca),
        joinedload(Produto.departamento),
        joinedload(Produto.fornecedor),
        joinedload(Produto.fornecedores_alternativos).joinedload(
            ProdutoFornecedor.fornecedor
        ),
    )

    if ordenacao == "validade_desc":
        query = query.order_by(ProdutoLote.data_validade.desc(), Produto.nome.asc())
    elif ordenacao == "quantidade_desc":
        query = query.order_by(
            func.coalesce(ProdutoLote.quantidade_disponivel, 0).desc(),
            ProdutoLote.data_validade.asc(),
        )
    elif ordenacao == "valor_desc":
        query = query.order_by(
            (
                func.coalesce(ProdutoLote.quantidade_disponivel, 0)
                * func.coalesce(ProdutoLote.custo_unitario, Produto.preco_custo, 0)
            ).desc(),
            ProdutoLote.data_validade.asc(),
        )
    else:
        query = query.order_by(ProdutoLote.data_validade.asc(), Produto.nome.asc())

    resultados = query.offset(offset).limit(page_size).all()

    resumo_rows = (
        query_base.with_entities(
            ProdutoLote.id,
            Produto.id,
            Produto.tenant_id,
            ProdutoLote.data_validade,
            func.coalesce(ProdutoLote.quantidade_disponivel, 0),
            func.coalesce(ProdutoLote.custo_unitario, Produto.preco_custo, 0),
            func.coalesce(Produto.preco_venda, 0),
        )
        .order_by(None)
        .all()
    )

    tenant_ids_resumo = {row[2] for row in resumo_rows if row[2]}
    tenant_ids_resultados = {
        produto.tenant_id for _, produto in resultados if produto.tenant_id
    }
    campaign_configs = obter_configs_campanha_validade(
        db,
        tenant_ids_resumo.union(tenant_ids_resultados),
    )
    exclusoes_produto, exclusoes_lote = obter_mapas_exclusao_validade(
        db,
        tenant_ids_resumo.union(tenant_ids_resultados),
        produto_ids={row[1] for row in resumo_rows},
    )

    items = []
    for lote, produto in resultados:
        dias_para_vencer = lote.dias_para_vencer
        custo_unitario = float(
            lote.custo_unitario
            if lote.custo_unitario is not None
            else produto.preco_custo or 0
        )
        preco_venda = float(produto.preco_venda or 0)
        quantidade_disponivel = float(lote.quantidade_disponivel or 0)
        departamento_nome = None
        if produto.departamento:
            departamento_nome = produto.departamento.nome
        elif produto.categoria and produto.categoria.departamento:
            departamento_nome = produto.categoria.departamento.nome

        fornecedor = produto.fornecedor
        if not fornecedor:
            vinculo_principal = next(
                (
                    vinculo
                    for vinculo in produto.fornecedores_alternativos
                    if vinculo.ativo and vinculo.e_principal and vinculo.fornecedor
                ),
                None,
            )
            vinculo_secundario = next(
                (
                    vinculo
                    for vinculo in produto.fornecedores_alternativos
                    if vinculo.ativo and vinculo.fornecedor
                ),
                None,
            )
            fornecedor = (
                vinculo_principal.fornecedor
                if vinculo_principal
                else vinculo_secundario.fornecedor
                if vinculo_secundario
                else None
            )

        tenant_key = str(produto.tenant_id)
        exclusao_produto = exclusoes_produto.get((tenant_key, int(produto.id)))
        exclusao_lote = exclusoes_lote.get((tenant_key, int(lote.id)))
        campanha_config = campaign_configs.get(tenant_key)
        oferta_app = construir_oferta_validade(
            produto,
            lote,
            "app",
            config=campanha_config,
            exclusao_produto=exclusao_produto,
            exclusao_lote=exclusao_lote,
        )
        oferta_ecommerce = construir_oferta_validade(
            produto,
            lote,
            "ecommerce",
            config=campanha_config,
            exclusao_produto=exclusao_produto,
            exclusao_lote=exclusao_lote,
        )
        campanha_canais = []
        if oferta_app.active:
            campanha_canais.append("app")
        if oferta_ecommerce.active:
            campanha_canais.append("ecommerce")
        preco_promocional_validade = (
            oferta_ecommerce.promotional_price
            if oferta_ecommerce.promotional_price is not None
            else oferta_app.promotional_price
        )
        percentual_desconto_validade = (
            oferta_ecommerce.percentual_desconto
            if oferta_ecommerce.percentual_desconto is not None
            else oferta_app.percentual_desconto
        )
        mensagem_promocional = oferta_ecommerce.message or oferta_app.message
        campanha_validade_ativa = bool(campanha_canais)
        campanha_validade_excluida = bool(exclusao_produto or exclusao_lote)

        items.append(
            RelatorioValidadeProximaItem(
                lote_id=lote.id,
                produto_id=produto.id,
                codigo=produto.codigo,
                sku=_produto_sku_value(produto),
                nome=produto.nome,
                categoria_nome=produto.categoria.nome if produto.categoria else None,
                marca_nome=produto.marca.nome if produto.marca else None,
                departamento_nome=departamento_nome,
                fornecedor_nome=fornecedor.nome if fornecedor else None,
                nome_lote=lote.nome_lote,
                data_validade=lote.data_validade,
                dias_para_vencer=int(dias_para_vencer or 0),
                quantidade_disponivel=quantidade_disponivel,
                custo_unitario=custo_unitario,
                preco_venda=preco_venda,
                valor_custo_lote=quantidade_disponivel * custo_unitario,
                valor_venda_lote=quantidade_disponivel * preco_venda,
                status_validade=_calcular_status_validade(dias_para_vencer),
                faixa_campanha=_calcular_faixa_campanha_validade(dias_para_vencer),
                promocao_ativa=bool(produto.promocao_ativa or campanha_validade_ativa),
                campanha_validade_ativa=campanha_validade_ativa,
                campanha_validade_excluida=campanha_validade_excluida,
                campanha_validade_exclusao_id=(
                    exclusao_lote.id
                    if exclusao_lote
                    else exclusao_produto.id
                    if exclusao_produto
                    else None
                ),
                campanha_validade_canais=campanha_canais,
                percentual_desconto_validade=percentual_desconto_validade,
                quantidade_promocional=quantidade_disponivel
                if campanha_validade_ativa
                else 0,
                preco_promocional_validade=preco_promocional_validade,
                preco_promocional_validade_app=oferta_app.promotional_price,
                preco_promocional_validade_ecommerce=oferta_ecommerce.promotional_price,
                mensagem_promocional=mensagem_promocional,
            )
        )

    totais = _calcular_totais_validade_proxima(
        resumo_rows,
        agora=agora,
        campaign_configs=campaign_configs,
        exclusoes_produto=exclusoes_produto,
        exclusoes_lote=exclusoes_lote,
    )

    pages = (total + page_size - 1) // page_size if total else 0

    return RelatorioValidadeProximaResponse(
        items=items,
        totais=RelatorioValidadeProximaTotais(**totais),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
