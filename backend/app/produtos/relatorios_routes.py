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

from .relatorios_validade_routes import router as validade_router
from .relatorios_validade_routes import relatorio_validade_proxima
from .relatorios_valorizacao_routes import router as valorizacao_router
from .relatorios_valorizacao_routes import relatorio_valorizacao_estoque

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


router.include_router(validade_router)
router.include_router(valorizacao_router)
