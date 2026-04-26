from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_agenda_capacity import montar_capacidade_dia
from app.banho_tosa_agenda_slots import sugerir_slots_agenda
from app.banho_tosa_schemas import (
    BanhoTosaCapacidadeDiaResponse,
    BanhoTosaSlotSugestaoResponse,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/agendamentos/capacidade", response_model=BanhoTosaCapacidadeDiaResponse)
def obter_capacidade_agenda(
    data_referencia: date = Query(...),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return montar_capacidade_dia(db, tenant_id, data_referencia)


@router.get("/agendamentos/sugestoes-slots", response_model=list[BanhoTosaSlotSugestaoResponse])
def obter_sugestoes_slots(
    data_referencia: date = Query(...),
    duracao_minutos: int = Query(60, ge=5, le=720),
    recurso_id: int | None = Query(None, gt=0),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return sugerir_slots_agenda(
        db,
        tenant_id,
        data_ref=data_referencia,
        duracao_minutos=duracao_minutos,
        recurso_id=recurso_id,
        limit=limit,
    )
