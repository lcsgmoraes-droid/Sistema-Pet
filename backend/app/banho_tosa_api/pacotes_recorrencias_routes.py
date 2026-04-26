from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.pacotes_helpers import (
    obter_credito,
    query_recorrencias,
    serializar_recorrencia,
    validar_cliente_pet_credito,
    validar_servico,
)
from app.banho_tosa_models import BanhoTosaRecorrencia
from app.banho_tosa_schemas import (
    BanhoTosaRecorrenciaCreate,
    BanhoTosaRecorrenciaResponse,
    BanhoTosaRecorrenciaUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/pacotes/recorrencias", response_model=List[BanhoTosaRecorrenciaResponse])
def listar_recorrencias(
    ativos_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = query_recorrencias(db, tenant_id)
    if ativos_only:
        query = query.filter(BanhoTosaRecorrencia.ativo == True)
    itens = query.order_by(BanhoTosaRecorrencia.proxima_execucao.asc()).limit(limit).all()
    return [serializar_recorrencia(item) for item in itens]


@router.post("/pacotes/recorrencias", response_model=BanhoTosaRecorrenciaResponse, status_code=201)
def criar_recorrencia(
    body: BanhoTosaRecorrenciaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    validar_cliente_pet_credito(db, tenant_id, body.cliente_id, body.pet_id)
    validar_servico(db, tenant_id, body.servico_id)
    if body.pacote_credito_id:
        obter_credito(db, tenant_id, body.pacote_credito_id)
    recorrencia = BanhoTosaRecorrencia(tenant_id=tenant_id, **body.model_dump(), ativo=True)
    db.add(recorrencia)
    db.commit()
    db.refresh(recorrencia)
    item = query_recorrencias(db, tenant_id).filter(BanhoTosaRecorrencia.id == recorrencia.id).first()
    return serializar_recorrencia(item)


@router.patch("/pacotes/recorrencias/{recorrencia_id}", response_model=BanhoTosaRecorrenciaResponse)
def atualizar_recorrencia(
    recorrencia_id: int,
    body: BanhoTosaRecorrenciaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    recorrencia = query_recorrencias(db, tenant_id).filter(BanhoTosaRecorrencia.id == recorrencia_id).first()
    if not recorrencia:
        raise HTTPException(status_code=404, detail="Recorrencia nao encontrada.")
    payload = body.model_dump(exclude_unset=True)
    if "servico_id" in payload:
        validar_servico(db, tenant_id, payload["servico_id"])
    if payload.get("pacote_credito_id"):
        obter_credito(db, tenant_id, payload["pacote_credito_id"])
    for campo, valor in payload.items():
        setattr(recorrencia, campo, valor)
    db.commit()
    db.refresh(recorrencia)
    return serializar_recorrencia(recorrencia)
