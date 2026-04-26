from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.utils import validar_cliente_pet
from app.banho_tosa_custos_reais import recalcular_snapshot_atendimento
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaTaxiDog,
)
from app.banho_tosa_schemas import (
    BanhoTosaTaxiDogCreate,
    BanhoTosaTaxiDogResponse,
    BanhoTosaTaxiDogStatusUpdate,
    BanhoTosaTaxiDogUpdate,
)
from app.db import get_session
from app.models import Cliente
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/taxi-dog", response_model=List[BanhoTosaTaxiDogResponse])
def listar_taxi_dog(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = _query_taxi_completo(db, tenant_id)
    if status:
        query = query.filter(BanhoTosaTaxiDog.status == status)
    if data_inicio:
        query = query.filter(BanhoTosaTaxiDog.janela_inicio >= _inicio_dia(data_inicio))
    if data_fim:
        query = query.filter(BanhoTosaTaxiDog.janela_inicio <= _fim_dia(data_fim))

    itens = query.order_by(BanhoTosaTaxiDog.janela_inicio.asc(), BanhoTosaTaxiDog.id.desc()).limit(limit).all()
    return [_serializar_taxi(item) for item in itens]


@router.post("/taxi-dog", response_model=BanhoTosaTaxiDogResponse, status_code=201)
def criar_taxi_dog(
    body: BanhoTosaTaxiDogCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    agendamento = _obter_agendamento(db, tenant_id, body.agendamento_id)
    cliente_id, pet_id = _resolver_cliente_pet(db, tenant_id, body, agendamento)
    _validar_motorista(db, tenant_id, body.motorista_id)

    taxi = BanhoTosaTaxiDog(
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        pet_id=pet_id,
        agendamento_id=agendamento.id if agendamento else None,
        tipo=body.tipo.strip().lower(),
        status=body.status.strip().lower(),
        motorista_id=body.motorista_id,
        endereco_origem=body.endereco_origem,
        endereco_destino=body.endereco_destino,
        janela_inicio=body.janela_inicio,
        janela_fim=body.janela_fim,
        km_estimado=body.km_estimado,
        km_real=body.km_real,
        valor_cobrado=body.valor_cobrado,
        custo_estimado=body.custo_estimado,
        custo_real=body.custo_real,
        rota_entrega_id=body.rota_entrega_id,
    )
    db.add(taxi)
    _validar_janela(taxi)
    db.flush()
    if agendamento:
        agendamento.taxi_dog_id = taxi.id
    _recalcular_custo_vinculado(db, tenant_id, taxi)
    db.commit()
    taxi = _obter_taxi_ou_404(db, tenant_id, taxi.id)
    return _serializar_taxi(taxi)


@router.patch("/taxi-dog/{taxi_id}", response_model=BanhoTosaTaxiDogResponse)
def atualizar_taxi_dog(
    taxi_id: int,
    body: BanhoTosaTaxiDogUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    taxi = _obter_taxi_ou_404(db, tenant_id, taxi_id)
    payload = body.model_dump(exclude_unset=True)
    _validar_motorista(db, tenant_id, payload.get("motorista_id"))

    for campo, valor in payload.items():
        if isinstance(valor, str) and campo in {"tipo", "status"}:
            valor = valor.strip().lower()
        setattr(taxi, campo, valor)

    _validar_janela(taxi)
    _recalcular_custo_vinculado(db, tenant_id, taxi)
    db.commit()
    taxi = _obter_taxi_ou_404(db, tenant_id, taxi.id)
    return _serializar_taxi(taxi)


@router.patch("/taxi-dog/{taxi_id}/status", response_model=BanhoTosaTaxiDogResponse)
def atualizar_status_taxi_dog(
    taxi_id: int,
    body: BanhoTosaTaxiDogStatusUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    taxi = _obter_taxi_ou_404(db, tenant_id, taxi_id)
    taxi.status = body.status.strip().lower()
    _recalcular_custo_vinculado(db, tenant_id, taxi)
    db.commit()
    taxi = _obter_taxi_ou_404(db, tenant_id, taxi.id)
    return _serializar_taxi(taxi)


def _query_taxi_completo(db: Session, tenant_id):
    return (
        db.query(BanhoTosaTaxiDog)
        .options(
            joinedload(BanhoTosaTaxiDog.cliente),
            joinedload(BanhoTosaTaxiDog.pet),
            joinedload(BanhoTosaTaxiDog.motorista),
            joinedload(BanhoTosaTaxiDog.agendamento),
        )
        .filter(BanhoTosaTaxiDog.tenant_id == tenant_id)
    )


def _obter_taxi_ou_404(db: Session, tenant_id, taxi_id: int) -> BanhoTosaTaxiDog:
    taxi = _query_taxi_completo(db, tenant_id).filter(BanhoTosaTaxiDog.id == taxi_id).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Taxi dog nao encontrado")
    return taxi


def _obter_agendamento(db: Session, tenant_id, agendamento_id: int | None):
    if not agendamento_id:
        return None
    agendamento = db.query(BanhoTosaAgendamento).filter(
        BanhoTosaAgendamento.id == agendamento_id,
        BanhoTosaAgendamento.tenant_id == tenant_id,
    ).first()
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")
    if agendamento.taxi_dog_id:
        raise HTTPException(status_code=409, detail="Agendamento ja possui taxi dog vinculado")
    return agendamento


def _resolver_cliente_pet(db: Session, tenant_id, body: BanhoTosaTaxiDogCreate, agendamento):
    if agendamento:
        return agendamento.cliente_id, agendamento.pet_id
    if not body.cliente_id or not body.pet_id:
        raise HTTPException(status_code=422, detail="Informe agendamento ou cliente/pet.")
    cliente, pet = validar_cliente_pet(db, tenant_id, body.cliente_id, body.pet_id)
    return cliente.id, pet.id


def _validar_motorista(db: Session, tenant_id, motorista_id: int | None):
    if not motorista_id:
        return
    motorista = db.query(Cliente).filter(Cliente.id == motorista_id, Cliente.tenant_id == tenant_id).first()
    if not motorista:
        raise HTTPException(status_code=404, detail="Motorista nao encontrado")


def _validar_janela(taxi: BanhoTosaTaxiDog):
    if taxi.janela_inicio and taxi.janela_fim and taxi.janela_fim <= taxi.janela_inicio:
        raise HTTPException(status_code=422, detail="Janela final deve ser maior que a inicial")


def _recalcular_custo_vinculado(db: Session, tenant_id, taxi: BanhoTosaTaxiDog):
    if not taxi.agendamento_id:
        return
    atendimento = db.query(BanhoTosaAtendimento).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.agendamento_id == taxi.agendamento_id,
    ).first()
    if atendimento:
        recalcular_snapshot_atendimento(db, tenant_id, atendimento.id)


def _serializar_taxi(taxi: BanhoTosaTaxiDog) -> dict:
    agendamento = taxi.agendamento
    return {
        "id": taxi.id,
        "cliente_id": taxi.cliente_id,
        "cliente_nome": taxi.cliente.nome if taxi.cliente else None,
        "pet_id": taxi.pet_id,
        "pet_nome": taxi.pet.nome if taxi.pet else None,
        "agendamento_id": taxi.agendamento_id,
        "agendamento_inicio": agendamento.data_hora_inicio if agendamento else None,
        "tipo": taxi.tipo,
        "status": taxi.status,
        "motorista_id": taxi.motorista_id,
        "motorista_nome": taxi.motorista.nome if taxi.motorista else None,
        "endereco_origem": taxi.endereco_origem,
        "endereco_destino": taxi.endereco_destino,
        "janela_inicio": taxi.janela_inicio,
        "janela_fim": taxi.janela_fim,
        "km_estimado": taxi.km_estimado,
        "km_real": taxi.km_real,
        "valor_cobrado": taxi.valor_cobrado,
        "custo_estimado": taxi.custo_estimado,
        "custo_real": taxi.custo_real,
        "rota_entrega_id": taxi.rota_entrega_id,
        "data_referencia": taxi.janela_inicio.date() if taxi.janela_inicio else None,
    }


def _inicio_dia(data_ref: date):
    return datetime.combine(data_ref, time.min)


def _fim_dia(data_ref: date):
    return datetime.combine(data_ref, time.max)
