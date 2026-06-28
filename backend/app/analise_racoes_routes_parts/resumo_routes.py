# -*- coding: utf-8 -*-
"""Rotas de resumo do dashboard de analise de racoes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.analise_racoes_filters import (
    _produto_eh_racao_expr,
    _validar_tenant_e_obter_usuario,
)
from app.analise_racoes_schemas import DashboardResumo
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos_models import Marca, Produto
from app.vendas_models import Venda, VendaItem

router = APIRouter()


@router.get("/resumo", response_model=DashboardResumo)
async def obter_resumo_dashboard(
    data_inicio: Optional[str] = Query(
        None, description="Data início para vendas (YYYY-MM-DD)"
    ),
    data_fim: Optional[str] = Query(
        None, description="Data fim para vendas (YYYY-MM-DD)"
    ),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Resumo geral do dashboard de rações

    Retorna estatísticas gerais:
    - Total de rações cadastradas
    - Total classificadas
    - Faturamento do período
    - Margem média geral
    - Produto mais vendido
    - Segmento mais rentável
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Total de rações
    total_racoes = (
        db.query(func.count(Produto.id))
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            _produto_eh_racao_expr(),
        )
        .scalar()
        or 0
    )

    # Total classificadas (com pelo menos um campo preenchido)
    total_classificadas = (
        db.query(func.count(Produto.id))
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            _produto_eh_racao_expr(),
            or_(
                Produto.porte_animal.isnot(None),
                Produto.fase_publico.isnot(None),
                Produto.sabor_proteina.isnot(None),
                Produto.peso_embalagem.isnot(None),
            ),
        )
        .scalar()
        or 0
    )

    percentual_classificadas = (
        (total_classificadas / total_racoes * 100) if total_racoes > 0 else 0
    )

    # Marcas cadastradas
    marcas_cadastradas = (
        db.query(func.count(Marca.id.distinct()))
        .join(Produto, Produto.marca_id == Marca.id)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            _produto_eh_racao_expr(),
        )
        .scalar()
        or 0
    )

    # Margem média geral
    query_margem = db.query(
        func.avg(
            (Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100
        )
    ).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo.is_(True),
        _produto_eh_racao_expr(),
        Produto.preco_venda > 0,
    )
    margem_media = query_margem.scalar() or 0.0

    # Vendas do período (se especificado)
    faturamento_periodo = 0.0
    produto_mais_vendido = None

    if data_inicio and data_fim:
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")

        # Faturamento
        faturamento_periodo = (
            db.query(func.sum(VendaItem.preco_unitario * VendaItem.quantidade))
            .join(Venda, VendaItem.venda_id == Venda.id)
            .join(Produto, VendaItem.produto_id == Produto.id)
            .filter(
                Venda.tenant_id == tenant_id,
                _produto_eh_racao_expr(),
                Venda.data_venda >= dt_inicio,
                Venda.data_venda <= dt_fim,
                Venda.status != "cancelada",
            )
            .scalar()
            or 0.0
        )

        # Produto mais vendido
        mais_vendido = (
            db.query(
                Produto.id,
                Produto.nome,
                func.sum(VendaItem.quantidade).label("total_vendido"),
            )
            .join(VendaItem, VendaItem.produto_id == Produto.id)
            .join(Venda, VendaItem.venda_id == Venda.id)
            .filter(
                Venda.tenant_id == tenant_id,
                _produto_eh_racao_expr(),
                Venda.data_venda >= dt_inicio,
                Venda.data_venda <= dt_fim,
                Venda.status != "cancelada",
            )
            .group_by(Produto.id, Produto.nome)
            .order_by(desc("total_vendido"))
            .first()
        )

        if mais_vendido:
            produto_mais_vendido = {
                "id": mais_vendido.id,
                "nome": mais_vendido.nome,
                "quantidade": float(mais_vendido.total_vendido),
            }

    # Segmento mais rentável (por porte)
    segmento_rentavel = (
        db.query(
            Produto.porte_animal,
            func.avg(
                (Produto.preco_venda - Produto.preco_custo) / Produto.preco_venda * 100
            ).label("margem_media"),
        )
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            _produto_eh_racao_expr(),
            Produto.porte_animal.isnot(None),
            Produto.preco_venda > 0,
        )
        .group_by(Produto.porte_animal)
        .order_by(desc("margem_media"))
        .first()
    )

    segmento_mais_rentavel = None
    if segmento_rentavel and segmento_rentavel.porte_animal:
        segmento_mais_rentavel = {
            "segmento": str(segmento_rentavel.porte_animal),
            "margem_media": float(segmento_rentavel.margem_media),
        }

    return DashboardResumo(
        total_racoes=total_racoes,
        total_classificadas=total_classificadas,
        percentual_classificadas=round(percentual_classificadas, 2),
        marcas_cadastradas=marcas_cadastradas,
        faturamento_periodo=float(faturamento_periodo),
        margem_media_geral=round(float(margem_media), 2),
        produto_mais_vendido=produto_mais_vendido,
        segmento_mais_rentavel=segmento_mais_rentavel,
    )
