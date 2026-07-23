"""Agenda de procedimentos da internacao veterinaria."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..veterinario_core import _get_tenant, _normalizar_datetime_local_brasilia
from ..veterinario_financeiro import _as_float
from ..veterinario_internacao import (
    _build_payload_procedimento_agenda_internacao,
    _build_procedimento_observacao,
    _garantir_internacao_ativa,
    _resolver_tenant_id_vet,
    _resolver_user_id_vet,
    _serializar_procedimento_agenda_internacao,
)
from ..veterinario_models import (
    EvolucaoInternacao,
    InternacaoProcedimentoAgenda,
    InternacaoVet,
)
from ..veterinario_schemas import (
    ProcedimentoAgendaInternacaoConcluir,
    ProcedimentoAgendaInternacaoCreate,
)

router = APIRouter()


@router.get("/internacoes/procedimentos-agenda")
def listar_procedimentos_agenda_internacao(
    status: Optional[str] = Query("ativos"),
    internacao_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(
        user, tenant_id, "Tenant nao identificado para agenda de internacao"
    )

    status_normalizado = (status or "ativos").strip().lower()
    if status_normalizado in {"", "ativos", "ativo"}:
        status_filtro = ["agendado", "concluido"]
    elif status_normalizado in {"pendente", "pendentes", "agendado"}:
        status_filtro = ["agendado"]
    elif status_normalizado in {"feito", "feitos", "concluido", "concluidos"}:
        status_filtro = ["concluido"]
    elif status_normalizado in {"cancelado", "cancelados"}:
        status_filtro = ["cancelado"]
    else:
        raise HTTPException(
            status_code=422, detail="Status da agenda de internacao invalido"
        )

    query = (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .filter(
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
            InternacaoProcedimentoAgenda.status.in_(status_filtro),
        )
    )
    if internacao_id:
        query = query.filter(
            InternacaoProcedimentoAgenda.internacao_id == internacao_id
        )

    itens = query.order_by(InternacaoProcedimentoAgenda.horario_agendado.asc()).all()
    return [_serializar_procedimento_agenda_internacao(item) for item in itens]


@router.post("/internacoes/{internacao_id}/procedimentos-agenda", status_code=201)
def criar_procedimento_agenda_internacao(
    internacao_id: int,
    body: ProcedimentoAgendaInternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(
        user, tenant_id, "Tenant nao identificado para agenda de internacao"
    )
    user_id = _resolver_user_id_vet(user, "Usuario invalido para agenda de internacao")

    internacao = (
        db.query(InternacaoVet)
        .options(joinedload(InternacaoVet.pet))
        .filter(
            InternacaoVet.id == internacao_id,
            InternacaoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not internacao:
        raise HTTPException(404, "Internacao nao encontrada")
    if internacao.status != "internado":
        raise HTTPException(
            status_code=409,
            detail="Agenda de procedimento so pode ser criada para internacao ativa",
        )

    medicamento = (body.medicamento or "").strip()
    if not medicamento:
        raise HTTPException(
            status_code=422, detail="Medicamento/procedimento e obrigatorio"
        )

    horario_agendado = _normalizar_datetime_local_brasilia(body.horario_agendado)
    if not horario_agendado:
        raise HTTPException(status_code=422, detail="Horario agendado e obrigatorio")

    quantidade_prevista = _as_float(body.quantidade_prevista)
    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(
            status_code=422, detail="Quantidade prevista nao pode ser negativa"
        )

    item = InternacaoProcedimentoAgenda(
        tenant_id=tenant_id,
        user_id=user_id,
        internacao_id=internacao.id,
        pet_id=internacao.pet_id,
        horario_agendado=horario_agendado,
        medicamento=medicamento,
        dose=(body.dose or "").strip() or None,
        via=(body.via or "").strip() or None,
        quantidade_prevista=quantidade_prevista,
        unidade_quantidade=(body.unidade_quantidade or "").strip() or None,
        lembrete_minutos=body.lembrete_min if body.lembrete_min is not None else 30,
        observacoes_agenda=(body.observacoes_agenda or "").strip() or None,
        status="agendado",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    item.internacao = internacao
    item.pet = internacao.pet
    return _serializar_procedimento_agenda_internacao(item)


@router.patch("/internacoes/procedimentos-agenda/{agenda_id}/concluir")
def concluir_procedimento_agenda_internacao(
    agenda_id: int,
    body: ProcedimentoAgendaInternacaoConcluir,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(
        user, tenant_id, "Tenant nao identificado para agenda de internacao"
    )
    user_id = _resolver_user_id_vet(user, "Usuario invalido para agenda de internacao")

    item = (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .filter(
            InternacaoProcedimentoAgenda.id == agenda_id,
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(404, "Procedimento agendado nao encontrado")
    _garantir_internacao_ativa(
        item.internacao,
        "concluir procedimento da agenda",
    )
    if item.status == "cancelado":
        raise HTTPException(
            status_code=409, detail="Procedimento cancelado nao pode ser concluido"
        )

    executado_por = (body.executado_por or "").strip()
    if not executado_por:
        raise HTTPException(
            status_code=422, detail="Campo 'executado_por' e obrigatorio"
        )

    horario_execucao = _normalizar_datetime_local_brasilia(body.horario_execucao)
    if not horario_execucao:
        raise HTTPException(
            status_code=422, detail="Campo 'horario_execucao' e obrigatorio"
        )

    quantidade_prevista = _as_float(body.quantidade_prevista)
    quantidade_executada = _as_float(body.quantidade_executada)
    quantidade_desperdicio = _as_float(body.quantidade_desperdicio) or 0.0

    if quantidade_prevista is not None and quantidade_prevista < 0:
        raise HTTPException(
            status_code=422, detail="Quantidade prevista nao pode ser negativa"
        )
    if quantidade_executada is not None and quantidade_executada < 0:
        raise HTTPException(
            status_code=422, detail="Quantidade executada nao pode ser negativa"
        )
    if quantidade_desperdicio < 0:
        raise HTTPException(
            status_code=422, detail="Quantidade de desperdicio nao pode ser negativa"
        )
    if quantidade_executada is None and quantidade_prevista is not None:
        quantidade_executada = quantidade_prevista

    item.status = "concluido"
    item.executado_por = executado_por
    item.horario_execucao = horario_execucao
    item.observacao_execucao = (body.observacao_execucao or "").strip() or None
    item.quantidade_prevista = (
        quantidade_prevista
        if quantidade_prevista is not None
        else item.quantidade_prevista
    )
    item.quantidade_executada = quantidade_executada
    item.quantidade_desperdicio = quantidade_desperdicio
    item.unidade_quantidade = (
        body.unidade_quantidade or ""
    ).strip() or item.unidade_quantidade

    payload = _build_payload_procedimento_agenda_internacao(item)
    if item.procedimento_evolucao_id:
        evolucao = (
            db.query(EvolucaoInternacao)
            .filter(
                EvolucaoInternacao.id == item.procedimento_evolucao_id,
                EvolucaoInternacao.tenant_id == tenant_id,
            )
            .first()
        )
        if evolucao:
            evolucao.user_id = user_id
            evolucao.data_hora = horario_execucao
            evolucao.observacoes = _build_procedimento_observacao(payload)
        else:
            item.procedimento_evolucao_id = None

    if not item.procedimento_evolucao_id:
        evolucao = EvolucaoInternacao(
            internacao_id=item.internacao_id,
            user_id=user_id,
            tenant_id=tenant_id,
            data_hora=horario_execucao,
            observacoes=_build_procedimento_observacao(payload),
        )
        db.add(evolucao)
        db.flush()
        item.procedimento_evolucao_id = evolucao.id

    db.commit()
    db.refresh(item)
    return _serializar_procedimento_agenda_internacao(item)


@router.delete("/internacoes/procedimentos-agenda/{agenda_id}", status_code=204)
def remover_procedimento_agenda_internacao(
    agenda_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(
        user, tenant_id, "Tenant nao identificado para agenda de internacao"
    )

    item = (
        db.query(InternacaoProcedimentoAgenda)
        .options(joinedload(InternacaoProcedimentoAgenda.internacao))
        .filter(
            InternacaoProcedimentoAgenda.id == agenda_id,
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(404, "Procedimento agendado nao encontrado")
    _garantir_internacao_ativa(
        item.internacao,
        "cancelar procedimento da agenda",
    )
    if item.status == "concluido":
        raise HTTPException(
            status_code=409,
            detail="Procedimento concluido ja compoe o historico clinico e nao pode ser excluido",
        )

    item.status = "cancelado"
    db.commit()
    return Response(status_code=204)
