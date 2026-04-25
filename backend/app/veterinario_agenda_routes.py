"""Rotas de agenda e cadastros operacionais do modulo veterinario."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .models import Cliente, Pet, User
from .veterinario_agendamentos import (
    _agendamento_to_dict,
    _consulta_tem_conteudo_clinico,
    _consulta_tem_dependencias,
    _garantir_sem_conflitos_agendamento,
    _sincronizar_marcos_agendamento,
    _validar_consultorio_agendamento,
    _validar_veterinario_agendamento,
)
from .veterinario_calendar import (
    buscar_agendamentos_para_calendario,
    gerar_calendario_ics,
    gerar_token_calendario_vet,
    montar_payload_calendario_vet,
)
from .veterinario_clinico import _upsert_lembretes_push_agendamento
from .veterinario_core import _all_accessible_tenant_ids, _get_tenant
from .veterinario_models import AgendamentoVet, ConsultaVet, ConsultorioVet
from .veterinario_schemas import (
    AgendamentoCreate,
    AgendamentoResponse,
    AgendamentoUpdate,
    ConsultorioCreate,
    ConsultorioResponse,
    ConsultorioUpdate,
    VeterinarioSimples,
)

router = APIRouter()

# ═══════════════════════════════════════════════════════════════
# VETERINÁRIOS (listagem para seleção em formulários)
# ═══════════════════════════════════════════════════════════════

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
            Cliente.ativo == True,
        )
        .order_by(Cliente.nome)
        .all()
    )
    return [
        {"id": v.id, "nome": v.nome, "crmv": getattr(v, "crmv", None), "email": v.email, "telefone": v.telefone}
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
        q = q.filter(ConsultorioVet.ativo == True)
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

    existente = db.query(ConsultorioVet).filter(
        ConsultorioVet.tenant_id == tenant_id,
        func.lower(ConsultorioVet.nome) == nome.lower(),
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ja existe um consultorio com esse nome")

    ultima_ordem = db.query(func.max(ConsultorioVet.ordem)).filter(
        ConsultorioVet.tenant_id == tenant_id
    ).scalar() or 0

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
    consultorio = db.query(ConsultorioVet).filter(
        ConsultorioVet.id == consultorio_id,
        ConsultorioVet.tenant_id == tenant_id,
    ).first()
    if not consultorio:
        raise HTTPException(status_code=404, detail="Consultorio nao encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "nome" in payload:
        nome = (payload.get("nome") or "").strip()
        if not nome:
            raise HTTPException(status_code=422, detail="Informe o nome do consultorio")
        duplicado = db.query(ConsultorioVet).filter(
            ConsultorioVet.tenant_id == tenant_id,
            func.lower(ConsultorioVet.nome) == nome.lower(),
            ConsultorioVet.id != consultorio_id,
        ).first()
        if duplicado:
            raise HTTPException(status_code=409, detail="Ja existe um consultorio com esse nome")
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
    consultorio = db.query(ConsultorioVet).filter(
        ConsultorioVet.id == consultorio_id,
        ConsultorioVet.tenant_id == tenant_id,
    ).first()
    if not consultorio:
        raise HTTPException(status_code=404, detail="Consultorio nao encontrado")

    agendamento_vinculado = db.query(AgendamentoVet.id).filter(
        AgendamentoVet.tenant_id == tenant_id,
        AgendamentoVet.consultorio_id == consultorio_id,
    ).first()
    if agendamento_vinculado:
        raise HTTPException(
            status_code=409,
            detail="Esse consultorio ja possui agendamentos vinculados. Inative-o em vez de excluir.",
        )

    db.delete(consultorio)
    db.commit()
    return Response(status_code=204)


# ═══════════════════════════════════════════════════════════════
# PETS ACESSÍVEIS (próprio tenant + empresas parceiras)
# ═══════════════════════════════════════════════════════════════

@router.get("/pets")
def listar_pets_vet(
    busca: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista os pets acessíveis ao veterinário:
    - pets do próprio tenant (se tiver cadastros próprios)
    - pets de todas as empresas parceiras ativas vinculadas
    """
    user, tenant_id = _get_tenant(current)
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)

    q = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Cliente.tenant_id.in_(tenant_ids), Pet.ativo == True)
    )

    if cliente_id:
        q = q.filter(Pet.cliente_id == cliente_id)

    if busca:
        busca_term = f"%{busca}%"
        q = q.filter(
            or_(
                Pet.nome.ilike(busca_term),
                Pet.raca.ilike(busca_term),
                Cliente.nome.ilike(busca_term),
            )
        )

    pets = q.order_by(Pet.nome).limit(limit).all()

    return [
        {
            "id": p.id,
            "codigo": p.codigo,
            "cliente_id": p.cliente_id,
            "nome": p.nome,
            "especie": p.especie,
            "raca": p.raca,
            "sexo": p.sexo,
            "castrado": p.castrado,
            "data_nascimento": p.data_nascimento,
            "peso": p.peso,
            "porte": p.porte,
            "microchip": p.microchip,
            "alergias": p.alergias,
            "doencas_cronicas": p.doencas_cronicas,
            "medicamentos_continuos": p.medicamentos_continuos,
            "historico_clinico": p.historico_clinico,
            "observacoes": p.observacoes,
            "foto_url": p.foto_url,
            "ativo": p.ativo,
            "tenant_id": str(p.tenant_id),
            "cliente_nome": p.cliente.nome if p.cliente else None,
            "cliente_telefone": p.cliente.telefone if p.cliente else None,
            "cliente_celular": p.cliente.celular if p.cliente else None,
        }
        for p in pets
    ]


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
    return Response(content=conteudo, media_type="text/calendar; charset=utf-8", headers=headers)


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

    result = []
    for ag in agendamentos:
        d = {
            "id": ag.id,
            "pet_id": ag.pet_id,
            "cliente_id": ag.cliente_id,
            "veterinario_id": ag.veterinario_id,
            "consultorio_id": ag.consultorio_id,
            "data_hora": ag.data_hora,
            "duracao_minutos": ag.duracao_minutos,
            "tipo": ag.tipo,
            "motivo": ag.motivo,
            "status": ag.status,
            "is_emergencia": ag.is_emergencia,
            "consulta_id": ag.consulta_id,
            "observacoes": ag.observacoes,
            "created_at": ag.created_at,
        }
        if ag.pet:
            d["pet_nome"] = ag.pet.nome
        if ag.cliente:
            d["cliente_nome"] = ag.cliente.nome
        if ag.veterinario:
            d["veterinario_nome"] = ag.veterinario.nome
        if ag.consultorio:
            d["consultorio_nome"] = ag.consultorio.nome
        result.append(d)
    return result


@router.get("/agendamentos/{agendamento_id}/push-diagnostico")
def diagnostico_push_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    from app.campaigns.models import NotificationQueue

    cliente = db.query(Cliente).filter(
        Cliente.id == ag.cliente_id,
        Cliente.tenant_id == str(tenant_id),
    ).first()
    user_tutor = None
    if cliente and cliente.user_id:
        user_tutor = db.query(User).filter(
            User.id == cliente.user_id,
            User.tenant_id == str(tenant_id),
        ).first()

    prefixo = f"vet-agendamento:{ag.id}:"
    lembretes = db.query(NotificationQueue).filter(
        NotificationQueue.tenant_id == str(tenant_id),
        NotificationQueue.idempotency_key.like(f"{prefixo}%"),
    ).order_by(NotificationQueue.scheduled_at.asc(), NotificationQueue.created_at.desc()).all()

    return {
        "agendamento_id": ag.id,
        "pet_id": ag.pet_id,
        "cliente_id": ag.cliente_id,
        "data_hora": ag.data_hora.isoformat() if ag.data_hora else None,
        "status": ag.status,
        "tutor_tem_push_token": bool(getattr(user_tutor, "push_token", None)),
        "push_token_preview": f"{user_tutor.push_token[:18]}..." if getattr(user_tutor, "push_token", None) else None,
        "lembretes": [
            {
                "id": lembrete.id,
                "subject": lembrete.subject,
                "status": lembrete.status.value if hasattr(lembrete.status, "value") else str(lembrete.status),
                "scheduled_at": lembrete.scheduled_at.isoformat() if lembrete.scheduled_at else None,
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
        raise HTTPException(status_code=404, detail="Pet nao encontrado para este agendamento")

    cliente_id = body.cliente_id or pet_ref.cliente_id
    if cliente_id != pet_ref.cliente_id:
        raise HTTPException(status_code=422, detail="Tutor informado nao corresponde ao pet selecionado")

    _validar_veterinario_agendamento(db, tenant_id, body.veterinario_id)
    _validar_consultorio_agendamento(db, tenant_id, body.consultorio_id)
    _garantir_sem_conflitos_agendamento(
        db,
        tenant_id=tenant_id,
        data_hora=body.data_hora,
        duracao_minutos=body.duracao_minutos,
        veterinario_id=body.veterinario_id,
        consultorio_id=body.consultorio_id,
    )

    tenant_agendamento = tenant_id or getattr(pet_ref, "tenant_id", None)
    if tenant_agendamento is None:
        raise HTTPException(status_code=400, detail="Nao foi possivel identificar o tenant do agendamento")

    ag = AgendamentoVet(
        tenant_id=tenant_agendamento,
        pet_id=body.pet_id,
        cliente_id=cliente_id,
        veterinario_id=body.veterinario_id,
        consultorio_id=body.consultorio_id,
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
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
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
            raise HTTPException(status_code=404, detail="Pet nao encontrado para este agendamento")

        cliente_relacionado = cliente_id_novo or pet_ref.cliente_id
        if cliente_relacionado != pet_ref.cliente_id:
            raise HTTPException(status_code=422, detail="Tutor informado nao corresponde ao pet selecionado")

        ag.pet_id = pet_ref.id
        ag.cliente_id = cliente_relacionado
    elif cliente_id_novo is not None and cliente_id_novo != ag.cliente_id:
        raise HTTPException(status_code=422, detail="Para alterar o tutor, selecione tambem o pet correspondente")

    veterinario_id_novo = payload.get("veterinario_id", ag.veterinario_id)
    consultorio_id_novo = payload.get("consultorio_id", ag.consultorio_id)
    data_hora_nova = payload.get("data_hora", ag.data_hora)
    duracao_nova = payload.get("duracao_minutos", ag.duracao_minutos)

    _validar_veterinario_agendamento(db, tenant_id, veterinario_id_novo)
    _validar_consultorio_agendamento(db, tenant_id, consultorio_id_novo)
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
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
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


@router.post("/agendamentos/{agendamento_id}/desfazer-inicio", response_model=AgendamentoResponse)
def desfazer_inicio_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).options(
        joinedload(AgendamentoVet.consulta),
        joinedload(AgendamentoVet.pet),
        joinedload(AgendamentoVet.cliente),
        joinedload(AgendamentoVet.veterinario),
        joinedload(AgendamentoVet.consultorio),
    ).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")

    if ag.status == "finalizado":
        raise HTTPException(
            status_code=409,
            detail="Esse agendamento ja foi finalizado e nao pode voltar para agendado.",
        )

    consulta = None
    if ag.consulta_id:
        consulta = db.query(ConsultaVet).filter(
            ConsultaVet.id == ag.consulta_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()

    if consulta:
        if consulta.status == "finalizada":
            raise HTTPException(
                status_code=409,
                detail="Esse atendimento ja foi finalizado. Para excluir o agendamento, primeiro cancele ou trate o atendimento vinculado.",
            )
        if _consulta_tem_conteudo_clinico(consulta) or _consulta_tem_dependencias(db, tenant_id, consulta.id):
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
