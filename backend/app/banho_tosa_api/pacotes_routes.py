from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.pacotes_helpers import (
    obter_pacote,
    query_creditos,
    validar_cliente_pet_credito,
    validar_nome_pacote_disponivel,
    validar_servico,
)
from app.banho_tosa_models import (
    BanhoTosaPacote,
    BanhoTosaPacoteCredito,
)
from app.banho_tosa_pacotes import (
    calcular_validade_pacote,
    consumir_credito_atendimento,
    estornar_consumo_atendimento,
)
from app.banho_tosa_pacotes_serializers import (
    serializar_credito,
    serializar_movimento,
    serializar_pacote,
)
from app.banho_tosa_schemas import (
    BanhoTosaPacoteConsumoInput,
    BanhoTosaPacoteConsumoResponse,
    BanhoTosaPacoteCreditoCreate,
    BanhoTosaPacoteCreditoResponse,
    BanhoTosaPacoteCreate,
    BanhoTosaPacoteEstornoInput,
    BanhoTosaPacoteResponse,
    BanhoTosaPacoteUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/pacotes", response_model=List[BanhoTosaPacoteResponse])
def listar_pacotes(
    ativos_only: bool = Query(False),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = db.query(BanhoTosaPacote).options(joinedload(BanhoTosaPacote.servico)).filter(
        BanhoTosaPacote.tenant_id == tenant_id
    )
    if ativos_only:
        query = query.filter(BanhoTosaPacote.ativo == True)
    return [serializar_pacote(item) for item in query.order_by(BanhoTosaPacote.nome.asc()).all()]


@router.post("/pacotes", response_model=BanhoTosaPacoteResponse, status_code=201)
def criar_pacote(
    body: BanhoTosaPacoteCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    nome = body.nome.strip()
    validar_nome_pacote_disponivel(db, tenant_id, nome)
    validar_servico(db, tenant_id, body.servico_id)
    pacote = BanhoTosaPacote(tenant_id=tenant_id, **body.model_dump())
    pacote.nome = nome
    db.add(pacote)
    db.commit()
    db.refresh(pacote)
    return serializar_pacote(pacote)


@router.delete("/pacotes/{pacote_id}")
def excluir_pacote(
    pacote_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pacote = obter_pacote(db, tenant_id, pacote_id)
    if _pacote_tem_creditos(db, tenant_id, pacote_id):
        pacote.ativo = False
        db.commit()
        return {
            "deleted": False,
            "deactivated": True,
            "message": "Pacote possui creditos emitidos e foi desativado para preservar o historico.",
        }

    db.delete(pacote)
    db.commit()
    return {
        "deleted": True,
        "deactivated": False,
        "message": "Pacote excluido.",
    }


@router.patch("/pacotes/{pacote_id}", response_model=BanhoTosaPacoteResponse)
def atualizar_pacote(
    pacote_id: int,
    body: BanhoTosaPacoteUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pacote = obter_pacote(db, tenant_id, pacote_id)
    payload = body.model_dump(exclude_unset=True)
    if "nome" in payload:
        payload["nome"] = (payload["nome"] or "").strip()
        validar_nome_pacote_disponivel(db, tenant_id, payload["nome"], ignorar_id=pacote.id)
    if "servico_id" in payload:
        validar_servico(db, tenant_id, payload["servico_id"])
    for campo, valor in payload.items():
        setattr(pacote, campo, valor)
    db.commit()
    db.refresh(pacote)
    return serializar_pacote(pacote)


@router.get("/pacotes/creditos", response_model=List[BanhoTosaPacoteCreditoResponse])
def listar_creditos(
    cliente_id: Optional[int] = Query(None),
    pet_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    disponiveis_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = query_creditos(db, tenant_id)
    if cliente_id:
        query = query.filter(BanhoTosaPacoteCredito.cliente_id == cliente_id)
    if pet_id:
        query = query.filter(or_(BanhoTosaPacoteCredito.pet_id == pet_id, BanhoTosaPacoteCredito.pet_id.is_(None)))
    if status:
        query = query.filter(BanhoTosaPacoteCredito.status == status)
    if disponiveis_only:
        query = query.filter(BanhoTosaPacoteCredito.status == "ativo", BanhoTosaPacoteCredito.data_validade >= date.today())
    creditos = query.order_by(BanhoTosaPacoteCredito.data_validade.asc()).limit(limit).all()
    return [serializar_credito(item) for item in creditos]


def _pacote_tem_creditos(db: Session, tenant_id, pacote_id: int) -> bool:
    return db.query(BanhoTosaPacoteCredito.id).filter(
        BanhoTosaPacoteCredito.tenant_id == tenant_id,
        BanhoTosaPacoteCredito.pacote_id == pacote_id,
    ).first() is not None


@router.post("/pacotes/creditos", response_model=BanhoTosaPacoteCreditoResponse, status_code=201)
def criar_credito(
    body: BanhoTosaPacoteCreditoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pacote = obter_pacote(db, tenant_id, body.pacote_id, ativo=True)
    validar_cliente_pet_credito(db, tenant_id, body.cliente_id, body.pet_id)
    data_inicio = body.data_inicio or date.today()
    data_validade = body.data_validade or calcular_validade_pacote(data_inicio, pacote.validade_dias)
    if data_validade < data_inicio:
        raise HTTPException(status_code=422, detail="Validade do pacote nao pode ser anterior ao inicio.")
    credito = BanhoTosaPacoteCredito(
        tenant_id=tenant_id,
        pacote_id=pacote.id,
        cliente_id=body.cliente_id,
        pet_id=body.pet_id,
        venda_id=body.venda_id,
        status="ativo",
        creditos_total=pacote.quantidade_creditos,
        data_inicio=data_inicio,
        data_validade=data_validade,
        observacoes=body.observacoes,
    )
    db.add(credito)
    db.commit()
    db.refresh(credito)
    credito = query_creditos(db, tenant_id).filter(BanhoTosaPacoteCredito.id == credito.id).first()
    return serializar_credito(credito)


@router.post("/pacotes/creditos/{credito_id}/consumir", response_model=BanhoTosaPacoteConsumoResponse)
def consumir_credito(
    credito_id: int,
    body: BanhoTosaPacoteConsumoInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    credito, movimento, ja_existia = consumir_credito_atendimento(
        db,
        tenant_id,
        credito_id,
        body.atendimento_id,
        body.quantidade,
        user_id=getattr(current_user, "id", None),
        observacoes=body.observacoes,
    )
    credito = query_creditos(db, tenant_id).filter(BanhoTosaPacoteCredito.id == credito.id).first()
    return {"credito": serializar_credito(credito), "movimento": serializar_movimento(movimento), "ja_existia": ja_existia}


@router.post("/pacotes/creditos/{credito_id}/estornar", response_model=BanhoTosaPacoteConsumoResponse)
def estornar_credito(
    credito_id: int,
    body: BanhoTosaPacoteEstornoInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    credito, movimento, ja_existia = estornar_consumo_atendimento(
        db,
        tenant_id,
        credito_id,
        atendimento_id=body.atendimento_id,
        movimento_id=body.movimento_id,
        user_id=getattr(current_user, "id", None),
        observacoes=body.observacoes,
    )
    credito = query_creditos(db, tenant_id).filter(BanhoTosaPacoteCredito.id == credito.id).first()
    return {"credito": serializar_credito(credito), "movimento": serializar_movimento(movimento), "ja_existia": ja_existia}
