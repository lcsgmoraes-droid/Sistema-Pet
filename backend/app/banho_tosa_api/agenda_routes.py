from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.agenda_helpers import (
    buscar_agendamento_completo,
    buscar_atendimento_completo,
)
from app.banho_tosa_api.utils import (
    STATUS_AGENDAMENTO_FINAIS,
    calcular_total_servicos,
    serializar_agendamento,
    serializar_atendimento,
    validar_cliente_pet,
)
from app.banho_tosa_agenda_capacity import validar_capacidade_agenda
from app.banho_tosa_custos import validar_transicao_status
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAgendamentoServico,
    BanhoTosaAtendimento,
    BanhoTosaServico,
)
from app.banho_tosa_schemas import (
    BanhoTosaAgendamentoCreate,
    BanhoTosaAgendamentoResponse,
    BanhoTosaAgendamentoStatusUpdate,
    BanhoTosaAtendimentoResponse,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/agendamentos", response_model=List[BanhoTosaAgendamentoResponse])
def listar_agendamentos(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = (
        db.query(BanhoTosaAgendamento)
        .options(
            joinedload(BanhoTosaAgendamento.cliente),
            joinedload(BanhoTosaAgendamento.pet),
            joinedload(BanhoTosaAgendamento.recurso),
            joinedload(BanhoTosaAgendamento.servicos),
        )
        .filter(BanhoTosaAgendamento.tenant_id == tenant_id)
    )

    if data_inicio:
        query = query.filter(BanhoTosaAgendamento.data_hora_inicio >= datetime.combine(data_inicio, time.min))
    if data_fim:
        query = query.filter(BanhoTosaAgendamento.data_hora_inicio <= datetime.combine(data_fim, time.max))
    if status:
        query = query.filter(BanhoTosaAgendamento.status == status)

    agendamentos = query.order_by(BanhoTosaAgendamento.data_hora_inicio.asc()).limit(limit).all()
    return [serializar_agendamento(item) for item in agendamentos]


@router.post("/agendamentos", response_model=BanhoTosaAgendamentoResponse, status_code=201)
def criar_agendamento(
    body: BanhoTosaAgendamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    cliente, pet = validar_cliente_pet(db, tenant_id, body.cliente_id, body.pet_id)
    servicos_snapshot: list[BanhoTosaAgendamentoServico] = []
    duracao_total = 0

    for item in body.servicos:
        servico = None
        if item.servico_id:
            servico = db.query(BanhoTosaServico).filter(
                BanhoTosaServico.id == item.servico_id,
                BanhoTosaServico.tenant_id == tenant_id,
                BanhoTosaServico.ativo == True,
            ).first()
            if not servico:
                raise HTTPException(status_code=404, detail="Servico nao encontrado")

        nome_servico = item.nome_servico or (servico.nome if servico else None)
        if not nome_servico:
            raise HTTPException(status_code=422, detail="Informe o nome do servico")

        tempo_previsto = item.tempo_previsto_minutos
        if tempo_previsto is None and servico:
            tempo_previsto = servico.duracao_padrao_minutos
        tempo_previsto = int(tempo_previsto or 0)
        duracao_total += tempo_previsto

        servicos_snapshot.append(
            BanhoTosaAgendamentoServico(
                tenant_id=tenant_id,
                servico_id=servico.id if servico else None,
                nome_servico_snapshot=nome_servico,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                desconto=item.desconto,
                tempo_previsto_minutos=tempo_previsto,
            )
        )

    if duracao_total <= 0:
        duracao_total = 60

    fim_previsto = body.data_hora_fim_prevista or (body.data_hora_inicio + timedelta(minutes=duracao_total))
    if fim_previsto <= body.data_hora_inicio:
        raise HTTPException(status_code=422, detail="Fim previsto deve ser maior que o inicio")

    validar_capacidade_agenda(
        db,
        tenant_id,
        pet_id=body.pet_id,
        inicio=body.data_hora_inicio,
        fim=fim_previsto,
        profissional_principal_id=body.profissional_principal_id,
        banhista_id=body.banhista_id,
        tosador_id=body.tosador_id,
        recurso_id=body.recurso_id,
    )

    valor_previsto = body.valor_previsto
    if valor_previsto is None:
        valor_previsto = calcular_total_servicos(servicos_snapshot)

    agendamento = BanhoTosaAgendamento(
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        pet_id=pet.id,
        responsavel_agendamento_user_id=getattr(current_user, "id", None),
        profissional_principal_id=body.profissional_principal_id,
        banhista_id=body.banhista_id,
        tosador_id=body.tosador_id,
        recurso_id=body.recurso_id,
        data_hora_inicio=body.data_hora_inicio,
        data_hora_fim_prevista=fim_previsto,
        status="agendado",
        origem=body.origem,
        observacoes=body.observacoes,
        valor_previsto=valor_previsto,
        restricoes_veterinarias_snapshot={
            "alergias": pet.alergias_lista or [],
            "condicoes_cronicas": pet.condicoes_cronicas_lista or [],
            "medicamentos_continuos": pet.medicamentos_continuos_lista or [],
            "restricoes_alimentares": pet.restricoes_alimentares_lista or [],
        },
        perfil_comportamental_snapshot={
            "porte": pet.porte,
            "peso": pet.peso,
            "cor_pelagem": pet.cor_pelagem or pet.cor,
        },
    )
    agendamento.servicos = servicos_snapshot

    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)
    agendamento = buscar_agendamento_completo(db, tenant_id, agendamento.id)
    return serializar_agendamento(agendamento)


@router.patch("/agendamentos/{agendamento_id}/status", response_model=BanhoTosaAgendamentoResponse)
def atualizar_status_agendamento(
    agendamento_id: int,
    body: BanhoTosaAgendamentoStatusUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    agendamento = buscar_agendamento_completo(db, tenant_id, agendamento_id)
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")

    try:
        agendamento.status = validar_transicao_status(agendamento.status, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if body.observacoes is not None:
        agendamento.observacoes = body.observacoes

    db.commit()
    db.refresh(agendamento)
    return serializar_agendamento(agendamento)


@router.post("/agendamentos/{agendamento_id}/check-in", response_model=BanhoTosaAtendimentoResponse)
def realizar_checkin_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    agendamento = (
        db.query(BanhoTosaAgendamento)
        .options(joinedload(BanhoTosaAgendamento.pet), joinedload(BanhoTosaAgendamento.cliente))
        .filter(BanhoTosaAgendamento.id == agendamento_id, BanhoTosaAgendamento.tenant_id == tenant_id)
        .first()
    )
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")
    if agendamento.status in STATUS_AGENDAMENTO_FINAIS:
        raise HTTPException(status_code=422, detail="Agendamento finalizado nao pode receber check-in")

    atendimento = db.query(BanhoTosaAtendimento).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.agendamento_id == agendamento.id,
    ).first()

    if not atendimento:
        agora = datetime.now()
        pet = agendamento.pet
        atendimento = BanhoTosaAtendimento(
            tenant_id=tenant_id,
            agendamento_id=agendamento.id,
            cliente_id=agendamento.cliente_id,
            pet_id=agendamento.pet_id,
            status="chegou",
            checkin_em=agora,
            porte_snapshot=pet.porte if pet else None,
            pelagem_snapshot=(pet.cor_pelagem or pet.cor) if pet else None,
            observacoes_entrada=agendamento.observacoes,
        )
        db.add(atendimento)

    agendamento.status = "em_atendimento"
    db.commit()
    db.refresh(atendimento)
    atendimento = buscar_atendimento_completo(db, tenant_id, atendimento.id)
    return serializar_atendimento(atendimento)
