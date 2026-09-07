"""Consulta autenticada dos recebimentos vinculados a vendas."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.recebimentos_vendas_service import montar_relatorio_recebimentos
from app.relatorio_vendas_common import _normalizar_canal_venda_relatorio
from app.security.permissions_decorator import require_permission_dependency

router = APIRouter(
    dependencies=[Depends(require_permission_dependency("relatorios.financeiro"))]
)


@router.get("/vendas/recebimentos")
def relatorio_recebimentos_vendas(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    canal_venda: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    if data_fim < data_inicio or (data_fim - data_inicio).days > 365:
        raise HTTPException(
            400,
            "Selecione um período de até 366 dias, com início anterior ou igual ao fim.",
        )
    _user, tenant_id = user_and_tenant
    return montar_relatorio_recebimentos(
        db,
        tenant_id,
        data_inicio,
        data_fim,
        _normalizar_canal_venda_relatorio(canal_venda),
    )


@router.get("/vendas/recebimentos/pdf")
def exportar_recebimentos_pdf(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    canal_venda: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    from app.financeiro.recebimentos_vendas_pdf import gerar_pdf_recebimentos

    relatorio = relatorio_recebimentos_vendas(
        data_inicio, data_fim, canal_venda, db, user_and_tenant
    )
    return StreamingResponse(
        gerar_pdf_recebimentos(relatorio, canal_venda),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="recebimentos_{data_inicio}_{data_fim}.pdf"'
        },
    )
