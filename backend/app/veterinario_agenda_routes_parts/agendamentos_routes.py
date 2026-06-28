"""CRUD e acoes operacionais de agendamentos veterinarios."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.services.push_devices import load_user_push_targets

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Cliente, Pet, User
from ..veterinario_agendamentos import (
    _agendamento_to_dict,
    _consulta_tem_conteudo_clinico,
    _consulta_tem_dependencias,
    _garantir_sem_conflitos_agendamento,
    _sincronizar_marcos_agendamento,
    _validar_consultorio_agendamento,
    _validar_veterinario_agendamento,
)
from ..veterinario_clinico import _upsert_lembretes_push_agendamento
from ..veterinario_core import _all_accessible_tenant_ids, _get_tenant
from ..veterinario_models import AgendamentoVet, ConsultaVet
from ..veterinario_schemas import (
    AgendamentoCreate,
    AgendamentoResponse,
    AgendamentoUpdate,
)

router = APIRouter()


def _validar_consulta_origem_agendamento(
    db: Session,
    *,
    tenant_id,
    consulta_origem_id: Optional[int],
    pet_id: Optional[int],
) -> Optional[ConsultaVet]:
    if not consulta_origem_id:
        return None
    if str(consulta_origem_id).strip() == "":
        return None

    consulta = (
        db.query(ConsultaVet)
        .filter(
            ConsultaVet.id == consulta_origem_id,
            ConsultaVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not consulta:
        raise HTTPException(
            status_code=422, detail="Consulta de origem do retorno nao foi encontrada"
        )
    if pet_id and consulta.pet_id != pet_id:
        raise HTTPException(
            status_code=422, detail="Consulta de origem nao pertence ao pet selecionado"
        )
    return consulta


@router.get("/agendamentos", response_model=List[AgendamentoResponse])
def listar_agendamentos(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    status: Optional[str] = None,
    pet_id: Optional[int] = None,
    veterinario_id: Optional[int] = None,
    consultorio_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = (
        db.query(AgendamentoVet)
        .options(
            joinedload(AgendamentoVet.pet),
            joinedload(AgendamentoVet.cliente),
            joinedload(AgendamentoVet.veterinario),
            joinedload(AgendamentoVet.consultorio),
        )
        .filter(AgendamentoVet.tenant_id == tenant_id)
    )

    if data_inicio:
        q = q.filter(func.date(AgendamentoVet.data_hora) >= data_inicio)
    if data_fim:
        q = q.filter(func.date(AgendamentoVet.data_hora) <= data_fim)
    if status:
        q = q.filter(AgendamentoVet.status == status)
    if pet_id:
        q = q.filter(AgendamentoVet.pet_id == pet_id)
    if veterinario_id:
        q = q.filter(AgendamentoVet.veterinario_id == veterinario_id)
    if consultorio_id:
        q = q.filter(AgendamentoVet.consultorio_id == consultorio_id)

    agendamentos = q.order_by(AgendamentoVet.data_hora).all()

    return [_agendamento_to_dict(ag) for ag in agendamentos]


@router.get("/agendamentos/{agendamento_id}/push-diagnostico")
def diagnostico_push_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = (
        db.query(AgendamentoVet)
        .filter(
            AgendamentoVet.id == agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    from app.campaigns.models import NotificationQueue

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == ag.cliente_id,
            Cliente.tenant_id == str(tenant_id),
        )
        .first()
    )
    user_tutor = None
    if cliente and cliente.user_id:
        user_tutor = (
            db.query(User)
            .filter(
                User.id == cliente.user_id,
                User.tenant_id == str(tenant_id),
            )
            .first()
        )
    push_targets = (
        load_user_push_targets(
            db,
            tenant_id=str(tenant_id),
            user_id=user_tutor.id,
            legacy_push_token=getattr(user_tutor, "push_token", None),
        )
        if user_tutor
        else []
    )
    push_token_preview = f"{push_targets[0].token[:18]}..." if push_targets else None

    prefixo = f"vet-agendamento:{ag.id}:"
    lembretes = (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.tenant_id == str(tenant_id),
            NotificationQueue.idempotency_key.like(f"{prefixo}%"),
        )
        .order_by(
            NotificationQueue.scheduled_at.asc(), NotificationQueue.created_at.desc()
        )
        .all()
    )

    return {
        "agendamento_id": ag.id,
        "pet_id": ag.pet_id,
        "cliente_id": ag.cliente_id,
        "data_hora": ag.data_hora.isoformat() if ag.data_hora else None,
        "status": ag.status,
        "tutor_tem_push_token": bool(push_targets),
        "push_token_preview": push_token_preview,
        "lembretes": [
            {
                "id": lembrete.id,
                "subject": lembrete.subject,
                "status": lembrete.status.value
                if hasattr(lembrete.status, "value")
                else str(lembrete.status),
                "scheduled_at": lembrete.scheduled_at.isoformat()
                if lembrete.scheduled_at
                else None,
            }
            for lembrete in lembretes
        ],
        "observacao": "Para validar push real no celular, o app precisa estar fora do Expo Go e com token registrado.",
    }


@router.post("/agendamentos", response_model=AgendamentoResponse, status_code=201)
def criar_agendamento(
    body: AgendamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
    pet_ref = (
        db.query(Pet)
        .join(Cliente, Cliente.id == Pet.cliente_id)
        .filter(
            Pet.id == body.pet_id,
            Cliente.tenant_id.in_(tenant_ids),
        )
        .first()
    )
    if not pet_ref:
        raise HTTPException(
            status_code=404, detail="Pet nao encontrado para este agendamento"
        )

    cliente_id = body.cliente_id or pet_ref.cliente_id
    if cliente_id != pet_ref.cliente_id:
        raise HTTPException(
            status_code=422, detail="Tutor informado nao corresponde ao pet selecionado"
        )

    _validar_veterinario_agendamento(db, tenant_id, body.veterinario_id)
    _validar_consultorio_agendamento(db, tenant_id, body.consultorio_id)
    _validar_consulta_origem_agendamento(
        db,
        tenant_id=tenant_id,
        consulta_origem_id=body.consulta_origem_id,
        pet_id=body.pet_id,
    )
    retorno_existente = None
    if body.tipo == "retorno" and body.consulta_origem_id:
        retorno_existente = (
            db.query(AgendamentoVet)
            .filter(
                AgendamentoVet.tenant_id == tenant_id,
                AgendamentoVet.consulta_origem_id == body.consulta_origem_id,
                AgendamentoVet.tipo == "retorno",
                AgendamentoVet.status.in_(["agendado", "confirmado", "aguardando"]),
            )
            .first()
        )

    _garantir_sem_conflitos_agendamento(
        db,
        tenant_id=tenant_id,
        data_hora=body.data_hora,
        duracao_minutos=body.duracao_minutos,
        veterinario_id=body.veterinario_id,
        consultorio_id=body.consultorio_id,
        agendamento_id_ignorar=retorno_existente.id if retorno_existente else None,
    )

    tenant_agendamento = tenant_id or getattr(pet_ref, "tenant_id", None)
    if tenant_agendamento is None:
        raise HTTPException(
            status_code=400,
            detail="Nao foi possivel identificar o tenant do agendamento",
        )

    if retorno_existente:
        retorno_existente.pet_id = body.pet_id
        retorno_existente.cliente_id = cliente_id
        retorno_existente.veterinario_id = body.veterinario_id
        retorno_existente.consultorio_id = body.consultorio_id
        retorno_existente.data_hora = body.data_hora
        retorno_existente.duracao_minutos = body.duracao_minutos
        retorno_existente.motivo = body.motivo
        retorno_existente.is_emergencia = body.is_emergencia
        retorno_existente.sintoma_emergencia = body.sintoma_emergencia
        retorno_existente.observacoes = body.observacoes
        _upsert_lembretes_push_agendamento(db, retorno_existente, tenant_id)
        db.commit()
        db.refresh(retorno_existente)
        return _agendamento_to_dict(retorno_existente)

    ag = AgendamentoVet(
        tenant_id=tenant_agendamento,
        pet_id=body.pet_id,
        cliente_id=cliente_id,
        veterinario_id=body.veterinario_id,
        consultorio_id=body.consultorio_id,
        consulta_origem_id=body.consulta_origem_id,
        user_id=user.id,
        data_hora=body.data_hora,
        duracao_minutos=body.duracao_minutos,
        tipo=body.tipo,
        motivo=body.motivo,
        is_emergencia=body.is_emergencia,
        sintoma_emergencia=body.sintoma_emergencia,
        observacoes=body.observacoes,
        status="agendado",
    )
    db.add(ag)
    db.flush()
    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


@router.patch("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
def atualizar_agendamento(
    agendamento_id: int,
    body: AgendamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    ag = (
        db.query(AgendamentoVet)
        .filter(
            AgendamentoVet.id == agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    payload = body.model_dump(exclude_unset=True)
    pet_id_novo = payload.pop("pet_id", None)
    cliente_id_novo = payload.pop("cliente_id", None)

    if pet_id_novo is not None:
        tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
        pet_ref = (
            db.query(Pet)
            .join(Cliente, Cliente.id == Pet.cliente_id)
            .filter(
                Pet.id == pet_id_novo,
                Cliente.tenant_id.in_(tenant_ids),
            )
            .first()
        )
        if not pet_ref:
            raise HTTPException(
                status_code=404, detail="Pet nao encontrado para este agendamento"
            )

        cliente_relacionado = cliente_id_novo or pet_ref.cliente_id
        if cliente_relacionado != pet_ref.cliente_id:
            raise HTTPException(
                status_code=422,
                detail="Tutor informado nao corresponde ao pet selecionado",
            )

        ag.pet_id = pet_ref.id
        ag.cliente_id = cliente_relacionado
    elif cliente_id_novo is not None and cliente_id_novo != ag.cliente_id:
        raise HTTPException(
            status_code=422,
            detail="Para alterar o tutor, selecione tambem o pet correspondente",
        )

    veterinario_id_novo = payload.get("veterinario_id", ag.veterinario_id)
    consultorio_id_novo = payload.get("consultorio_id", ag.consultorio_id)
    consulta_origem_id_nova = payload.get("consulta_origem_id", ag.consulta_origem_id)
    data_hora_nova = payload.get("data_hora", ag.data_hora)
    duracao_nova = payload.get("duracao_minutos", ag.duracao_minutos)

    _validar_veterinario_agendamento(db, tenant_id, veterinario_id_novo)
    _validar_consultorio_agendamento(db, tenant_id, consultorio_id_novo)
    _validar_consulta_origem_agendamento(
        db,
        tenant_id=tenant_id,
        consulta_origem_id=consulta_origem_id_nova,
        pet_id=ag.pet_id,
    )
    _garantir_sem_conflitos_agendamento(
        db,
        tenant_id=tenant_id,
        data_hora=data_hora_nova,
        duracao_minutos=duracao_nova,
        veterinario_id=veterinario_id_novo,
        consultorio_id=consultorio_id_novo,
        agendamento_id_ignorar=agendamento_id,
    )

    for field, value in payload.items():
        setattr(ag, field, value)

    _sincronizar_marcos_agendamento(ag)
    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


@router.delete("/agendamentos/{agendamento_id}", status_code=204)
def remover_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = (
        db.query(AgendamentoVet)
        .filter(
            AgendamentoVet.id == agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    if ag.consulta_id or ag.status == "finalizado":
        raise HTTPException(
            status_code=409,
            detail="Esse agendamento ja gerou um atendimento. Use 'Desfazer inicio do atendimento' primeiro. Se o atendimento ja tiver dados clinicos, exclua ou cancele o atendimento antes.",
        )

    try:
        from app.campaigns.models import NotificationQueue

        prefixo = f"vet-agendamento:{ag.id}:"
        db.query(NotificationQueue).filter(
            NotificationQueue.tenant_id == str(tenant_id),
            NotificationQueue.idempotency_key.like(f"{prefixo}%"),
        ).delete(synchronize_session=False)
    except Exception:
        pass

    db.delete(ag)
    db.commit()
    return Response(status_code=204)


@router.post(
    "/agendamentos/{agendamento_id}/desfazer-inicio", response_model=AgendamentoResponse
)
def desfazer_inicio_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = (
        db.query(AgendamentoVet)
        .options(
            joinedload(AgendamentoVet.consulta),
            joinedload(AgendamentoVet.pet),
            joinedload(AgendamentoVet.cliente),
            joinedload(AgendamentoVet.veterinario),
            joinedload(AgendamentoVet.consultorio),
        )
        .filter(
            AgendamentoVet.id == agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")

    if ag.status == "finalizado":
        raise HTTPException(
            status_code=409,
            detail="Esse agendamento ja foi finalizado e nao pode voltar para agendado.",
        )

    consulta = None
    if ag.consulta_id:
        consulta = (
            db.query(ConsultaVet)
            .filter(
                ConsultaVet.id == ag.consulta_id,
                ConsultaVet.tenant_id == tenant_id,
            )
            .first()
        )

    if consulta:
        if consulta.status == "finalizada":
            raise HTTPException(
                status_code=409,
                detail="Esse atendimento ja foi finalizado. Para excluir o agendamento, primeiro cancele ou trate o atendimento vinculado.",
            )
        if _consulta_tem_conteudo_clinico(consulta) or _consulta_tem_dependencias(
            db, tenant_id, consulta.id
        ):
            raise HTTPException(
                status_code=409,
                detail="Esse atendimento ja tem dados clinicos ou registros vinculados. Exclua/cancele o atendimento antes de voltar o agendamento.",
            )
        ag.consulta_id = None
        db.flush()
        db.delete(consulta)

    ag.status = "agendado"
    _sincronizar_marcos_agendamento(ag)
    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)
