from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_models import BanhoTosaServico
from app.banho_tosa_schemas import (
    BanhoTosaServicoCreate,
    BanhoTosaServicoResponse,
    BanhoTosaServicoUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/servicos", response_model=List[BanhoTosaServicoResponse])
def listar_servicos(
    ativos_only: bool = Query(False),
    categoria: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = db.query(BanhoTosaServico).filter(BanhoTosaServico.tenant_id == tenant_id)
    if ativos_only:
        query = query.filter(BanhoTosaServico.ativo == True)
    if categoria:
        query = query.filter(BanhoTosaServico.categoria == categoria)
    return query.order_by(BanhoTosaServico.categoria.asc(), BanhoTosaServico.nome.asc()).all()


@router.post("/servicos", response_model=BanhoTosaServicoResponse, status_code=201)
def criar_servico(
    body: BanhoTosaServicoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    nome = body.nome.strip()
    existente = db.query(BanhoTosaServico).filter(
        BanhoTosaServico.tenant_id == tenant_id,
        func.lower(BanhoTosaServico.nome) == nome.lower(),
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ja existe um servico de Banho & Tosa com esse nome")

    servico = BanhoTosaServico(tenant_id=tenant_id, **body.model_dump())
    servico.nome = nome
    db.add(servico)
    db.commit()
    db.refresh(servico)
    return servico

@router.patch("/servicos/{servico_id}", response_model=BanhoTosaServicoResponse)
def atualizar_servico(
    servico_id: int,
    body: BanhoTosaServicoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    servico = db.query(BanhoTosaServico).filter(
        BanhoTosaServico.id == servico_id,
        BanhoTosaServico.tenant_id == tenant_id,
    ).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Servico de Banho & Tosa nao encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "nome" in payload:
        nome = (payload["nome"] or "").strip()
        duplicado = db.query(BanhoTosaServico).filter(
            BanhoTosaServico.tenant_id == tenant_id,
            func.lower(BanhoTosaServico.nome) == nome.lower(),
            BanhoTosaServico.id != servico_id,
        ).first()
        if duplicado:
            raise HTTPException(status_code=409, detail="Ja existe um servico de Banho & Tosa com esse nome")
        payload["nome"] = nome

    for campo, valor in payload.items():
        setattr(servico, campo, valor)

    db.commit()
    db.refresh(servico)
    return servico
