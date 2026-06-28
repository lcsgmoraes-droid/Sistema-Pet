"""Cadastros operacionais da agenda veterinaria."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Cliente
from ..veterinario_core import _get_tenant
from ..veterinario_models import AgendamentoVet, ConsultorioVet
from ..veterinario_schemas import (
    ConsultorioCreate,
    ConsultorioResponse,
    ConsultorioUpdate,
    VeterinarioSimples,
)

router = APIRouter()


@router.get("/veterinarios", response_model=List[VeterinarioSimples])
def listar_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista pessoas cadastradas como veterinário neste tenant (para selects nos formulários)."""
    user, tenant_id = _get_tenant(current)
    vets = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "veterinario",
            Cliente.ativo.is_(True),
        )
        .order_by(Cliente.nome)
        .all()
    )
    return [
        {
            "id": v.id,
            "nome": v.nome,
            "crmv": getattr(v, "crmv", None),
            "email": v.email,
            "telefone": v.telefone,
        }
        for v in vets
    ]


@router.get("/consultorios", response_model=List[ConsultorioResponse])
def listar_consultorios(
    ativos_only: bool = Query(False),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    q = db.query(ConsultorioVet).filter(ConsultorioVet.tenant_id == tenant_id)
    if ativos_only:
        q = q.filter(ConsultorioVet.ativo.is_(True))
    return q.order_by(ConsultorioVet.ordem.asc(), ConsultorioVet.nome.asc()).all()


@router.post("/consultorios", response_model=ConsultorioResponse, status_code=201)
def criar_consultorio(
    body: ConsultorioCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    nome = (body.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=422, detail="Informe o nome do consultorio")

    existente = (
        db.query(ConsultorioVet)
        .filter(
            ConsultorioVet.tenant_id == tenant_id,
            func.lower(ConsultorioVet.nome) == nome.lower(),
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=409, detail="Ja existe um consultorio com esse nome"
        )

    ultima_ordem = (
        db.query(func.max(ConsultorioVet.ordem))
        .filter(ConsultorioVet.tenant_id == tenant_id)
        .scalar()
        or 0
    )

    consultorio = ConsultorioVet(
        tenant_id=tenant_id,
        nome=nome,
        descricao=(body.descricao or "").strip() or None,
        ordem=body.ordem or (int(ultima_ordem) + 1),
        ativo=True,
    )
    db.add(consultorio)
    db.commit()
    db.refresh(consultorio)
    return consultorio


@router.patch("/consultorios/{consultorio_id}", response_model=ConsultorioResponse)
def atualizar_consultorio(
    consultorio_id: int,
    body: ConsultorioUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    consultorio = (
        db.query(ConsultorioVet)
        .filter(
            ConsultorioVet.id == consultorio_id,
            ConsultorioVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not consultorio:
        raise HTTPException(status_code=404, detail="Consultorio nao encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "nome" in payload:
        nome = (payload.get("nome") or "").strip()
        if not nome:
            raise HTTPException(status_code=422, detail="Informe o nome do consultorio")
        duplicado = (
            db.query(ConsultorioVet)
            .filter(
                ConsultorioVet.tenant_id == tenant_id,
                func.lower(ConsultorioVet.nome) == nome.lower(),
                ConsultorioVet.id != consultorio_id,
            )
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=409, detail="Ja existe um consultorio com esse nome"
            )
        consultorio.nome = nome

    if "descricao" in payload:
        consultorio.descricao = (payload.get("descricao") or "").strip() or None
    if "ordem" in payload and payload.get("ordem") is not None:
        consultorio.ordem = int(payload["ordem"])
    if "ativo" in payload and payload.get("ativo") is not None:
        consultorio.ativo = bool(payload["ativo"])

    db.commit()
    db.refresh(consultorio)
    return consultorio


@router.delete("/consultorios/{consultorio_id}", status_code=204)
def remover_consultorio(
    consultorio_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    consultorio = (
        db.query(ConsultorioVet)
        .filter(
            ConsultorioVet.id == consultorio_id,
            ConsultorioVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not consultorio:
        raise HTTPException(status_code=404, detail="Consultorio nao encontrado")

    agendamento_vinculado = (
        db.query(AgendamentoVet.id)
        .filter(
            AgendamentoVet.tenant_id == tenant_id,
            AgendamentoVet.consultorio_id == consultorio_id,
        )
        .first()
    )
    if agendamento_vinculado:
        raise HTTPException(
            status_code=409,
            detail="Esse consultorio ja possui agendamentos vinculados. Inative-o em vez de excluir.",
        )

    db.delete(consultorio)
    db.commit()
    return Response(status_code=204)
