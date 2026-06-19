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


# ==========================================
# ENDPOINTS - RELATÃ“RIOS
# ==========================================


@router.get("/relatorio/movimentacoes")
@require_permission("produtos.visualizar")
def relatorio_movimentacoes(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    produto_id: Optional[str] = None,
    tipo_movimentacao: Optional[str] = None,
    agrupar_por_mes: bool = False,
    page: int = 1,
    page_size: int = 20,
    export_all: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Relatorio operacional de movimentacoes de estoque.

    A resposta agora e paginada para manter a tela leve e os totais sao
    calculados sobre todo o filtro aplicado, nao apenas sobre a pagina atual.
    """

    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)
    page, page_size, offset = _normalizar_paginacao_produtos(
        page,
        page_size,
        max_page_size=200,
    )

    query = (
        db.query(EstoqueMovimentacao)
        .join(Produto)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            Produto.tenant_id.in_(access_ids),
        )
    )

    data_inicio_dt = _parse_relatorio_datetime(data_inicio)
    data_fim_dt = _parse_relatorio_datetime(data_fim, end_of_day=True)

    if data_inicio_dt:
        query = query.filter(EstoqueMovimentacao.created_at >= data_inicio_dt)

    if data_fim_dt:
        query = query.filter(EstoqueMovimentacao.created_at <= data_fim_dt)

    if not data_inicio_dt and not data_fim_dt:
        query = query.filter(
            EstoqueMovimentacao.created_at >= (datetime.now() - timedelta(days=90))
        )

    if produto_id and produto_id.strip():
        try:
            query = query.filter(EstoqueMovimentacao.produto_id == int(produto_id))
        except ValueError:
            pass

    if tipo_movimentacao and tipo_movimentacao != "todos":
        query = query.filter(EstoqueMovimentacao.tipo == tipo_movimentacao)

    total_registros = query.count()
    pages = (total_registros + page_size - 1) // page_size if total_registros else 0

    totais_row = query.with_entities(
        func.coalesce(
            func.sum(
                case(
                    (
                        EstoqueMovimentacao.tipo == "entrada",
                        EstoqueMovimentacao.quantidade,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case(
                    (
                        EstoqueMovimentacao.tipo != "entrada",
                        EstoqueMovimentacao.quantidade,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(func.sum(EstoqueMovimentacao.valor_total), 0),
    ).first()

    query = query.options(
        joinedload(EstoqueMovimentacao.produto),
        joinedload(EstoqueMovimentacao.user),
    ).order_by(EstoqueMovimentacao.created_at.desc(), EstoqueMovimentacao.id.desc())

    if not export_all:
        query = query.offset(offset).limit(page_size)

    movimentacoes_resultado = query.all()
    promocoes_por_chave = _mapear_promocoes_movimentacoes(
        db,
        tenant_id,
        movimentacoes_resultado,
    )
    resultado = [
        _serializar_movimentacao_relatorio(
            mov,
            promocoes_por_chave.get((int(mov.referencia_id), int(mov.produto_id)))
            if mov.referencia_id and mov.produto_id
            else None,
        )
        for mov in movimentacoes_resultado
    ]

    if agrupar_por_mes:
        agrupado = {}

        for item in resultado:
            data_item = _parse_relatorio_datetime(
                (item.get("data_completa") or "")[:10]
            )
            if not data_item:
                continue

            chave_mes = f"{data_item.year}-{data_item.month:02d}"

            if chave_mes not in agrupado:
                agrupado[chave_mes] = {
                    "mes": data_item.strftime("%B, %Y"),
                    "ano": data_item.year,
                    "total_vendas": 0,
                    "total_outras_saidas": 0,
                    "total_entradas": 0,
                    "movimentacoes": [],
                }

            if item["entrada"]:
                agrupado[chave_mes]["total_entradas"] += item["entrada"]
            elif (item.get("motivo") or "").lower() == "venda":
                agrupado[chave_mes]["total_vendas"] += item["saida"] or 0
            else:
                agrupado[chave_mes]["total_outras_saidas"] += item["saida"] or 0

            agrupado[chave_mes]["movimentacoes"].append(item)

        return {
            "total_registros": total_registros,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "totais": {
                "total_entradas": float(totais_row[0] or 0),
                "total_saidas": float(totais_row[1] or 0),
                "valor_total": float(totais_row[2] or 0),
            },
            "agrupado_por_mes": True,
            "meses": [
                agrupado[chave] for chave in sorted(agrupado.keys(), reverse=True)
            ],
        }

    return {
        "total_registros": total_registros,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "totais": {
            "total_entradas": float(totais_row[0] or 0),
            "total_saidas": float(totais_row[1] or 0),
            "valor_total": float(totais_row[2] or 0),
        },
        "agrupado_por_mes": False,
        "movimentacoes": resultado,
    }


@router.get("/relatorio/produto-vendas")
@require_permission("produtos.visualizar")
def relatorio_vendas_produto(
    produto_id: int,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Resumo de giro comercial de um produto para apoiar a compra.
    """

    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)
    page, page_size, offset = _normalizar_paginacao_produtos(
        page,
        page_size,
        max_page_size=50,
    )

    produto = (
        db.query(Produto)
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
        )
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id.in_(access_ids),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    data_fim_dt = _parse_relatorio_datetime(data_fim, end_of_day=True) or datetime.now()
    data_inicio_dt = _parse_relatorio_datetime(data_inicio) or (
        data_fim_dt - timedelta(days=89)
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    janela_90_inicio = (data_fim_dt - timedelta(days=89)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    janela_30_inicio = (data_fim_dt - timedelta(days=29)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    base_historico = (
        db.query(VendaItem)
        .join(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            VendaItem.produto_id == produto.id,
            VendaItem.tipo == "produto",
            Venda.status.notin_(["cancelada", "devolvida"]),
            Venda.data_venda >= data_inicio_dt,
            Venda.data_venda <= data_fim_dt,
        )
    )

    historico_total = base_historico.count()
    historico_pages = (
        (historico_total + page_size - 1) // page_size if historico_total else 0
    )

    historico_rows = (
        base_historico.options(
            joinedload(VendaItem.venda).joinedload(Venda.cliente),
            joinedload(VendaItem.produto),
        )
        .order_by(
            Venda.data_venda.desc(),
            Venda.numero_venda.desc(),
            VendaItem.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    historico = []
    for item in historico_rows:
        venda = item.venda
        info_promocao = _detectar_promocao_venda_item(item)
        historico.append(
            {
                "id": item.id,
                "venda_id": venda.id if venda else None,
                "numero_venda": venda.numero_venda if venda else None,
                "data_venda": venda.data_venda.isoformat()
                if venda and venda.data_venda
                else None,
                "cliente_nome": venda.cliente.nome
                if venda and venda.cliente
                else "Sem cliente",
                "status": venda.status if venda else None,
                "canal": venda.canal if venda else None,
                "quantidade": float(item.quantidade or 0),
                "preco_unitario": float(item.preco_unitario or 0),
                "subtotal": float(item.subtotal or 0),
                "em_promocao": bool(info_promocao.get("em_promocao")),
                "promocao_origem": info_promocao.get("promocao_origem"),
                "desconto_promocional": info_promocao.get("desconto_promocional", 0),
            }
        )

    analise_rows = (
        db.query(
            Venda.id.label("venda_id"),
            Venda.data_venda,
            VendaItem.quantidade,
            VendaItem.subtotal,
        )
        .join(VendaItem, VendaItem.venda_id == Venda.id)
        .filter(
            Venda.tenant_id == tenant_id,
            VendaItem.produto_id == produto.id,
            VendaItem.tipo == "produto",
            Venda.status.notin_(["cancelada", "devolvida"]),
            Venda.data_venda >= janela_90_inicio,
            Venda.data_venda <= data_fim_dt,
        )
        .all()
    )

    janelas, curva_30_dias = _calcular_janelas_vendas_produto(
        analise_rows,
        data_fim_dt=data_fim_dt,
        janela_30_inicio=janela_30_inicio,
    )

    ultima_venda_row = (
        db.query(
            Venda.id.label("venda_id"),
            Venda.numero_venda,
            Venda.data_venda,
            Cliente.nome.label("cliente_nome"),
            VendaItem.quantidade,
            VendaItem.preco_unitario,
        )
        .join(VendaItem, VendaItem.venda_id == Venda.id)
        .outerjoin(
            Cliente,
            Cliente.id == Venda.cliente_id,
        )
        .filter(
            Venda.tenant_id == tenant_id,
            VendaItem.produto_id == produto.id,
            VendaItem.tipo == "produto",
            Venda.status.notin_(["cancelada", "devolvida"]),
        )
        .order_by(
            Venda.data_venda.desc(),
            VendaItem.id.desc(),
        )
        .first()
    )

    ultima_venda = None
    dias_sem_vender = None
    if ultima_venda_row:
        dias_sem_vender = max(
            0, (data_fim_dt.date() - ultima_venda_row.data_venda.date()).days
        )
        ultima_venda = {
            "venda_id": ultima_venda_row.venda_id,
            "numero_venda": ultima_venda_row.numero_venda,
            "data_venda": ultima_venda_row.data_venda.isoformat()
            if ultima_venda_row.data_venda
            else None,
            "cliente_nome": ultima_venda_row.cliente_nome or "Sem cliente",
            "quantidade": float(ultima_venda_row.quantidade or 0),
            "preco_unitario": float(ultima_venda_row.preco_unitario or 0),
        }

    media_diaria_30 = float(janelas["30"]["media_diaria"] or 0)
    estoque_atual = float(produto.estoque_atual or 0)
    ruptura_ativa = estoque_atual <= 0
    estoque_para_cobertura = max(0.0, estoque_atual)
    cobertura_estimada_dias = (
        round(estoque_para_cobertura / media_diaria_30, 1)
        if media_diaria_30 > 0
        else None
    )

    return {
        "produto": {
            "id": produto.id,
            "nome": produto.nome,
            "codigo": produto.codigo,
            "sku": _produto_sku_value(produto),
            "codigo_barras": produto.codigo_barras,
            "estoque_atual": estoque_atual,
            "estoque_minimo": float(produto.estoque_minimo or 0),
            "preco_custo": float(produto.preco_custo or 0),
            "preco_venda": float(produto.preco_venda or 0),
            "categoria_nome": produto.categoria.nome if produto.categoria else None,
            "marca_nome": produto.marca.nome if produto.marca else None,
        },
        "resumo": {
            "data_referencia": data_fim_dt.isoformat(),
            "cobertura_estimada_dias": cobertura_estimada_dias,
            "ruptura_ativa": ruptura_ativa,
            "estoque_para_cobertura": estoque_para_cobertura,
            "media_diaria_30": round(media_diaria_30, 2),
            "quantidade_vendida_30": float(janelas["30"]["quantidade_vendida"] or 0),
            "quantidade_vendida_90": float(janelas["90"]["quantidade_vendida"] or 0),
            "dias_sem_vender": dias_sem_vender,
            "ultima_venda": ultima_venda,
        },
        "janelas": [janelas[str(dias)] for dias in (7, 15, 30, 60, 90)],
        "curva_30_dias": curva_30_dias,
        "historico_vendas": historico,
        "historico_total": historico_total,
        "historico_page": page,
        "historico_page_size": page_size,
        "historico_pages": historico_pages,
    }


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
            if PRODUTO_SKU_COLUMN is None:
                query_base = query_base.filter(
                    or_(
                        Produto.nome.ilike(busca_pattern),
                        Produto.codigo.ilike(busca_pattern),
                        Produto.codigo_barras.ilike(busca_pattern),
                        ProdutoLote.nome_lote.ilike(busca_pattern),
                    )
                )
            else:
                query_base = query_base.filter(
                    or_(
                        Produto.nome.ilike(busca_pattern),
                        Produto.codigo.ilike(busca_pattern),
                        PRODUTO_SKU_COLUMN.ilike(busca_pattern),
                        Produto.codigo_barras.ilike(busca_pattern),
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
