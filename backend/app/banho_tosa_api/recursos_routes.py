from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_models import BanhoTosaRecurso
from app.banho_tosa_schemas import (
    BanhoTosaRecursoCreate,
    BanhoTosaRecursoResponse,
    BanhoTosaRecursoUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/recursos", response_model=List[BanhoTosaRecursoResponse])
def listar_recursos(
    ativos_only: bool = Query(False),
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = db.query(BanhoTosaRecurso).filter(BanhoTosaRecurso.tenant_id == tenant_id)
    if ativos_only:
        query = query.filter(BanhoTosaRecurso.ativo == True)
    if tipo:
        query = query.filter(BanhoTosaRecurso.tipo == tipo)
    return query.order_by(BanhoTosaRecurso.tipo.asc(), BanhoTosaRecurso.nome.asc()).all()


@router.post("/recursos", response_model=BanhoTosaRecursoResponse, status_code=201)
def criar_recurso(
    body: BanhoTosaRecursoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    nome = body.nome.strip()
    tipo = body.tipo.strip().lower()
    existente = db.query(BanhoTosaRecurso).filter(
        BanhoTosaRecurso.tenant_id == tenant_id,
        func.lower(BanhoTosaRecurso.nome) == nome.lower(),
        BanhoTosaRecurso.tipo == tipo,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ja existe um recurso desse tipo com esse nome")

    recurso = BanhoTosaRecurso(tenant_id=tenant_id, **body.model_dump())
    recurso.nome = nome
    recurso.tipo = tipo
    db.add(recurso)
    db.commit()
    db.refresh(recurso)
    return recurso

@router.patch("/recursos/{recurso_id}", response_model=BanhoTosaRecursoResponse)
def atualizar_recurso(
    recurso_id: int,
    body: BanhoTosaRecursoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    recurso = db.query(BanhoTosaRecurso).filter(
        BanhoTosaRecurso.id == recurso_id,
        BanhoTosaRecurso.tenant_id == tenant_id,
    ).first()
    if not recurso:
        raise HTTPException(status_code=404, detail="Recurso nao encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "nome" in payload:
        payload["nome"] = (payload["nome"] or "").strip()
    if "tipo" in payload:
        payload["tipo"] = (payload["tipo"] or "").strip().lower()

    for campo, valor in payload.items():
        setattr(recurso, campo, valor)

    db.commit()
    db.refresh(recurso)
    return recurso
