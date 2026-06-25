"""Rotas de relatorios resumidos de vendas."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas_models import Venda

router = APIRouter()


@router.get("/relatorios/resumo")
def relatorio_resumo(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Relatório resumo de vendas"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    query = db.query(Venda).filter_by(tenant_id=tenant_id)

    if data_inicio:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
        data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0)
        query = query.filter(Venda.data_venda >= data_inicio_dt)

    if data_fim:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(Venda.data_venda <= data_fim_dt)

    vendas = query.all()

    # Calcular resumo
    total_vendas = len(vendas)
    total_valor = sum(float(v.total) for v in vendas if v.status != "cancelada")
    total_canceladas = sum(1 for v in vendas if v.status == "cancelada")

    # Por forma de pagamento
    pagamentos_resumo = {}
    for venda in vendas:
        if venda.status != "cancelada":
            for pag in venda.pagamentos:
                forma = pag.forma_pagamento
                if forma not in pagamentos_resumo:
                    pagamentos_resumo[forma] = 0
                pagamentos_resumo[forma] += float(pag.valor)

    return {
        "total_vendas": total_vendas,
        "total_valor": total_valor,
        "total_canceladas": total_canceladas,
        "pagamentos_resumo": pagamentos_resumo,
        "periodo": {
            "inicio": data_inicio if data_inicio else None,
            "fim": data_fim if data_fim else None,
        },
    }
