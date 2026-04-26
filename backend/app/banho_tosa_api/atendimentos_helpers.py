from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_api.utils import STATUS_ATENDIMENTO_FINAIS
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaEtapa,
    BanhoTosaPacoteCredito,
    BanhoTosaRecurso,
)
from app.models import Cliente
from app.vendas_models import Venda


STATUS_POR_TIPO_ETAPA = {
    "banho": "em_banho",
    "secagem": "em_secagem",
    "tosa": "em_tosa",
    "higiene": "em_banho",
    "preparo": "em_banho",
}


def query_atendimento_completo(db: Session, tenant_id):
    return (
        db.query(BanhoTosaAtendimento)
        .options(
            joinedload(BanhoTosaAtendimento.cliente),
            joinedload(BanhoTosaAtendimento.pet),
            joinedload(BanhoTosaAtendimento.agendamento),
            joinedload(BanhoTosaAtendimento.pacote_credito).joinedload(BanhoTosaPacoteCredito.pacote),
            joinedload(BanhoTosaAtendimento.venda).joinedload(Venda.pagamentos),
            joinedload(BanhoTosaAtendimento.etapas).joinedload(BanhoTosaEtapa.responsavel),
            joinedload(BanhoTosaAtendimento.etapas).joinedload(BanhoTosaEtapa.recurso),
        )
        .filter(BanhoTosaAtendimento.tenant_id == tenant_id)
    )


def obter_atendimento_ou_404(db: Session, tenant_id, atendimento_id: int) -> BanhoTosaAtendimento:
    atendimento = query_atendimento_completo(db, tenant_id).filter(BanhoTosaAtendimento.id == atendimento_id).first()
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado")
    return atendimento


def obter_etapa_ou_404(db: Session, tenant_id, atendimento_id: int, etapa_id: int) -> BanhoTosaEtapa:
    etapa = (
        db.query(BanhoTosaEtapa)
        .options(joinedload(BanhoTosaEtapa.responsavel), joinedload(BanhoTosaEtapa.recurso))
        .filter(
            BanhoTosaEtapa.id == etapa_id,
            BanhoTosaEtapa.tenant_id == tenant_id,
            BanhoTosaEtapa.atendimento_id == atendimento_id,
        )
        .first()
    )
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa nao encontrada")
    return etapa


def validar_responsavel_recurso(db: Session, tenant_id, responsavel_id: Optional[int], recurso_id: Optional[int]):
    if responsavel_id:
        responsavel = db.query(Cliente).filter(Cliente.id == responsavel_id, Cliente.tenant_id == tenant_id).first()
        if not responsavel:
            raise HTTPException(status_code=404, detail="Responsavel nao encontrado")

    if recurso_id:
        recurso = db.query(BanhoTosaRecurso).filter(
            BanhoTosaRecurso.id == recurso_id,
            BanhoTosaRecurso.tenant_id == tenant_id,
            BanhoTosaRecurso.ativo == True,
        ).first()
        if not recurso:
            raise HTTPException(status_code=404, detail="Recurso nao encontrado")


def aplicar_status_atendimento(db: Session, tenant_id, atendimento: BanhoTosaAtendimento, novo_status: str):
    agora = datetime.now()
    atendimento.status = novo_status
    if novo_status in {"em_banho", "em_tosa", "em_secagem"} and not atendimento.inicio_em:
        atendimento.inicio_em = agora
    if novo_status == "pronto" and not atendimento.fim_em:
        atendimento.fim_em = agora
    if novo_status == "entregue" and not atendimento.entregue_em:
        atendimento.entregue_em = agora

    if not atendimento.agendamento_id:
        return

    agendamento = db.query(BanhoTosaAgendamento).filter(
        BanhoTosaAgendamento.id == atendimento.agendamento_id,
        BanhoTosaAgendamento.tenant_id == tenant_id,
    ).first()
    if not agendamento:
        return

    if novo_status in STATUS_ATENDIMENTO_FINAIS:
        agendamento.status = novo_status
    elif novo_status == "pronto":
        agendamento.status = "pronto"
    else:
        agendamento.status = "em_atendimento"
