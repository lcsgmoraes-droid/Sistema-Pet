"""Operacao de Banho & Tosa no app de funcionario e do entregador."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_api.agenda_routes import (
    criar_agendamento as criar_agendamento_erp,
    realizar_checkin_agendamento as realizar_checkin_agendamento_erp,
)
from app.banho_tosa_api.atendimentos_helpers import query_atendimento_completo
from app.banho_tosa_api.atendimentos_routes import (
    mover_etapa_atendimento as mover_etapa_atendimento_erp,
)
from app.banho_tosa_api.taxi_routes import _query_taxi_completo, _serializar_taxi
from app.banho_tosa_api.utils import (
    obter_ou_criar_configuracao,
    serializar_agendamento,
    serializar_atendimento,
)
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaRecurso,
    BanhoTosaServico,
    BanhoTosaTaxiDog,
)
from app.banho_tosa_schemas import (
    BanhoTosaAgendamentoCreate,
    BanhoTosaMoverEtapaInput,
    BanhoTosaTaxiDogStatusUpdate,
)
from app.banho_tosa_taxi_fluxo import (
    TAXI_DOG_STATUS_LABELS,
    proximo_status_taxi_dog,
    sincronizar_chegada_taxi_dog,
    validar_transicao_status_taxi_dog,
)
from app.db import get_session
from app.models import Cliente, Pet, User
from app.routes.ecommerce_auth import (
    _activate_user_tenant_context,
    _get_current_ecommerce_user,
)
from app.services.app_access_profile_service import get_cliente_for_app_profile_or_none


router = APIRouter(
    prefix="/app/funcionario/banho-tosa",
    tags=["App Mobile - Funcionario Banho & Tosa"],
)
taxi_dog_router = APIRouter(
    prefix="/app/entregador/taxi-dog",
    tags=["App Mobile - Entregador Taxi Dog"],
)


class BanhoTosaApoiosResponse(BaseModel):
    fluxo_etapas: list[str]
    funcionario_id: int
    funcionarios: list[dict]
    recursos: list[dict]
    servicos: list[dict]
    pets: list[dict]


def _get_mobile_funcionario_or_403(
    db: Session,
    current_user: User,
) -> tuple[Cliente, str]:
    tenant_id = str(_activate_user_tenant_context(current_user))
    funcionario = get_cliente_for_app_profile_or_none(db, current_user, "funcionario")
    if not funcionario:
        raise HTTPException(
            status_code=403,
            detail="Acesso exclusivo para funcionario operacional.",
        )
    return funcionario, tenant_id


def _get_mobile_entregador_or_403(
    db: Session,
    current_user: User,
) -> tuple[Cliente, str]:
    tenant_id = str(_activate_user_tenant_context(current_user))
    entregador = get_cliente_for_app_profile_or_none(db, current_user, "entregador")
    if not entregador:
        raise HTTPException(
            status_code=403,
            detail="Acesso exclusivo para entregador.",
        )
    return entregador, tenant_id


def _range_bounds(
    data: Optional[date],
    data_inicio: Optional[date],
    data_fim: Optional[date],
) -> tuple[datetime, datetime]:
    if data:
        return datetime.combine(data, time.min), datetime.combine(data, time.max)
    inicio = data_inicio or date.today()
    fim = data_fim or inicio
    if fim < inicio:
        inicio, fim = fim, inicio
    return datetime.combine(inicio, time.min), datetime.combine(fim, time.max)


@router.get("/agenda")
def listar_agenda_banho_tosa_mobile(
    data: Optional[date] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    _, tenant_id = _get_mobile_funcionario_or_403(db, current_user)
    inicio, fim = _range_bounds(data, data_inicio, data_fim)
    itens = (
        db.query(BanhoTosaAgendamento)
        .options(
            joinedload(BanhoTosaAgendamento.cliente),
            joinedload(BanhoTosaAgendamento.pet),
            joinedload(BanhoTosaAgendamento.recurso),
            joinedload(BanhoTosaAgendamento.servicos),
        )
        .filter(
            BanhoTosaAgendamento.tenant_id == tenant_id,
            BanhoTosaAgendamento.data_hora_inicio >= inicio,
            BanhoTosaAgendamento.data_hora_inicio <= fim,
        )
        .order_by(BanhoTosaAgendamento.data_hora_inicio.asc())
        .limit(500)
        .all()
    )
    return [serializar_agendamento(item) for item in itens]


@router.post("/agenda", status_code=201)
def criar_agendamento_banho_tosa_mobile(
    body: BanhoTosaAgendamentoCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    _, tenant_id = _get_mobile_funcionario_or_403(db, current_user)
    return criar_agendamento_erp(
        body=body,
        db=db,
        current=(current_user, tenant_id),
    )


@router.post("/agenda/{agendamento_id}/check-in")
def realizar_checkin_banho_tosa_mobile(
    agendamento_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    _, tenant_id = _get_mobile_funcionario_or_403(db, current_user)
    return realizar_checkin_agendamento_erp(
        agendamento_id=agendamento_id,
        db=db,
        current=(current_user, tenant_id),
    )


@router.get("/fila")
def listar_fila_banho_tosa_mobile(
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    _, tenant_id = _get_mobile_funcionario_or_403(db, current_user)
    itens = (
        query_atendimento_completo(db, tenant_id)
        .filter(
            BanhoTosaAtendimento.status.notin_(["entregue", "cancelado", "no_show"])
        )
        .order_by(BanhoTosaAtendimento.checkin_em.asc())
        .limit(300)
        .all()
    )
    config = obter_ou_criar_configuracao(db, tenant_id)
    return [serializar_atendimento(item, config) for item in itens]


@router.post("/fila/{atendimento_id}/mover-etapa")
def mover_etapa_banho_tosa_mobile(
    atendimento_id: int,
    body: BanhoTosaMoverEtapaInput,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    _, tenant_id = _get_mobile_funcionario_or_403(db, current_user)
    return mover_etapa_atendimento_erp(
        atendimento_id=atendimento_id,
        body=body,
        db=db,
        current=(current_user, tenant_id),
    )


@router.get("/apoios", response_model=BanhoTosaApoiosResponse)
def listar_apoios_banho_tosa_mobile(
    busca_pet: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    funcionario, tenant_id = _get_mobile_funcionario_or_403(db, current_user)
    config = obter_ou_criar_configuracao(db, tenant_id)
    funcionarios = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_(True),
            Cliente.tipo_cadastro.in_(["funcionario", "veterinario", "outro"]),
        )
        .order_by(Cliente.nome.asc())
        .limit(300)
        .all()
    )
    recursos = (
        db.query(BanhoTosaRecurso)
        .filter(
            BanhoTosaRecurso.tenant_id == tenant_id,
            BanhoTosaRecurso.ativo.is_(True),
        )
        .order_by(BanhoTosaRecurso.tipo.asc(), BanhoTosaRecurso.nome.asc())
        .all()
    )
    servicos = (
        db.query(BanhoTosaServico)
        .filter(
            BanhoTosaServico.tenant_id == tenant_id,
            BanhoTosaServico.ativo.is_(True),
        )
        .order_by(BanhoTosaServico.nome.asc())
        .all()
    )
    pets_query = (
        db.query(Pet)
        .options(joinedload(Pet.cliente))
        .filter(Pet.tenant_id == tenant_id, Pet.ativo.is_(True))
    )
    if busca_pet and busca_pet.strip():
        termo = f"%{busca_pet.strip()}%"
        pets_query = pets_query.join(Cliente, Cliente.id == Pet.cliente_id).filter(
            or_(
                Pet.nome.ilike(termo),
                Pet.codigo.ilike(termo),
                Cliente.nome.ilike(termo),
                Cliente.telefone.ilike(termo),
                Cliente.celular.ilike(termo),
            )
        )
    pets = pets_query.order_by(Pet.nome.asc()).limit(300).all()
    return {
        "fluxo_etapas": list(config.fluxo_etapas or []),
        "funcionario_id": funcionario.id,
        "funcionarios": [
            {"id": item.id, "nome": item.nome, "tipo_cadastro": item.tipo_cadastro}
            for item in funcionarios
        ],
        "recursos": [
            {
                "id": item.id,
                "nome": item.nome,
                "tipo": item.tipo,
                "capacidade_simultanea": item.capacidade_simultanea,
            }
            for item in recursos
        ],
        "servicos": [
            {
                "id": item.id,
                "nome": item.nome,
                "categoria": item.categoria,
                "duracao_padrao_minutos": item.duracao_padrao_minutos,
                "preco_base": item.preco_base,
            }
            for item in servicos
        ],
        "pets": [
            {
                "id": item.id,
                "nome": item.nome,
                "codigo": item.codigo,
                "especie": item.especie,
                "raca": item.raca,
                "porte": item.porte,
                "cliente_id": item.cliente_id,
                "cliente_nome": item.cliente.nome if item.cliente else None,
                "cliente_telefone": (
                    (item.cliente.celular or item.cliente.telefone)
                    if item.cliente
                    else None
                ),
            }
            for item in pets
        ],
    }


@taxi_dog_router.get("")
def listar_taxi_dog_entregador_mobile(
    data: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    entregador, tenant_id = _get_mobile_entregador_or_403(db, current_user)
    data_ref = data or date.today()
    itens = (
        _query_taxi_completo(db, tenant_id)
        .filter(
            BanhoTosaTaxiDog.motorista_id == entregador.id,
            BanhoTosaTaxiDog.janela_inicio >= datetime.combine(data_ref, time.min),
            BanhoTosaTaxiDog.janela_inicio <= datetime.combine(data_ref, time.max),
        )
        .order_by(BanhoTosaTaxiDog.janela_inicio.asc(), BanhoTosaTaxiDog.id.asc())
        .all()
    )
    return [
        {
            **_serializar_taxi(item),
            "status_label": TAXI_DOG_STATUS_LABELS.get(item.status, item.status),
            "proximo_status": proximo_status_taxi_dog(item.status, item.tipo),
        }
        for item in itens
    ]


@taxi_dog_router.patch("/{taxi_id}/status")
def atualizar_status_taxi_dog_entregador_mobile(
    taxi_id: int,
    body: BanhoTosaTaxiDogStatusUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    entregador, tenant_id = _get_mobile_entregador_or_403(db, current_user)
    taxi = (
        _query_taxi_completo(db, tenant_id)
        .filter(
            BanhoTosaTaxiDog.id == taxi_id,
            BanhoTosaTaxiDog.motorista_id == entregador.id,
        )
        .first()
    )
    if not taxi:
        raise HTTPException(
            status_code=404, detail="Taxi Dog nao encontrado para este motorista"
        )
    try:
        novo_status = validar_transicao_status_taxi_dog(
            taxi.status,
            body.status,
            taxi.tipo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    taxi.status = novo_status
    if novo_status == "entregue_na_clinica":
        sincronizar_chegada_taxi_dog(
            db,
            tenant_id,
            agendamento_id=taxi.agendamento_id,
        )
    db.commit()
    taxi = (
        _query_taxi_completo(db, tenant_id)
        .filter(BanhoTosaTaxiDog.id == taxi.id)
        .first()
    )
    return {
        **_serializar_taxi(taxi),
        "status_label": TAXI_DOG_STATUS_LABELS.get(taxi.status, taxi.status),
        "proximo_status": proximo_status_taxi_dog(taxi.status, taxi.tipo),
    }
