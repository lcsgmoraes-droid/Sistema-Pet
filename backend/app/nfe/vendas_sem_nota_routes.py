"""Vendas finalizadas que ainda não possuem tentativa de emissão fiscal."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.vendas_models import Venda

router = APIRouter()


@router.get("/vendas-sem-nota")
def listar_vendas_sem_nota(
    data_inicial: date,
    data_final: date,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    if data_final < data_inicial:
        raise HTTPException(
            422, "A data final deve ser igual ou posterior à data inicial."
        )

    _, tenant_id = user_and_tenant
    query = (
        db.query(
            Venda.id,
            Venda.numero_venda,
            Venda.data_venda,
            Cliente.nome.label("cliente_nome"),
            Venda.total,
        )
        .outerjoin(
            Cliente,
            (Cliente.id == Venda.cliente_id) & (Cliente.tenant_id == tenant_id),
        )
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.status == "finalizada",
            Venda.data_venda >= datetime.combine(data_inicial, time.min),
            Venda.data_venda
            < datetime.combine(data_final + timedelta(days=1), time.min),
            Venda.nfe_correlation_id.is_(None),
            Venda.nfe_idempotency_key.is_(None),
            Venda.nfe_bling_id.is_(None),
            Venda.nfe_numero.is_(None),
            Venda.nfe_chave.is_(None),
            Venda.nfe_status.is_(None),
        )
    )
    total = query.count()
    vendas = (
        query.order_by(Venda.data_venda.desc(), Venda.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "vendas": [
            {
                "id": venda.id,
                "numero_venda": venda.numero_venda,
                "data_venda": venda.data_venda.isoformat(),
                "cliente_nome": venda.cliente_nome,
                "total": float(venda.total),
            }
            for venda in vendas
        ],
    }
