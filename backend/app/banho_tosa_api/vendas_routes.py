from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_schemas import (
    BanhoTosaFechamentoPendenciasResponse,
    BanhoTosaFechamentoSincronizacaoLoteResponse,
    BanhoTosaFechamentoSyncResponse,
    BanhoTosaVendaAtendimentoResponse,
)
from app.banho_tosa_fechamento import (
    listar_pendencias_fechamento,
    sincronizar_fechamento_atendimento,
    sincronizar_pendencias_fechamento,
)
from app.banho_tosa_vendas import gerar_venda_atendimento
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/fechamentos/pendencias", response_model=BanhoTosaFechamentoPendenciasResponse)
def listar_pendencias_de_fechamento(
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return listar_pendencias_fechamento(db, tenant_id, limit=limit)


@router.post(
    "/fechamentos/pendencias/sincronizar",
    response_model=BanhoTosaFechamentoSincronizacaoLoteResponse,
)
def sincronizar_pendencias_de_fechamento(
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return sincronizar_pendencias_fechamento(db, tenant_id, limit=limit)


@router.post(
    "/atendimentos/{atendimento_id}/venda",
    response_model=BanhoTosaVendaAtendimentoResponse,
)
def gerar_venda_para_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    return gerar_venda_atendimento(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        atendimento_id=atendimento_id,
    )


@router.post(
    "/atendimentos/{atendimento_id}/fechamento/sincronizar",
    response_model=BanhoTosaFechamentoSyncResponse,
)
def sincronizar_fechamento_do_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return sincronizar_fechamento_atendimento(db, tenant_id, atendimento_id)
