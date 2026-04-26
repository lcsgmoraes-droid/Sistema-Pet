from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_relatorios import gerar_relatorio_operacional
from app.banho_tosa_schemas import BanhoTosaRelatorioOperacionalResponse
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/relatorios/operacional", response_model=BanhoTosaRelatorioOperacionalResponse)
def relatorio_operacional_banho_tosa(
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    fim = data_fim or date.today()
    inicio = data_inicio or (fim - timedelta(days=30))
    if inicio > fim:
        inicio, fim = fim, inicio
    return gerar_relatorio_operacional(db, tenant_id, inicio, fim)
