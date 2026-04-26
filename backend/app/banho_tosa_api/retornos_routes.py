from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_retornos import (
    avancar_recorrencia,
    listar_sugestoes_retorno,
)
from app.banho_tosa_retornos_notificacoes import enfileirar_notificacoes_retorno
from app.banho_tosa_schemas import (
    BanhoTosaNotificarRetornosInput,
    BanhoTosaNotificarRetornosResponse,
    BanhoTosaRecorrenciaAvancarInput,
    BanhoTosaRetornosResponse,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/retornos/sugestoes", response_model=BanhoTosaRetornosResponse)
def listar_retornos_sugeridos(
    dias: int = Query(30, ge=0, le=365),
    sem_banho_dias: int = Query(45, ge=7, le=365),
    pacote_vencendo_dias: int = Query(15, ge=0, le=365),
    saldo_baixo_creditos: int = Query(1, ge=0, le=20),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return listar_sugestoes_retorno(
        db,
        tenant_id,
        dias=dias,
        sem_banho_dias=sem_banho_dias,
        pacote_vencendo_dias=pacote_vencendo_dias,
        saldo_baixo_creditos=saldo_baixo_creditos,
        limit=limit,
    )


@router.post("/retornos/recorrencias/{recorrencia_id}/avancar")
def avancar_retornos_recorrencia(
    recorrencia_id: int,
    body: BanhoTosaRecorrenciaAvancarInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return avancar_recorrencia(
        db,
        tenant_id,
        recorrencia_id,
        data_base=body.data_base,
        observacoes=body.observacoes,
    )


@router.post("/retornos/notificacoes/enfileirar", response_model=BanhoTosaNotificarRetornosResponse)
def enfileirar_notificacoes(
    body: BanhoTosaNotificarRetornosInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return enfileirar_notificacoes_retorno(
        db,
        tenant_id,
        tipos=body.tipos,
        dias_antecedencia=body.dias_antecedencia,
        limit=body.limit,
        canal=body.canal,
        template_id=body.template_id,
    )
