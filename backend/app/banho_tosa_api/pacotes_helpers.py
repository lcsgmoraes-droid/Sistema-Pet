from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_api.utils import validar_cliente_pet
from app.banho_tosa_models import (
    BanhoTosaPacote,
    BanhoTosaPacoteCredito,
    BanhoTosaRecorrencia,
    BanhoTosaServico,
)
from app.models import Cliente


def query_creditos(db: Session, tenant_id):
    return db.query(BanhoTosaPacoteCredito).options(
        joinedload(BanhoTosaPacoteCredito.pacote).joinedload(BanhoTosaPacote.servico),
        joinedload(BanhoTosaPacoteCredito.cliente),
        joinedload(BanhoTosaPacoteCredito.pet),
    ).filter(BanhoTosaPacoteCredito.tenant_id == tenant_id)


def query_recorrencias(db: Session, tenant_id):
    return db.query(BanhoTosaRecorrencia).options(
        joinedload(BanhoTosaRecorrencia.cliente),
        joinedload(BanhoTosaRecorrencia.pet),
        joinedload(BanhoTosaRecorrencia.servico),
    ).filter(BanhoTosaRecorrencia.tenant_id == tenant_id)


def obter_pacote(db: Session, tenant_id, pacote_id: int, ativo: bool = False):
    query = db.query(BanhoTosaPacote).options(joinedload(BanhoTosaPacote.servico)).filter(
        BanhoTosaPacote.id == pacote_id,
        BanhoTosaPacote.tenant_id == tenant_id,
    )
    if ativo:
        query = query.filter(BanhoTosaPacote.ativo == True)
    pacote = query.first()
    if not pacote:
        raise HTTPException(status_code=404, detail="Pacote nao encontrado.")
    return pacote


def obter_credito(db: Session, tenant_id, credito_id: int):
    credito = query_creditos(db, tenant_id).filter(BanhoTosaPacoteCredito.id == credito_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Credito de pacote nao encontrado.")
    return credito


def validar_servico(db: Session, tenant_id, servico_id: Optional[int]) -> None:
    if not servico_id:
        return
    servico = db.query(BanhoTosaServico.id).filter(
        BanhoTosaServico.id == servico_id,
        BanhoTosaServico.tenant_id == tenant_id,
    ).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Servico nao encontrado.")


def validar_nome_pacote_disponivel(db: Session, tenant_id, nome: str, ignorar_id: Optional[int] = None) -> None:
    query = db.query(BanhoTosaPacote.id).filter(
        BanhoTosaPacote.tenant_id == tenant_id,
        func.lower(BanhoTosaPacote.nome) == nome.lower(),
    )
    if ignorar_id:
        query = query.filter(BanhoTosaPacote.id != ignorar_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Ja existe um pacote com esse nome.")


def validar_cliente_pet_credito(db: Session, tenant_id, cliente_id: int, pet_id: Optional[int]) -> None:
    if pet_id:
        validar_cliente_pet(db, tenant_id, cliente_id, pet_id)
        return
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id,
        Cliente.ativo == True,
    ).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Tutor nao encontrado.")


def serializar_recorrencia(item) -> dict:
    return {
        "id": item.id,
        "cliente_id": item.cliente_id,
        "cliente_nome": item.cliente.nome if item.cliente else None,
        "pet_id": item.pet_id,
        "pet_nome": item.pet.nome if item.pet else None,
        "servico_id": item.servico_id,
        "servico_nome": item.servico.nome if item.servico else None,
        "pacote_credito_id": item.pacote_credito_id,
        "intervalo_dias": item.intervalo_dias,
        "proxima_execucao": item.proxima_execucao,
        "canal_lembrete": item.canal_lembrete,
        "ativo": item.ativo,
        "observacoes": item.observacoes,
    }
