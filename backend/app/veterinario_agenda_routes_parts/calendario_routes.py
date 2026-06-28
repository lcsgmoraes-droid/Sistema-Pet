"""Rotas de calendario da agenda veterinaria."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import User
from ..veterinario_calendar import (
    buscar_agendamentos_para_calendario,
    gerar_calendario_ics,
    gerar_token_calendario_vet,
    montar_payload_calendario_vet,
)
from ..veterinario_core import _get_tenant

router = APIRouter()


@router.get("/agenda/calendario")
def obter_calendario_agenda_vet(
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)


@router.post("/agenda/calendario/token")
def regenerar_token_calendario_agenda_vet(
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    user.vet_calendar_token = gerar_token_calendario_vet(db)
    db.add(user)
    db.commit()
    db.refresh(user)
    return montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)


@router.get("/agenda/calendario.ics")
def baixar_calendario_agenda_vet(
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    payload = montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)
    agendamentos = buscar_agendamentos_para_calendario(
        db,
        tenant_id=tenant_id,
        veterinario_id=payload["veterinario_id"],
    )
    nome_calendario = (
        f"Agenda Vet - {payload['veterinario_nome']}"
        if payload["veterinario_nome"]
        else "Agenda Veterinaria"
    )
    conteudo = gerar_calendario_ics(agendamentos, nome_calendario=nome_calendario)
    headers = {
        "Content-Disposition": 'attachment; filename="agenda-veterinaria.ics"',
        "Cache-Control": "no-store",
    }
    return Response(
        content=conteudo, media_type="text/calendar; charset=utf-8", headers=headers
    )


@router.get("/agenda/feed/{token}.ics")
def feed_publico_calendario_agenda_vet(
    token: str,
    request: Request,
    db: Session = Depends(get_session),
):
    user = db.query(User).filter(User.vet_calendar_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Calendario nao encontrado")

    tenant_id = user.tenant_id
    payload = montar_payload_calendario_vet(db, request, user=user, tenant_id=tenant_id)
    agendamentos = buscar_agendamentos_para_calendario(
        db,
        tenant_id=tenant_id,
        veterinario_id=payload["veterinario_id"],
    )
    nome_calendario = (
        f"Agenda Vet - {payload['veterinario_nome']}"
        if payload["veterinario_nome"]
        else "Agenda Veterinaria"
    )
    conteudo = gerar_calendario_ics(agendamentos, nome_calendario=nome_calendario)
    return Response(content=conteudo, media_type="text/calendar; charset=utf-8")
