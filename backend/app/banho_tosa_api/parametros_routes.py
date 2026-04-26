from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_models import (
    BanhoTosaInsumoPrevisto,
    BanhoTosaParametroPorte,
    BanhoTosaPrecoServico,
)
from app.banho_tosa_schemas import (
    BanhoTosaParametroPorteCreate,
    BanhoTosaParametroPorteResponse,
    BanhoTosaParametroPorteUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/parametros-porte", response_model=List[BanhoTosaParametroPorteResponse])
def listar_parametros_porte(
    ativos_only: bool = Query(False),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = db.query(BanhoTosaParametroPorte).filter(BanhoTosaParametroPorte.tenant_id == tenant_id)
    if ativos_only:
        query = query.filter(BanhoTosaParametroPorte.ativo == True)
    return query.order_by(BanhoTosaParametroPorte.peso_min_kg.asc().nullslast(), BanhoTosaParametroPorte.porte.asc()).all()


@router.post("/parametros-porte", response_model=BanhoTosaParametroPorteResponse, status_code=201)
def criar_parametro_porte(
    body: BanhoTosaParametroPorteCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    porte = body.porte.strip().lower()
    existente = db.query(BanhoTosaParametroPorte).filter(
        BanhoTosaParametroPorte.tenant_id == tenant_id,
        func.lower(BanhoTosaParametroPorte.porte) == porte,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ja existe um parametro para esse porte")

    parametro = BanhoTosaParametroPorte(tenant_id=tenant_id, **body.model_dump())
    parametro.porte = porte
    db.add(parametro)
    db.commit()
    db.refresh(parametro)
    return parametro


@router.delete("/parametros-porte/{porte_id}")
def excluir_parametro_porte(
    porte_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    parametro = db.query(BanhoTosaParametroPorte).filter(
        BanhoTosaParametroPorte.id == porte_id,
        BanhoTosaParametroPorte.tenant_id == tenant_id,
    ).first()
    if not parametro:
        raise HTTPException(status_code=404, detail="Parametro de porte nao encontrado")

    if _porte_tem_vinculos(db, tenant_id, porte_id):
        parametro.ativo = False
        db.commit()
        return {
            "deleted": False,
            "deactivated": True,
            "message": "Porte possui historico e foi desativado para preservar os registros.",
        }

    db.delete(parametro)
    db.commit()
    return {
        "deleted": True,
        "deactivated": False,
        "message": "Porte excluido.",
    }


def _porte_tem_vinculos(db: Session, tenant_id, porte_id: int) -> bool:
    checks = [
        db.query(BanhoTosaPrecoServico.id).filter(
            BanhoTosaPrecoServico.tenant_id == tenant_id,
            BanhoTosaPrecoServico.porte_id == porte_id,
        ),
        db.query(BanhoTosaInsumoPrevisto.id).filter(
            BanhoTosaInsumoPrevisto.tenant_id == tenant_id,
            BanhoTosaInsumoPrevisto.porte_id == porte_id,
        ),
    ]
    return any(query.first() is not None for query in checks)

@router.patch("/parametros-porte/{porte_id}", response_model=BanhoTosaParametroPorteResponse)
def atualizar_parametro_porte(
    porte_id: int,
    body: BanhoTosaParametroPorteUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    parametro = db.query(BanhoTosaParametroPorte).filter(
        BanhoTosaParametroPorte.id == porte_id,
        BanhoTosaParametroPorte.tenant_id == tenant_id,
    ).first()
    if not parametro:
        raise HTTPException(status_code=404, detail="Parametro de porte nao encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "porte" in payload:
        porte = (payload["porte"] or "").strip().lower()
        duplicado = db.query(BanhoTosaParametroPorte).filter(
            BanhoTosaParametroPorte.tenant_id == tenant_id,
            func.lower(BanhoTosaParametroPorte.porte) == porte,
            BanhoTosaParametroPorte.id != porte_id,
        ).first()
        if duplicado:
            raise HTTPException(status_code=409, detail="Ja existe um parametro para esse porte")
        payload["porte"] = porte

    for campo, valor in payload.items():
        setattr(parametro, campo, valor)

    db.commit()
    db.refresh(parametro)
    return parametro
