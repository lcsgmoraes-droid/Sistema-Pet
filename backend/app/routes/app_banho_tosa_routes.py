"""Rotas do Banho & Tosa para o app do tutor."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaAvaliacao,
)
from app.db import get_session
from app.models import User
from app.routes.app_mobile_routes import _get_cliente_or_404
from app.routes.ecommerce_auth import _get_current_ecommerce_user


router = APIRouter(prefix="/app/banho-tosa", tags=["App Mobile - Banho & Tosa"])

STATUS_LABELS = {
    "agendado": "Agendado",
    "confirmado": "Confirmado",
    "chegou": "Pet recebido",
    "em_banho": "Em banho",
    "em_tosa": "Em tosa",
    "secagem": "Secagem",
    "pronto": "Pronto para buscar",
    "entregue": "Entregue",
    "cancelado": "Cancelado",
    "no_show": "Nao compareceu",
}
STATUS_PROGRESSO = {
    "agendado": 10,
    "confirmado": 20,
    "chegou": 35,
    "em_banho": 55,
    "secagem": 70,
    "em_tosa": 78,
    "pronto": 90,
    "entregue": 100,
}


class BanhoTosaAvaliacaoInput(BaseModel):
    nota_nps: int = Field(..., ge=0, le=10)
    nota_servico: Optional[int] = Field(default=None, ge=1, le=5)
    comentario: Optional[str] = Field(default=None, max_length=1000)


@router.get("/status")
def listar_status_banho_tosa(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    cliente = _get_cliente_or_404(db, current_user)
    tenant_id = current_user.tenant_id
    atendimentos = _listar_atendimentos_visiveis(db, tenant_id, cliente.id)
    agendamento_ids = {item.agendamento_id for item in atendimentos if item.agendamento_id}
    agendamentos = _listar_agendamentos_visiveis(db, tenant_id, cliente.id, agendamento_ids)
    itens = [_serializar_atendimento(item) for item in atendimentos]
    itens.extend(_serializar_agendamento(item) for item in agendamentos)
    itens = sorted(itens, key=lambda item: item.get("ordenacao") or "", reverse=True)
    return {"total": len(itens), "itens": [{k: v for k, v in item.items() if k != "ordenacao"} for item in itens]}


@router.post("/atendimentos/{atendimento_id}/avaliacao")
def avaliar_atendimento_banho_tosa(
    atendimento_id: int,
    payload: BanhoTosaAvaliacaoInput,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    cliente = _get_cliente_or_404(db, current_user)
    atendimento = db.query(BanhoTosaAtendimento).filter(
        BanhoTosaAtendimento.tenant_id == current_user.tenant_id,
        BanhoTosaAtendimento.id == atendimento_id,
        BanhoTosaAtendimento.cliente_id == cliente.id,
    ).first()
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado.")
    if atendimento.status != "entregue":
        raise HTTPException(status_code=422, detail="Avaliacao liberada apenas apos a entrega do pet.")
    avaliacao = db.query(BanhoTosaAvaliacao).filter(
        BanhoTosaAvaliacao.tenant_id == current_user.tenant_id,
        BanhoTosaAvaliacao.atendimento_id == atendimento.id,
        BanhoTosaAvaliacao.cliente_id == cliente.id,
    ).first()
    if not avaliacao:
        avaliacao = BanhoTosaAvaliacao(
            tenant_id=current_user.tenant_id,
            atendimento_id=atendimento.id,
            cliente_id=cliente.id,
            pet_id=atendimento.pet_id,
        )
        db.add(avaliacao)
    avaliacao.nota_nps = payload.nota_nps
    avaliacao.nota_servico = payload.nota_servico
    avaliacao.comentario = (payload.comentario or "").strip() or None
    avaliacao.origem = "app"
    db.commit()
    db.refresh(avaliacao)
    return _serializar_avaliacao(avaliacao)


def _listar_atendimentos_visiveis(db: Session, tenant_id, cliente_id: int):
    corte = datetime.now() - timedelta(days=45)
    return db.query(BanhoTosaAtendimento).options(
        joinedload(BanhoTosaAtendimento.pet),
        joinedload(BanhoTosaAtendimento.avaliacoes),
        joinedload(BanhoTosaAtendimento.etapas),
        joinedload(BanhoTosaAtendimento.agendamento).joinedload(BanhoTosaAgendamento.servicos),
    ).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.cliente_id == cliente_id,
        BanhoTosaAtendimento.status.notin_(["cancelado", "no_show"]),
        BanhoTosaAtendimento.checkin_em >= corte,
    ).order_by(BanhoTosaAtendimento.checkin_em.desc()).limit(20).all()


def _listar_agendamentos_visiveis(db: Session, tenant_id, cliente_id: int, ignorar_ids: set[int]):
    inicio = datetime.now() - timedelta(hours=12)
    query = db.query(BanhoTosaAgendamento).options(
        joinedload(BanhoTosaAgendamento.pet),
        joinedload(BanhoTosaAgendamento.servicos),
    ).filter(
        BanhoTosaAgendamento.tenant_id == tenant_id,
        BanhoTosaAgendamento.cliente_id == cliente_id,
        BanhoTosaAgendamento.status.in_(["agendado", "confirmado"]),
        BanhoTosaAgendamento.data_hora_inicio >= inicio,
    )
    if ignorar_ids:
        query = query.filter(BanhoTosaAgendamento.id.notin_(ignorar_ids))
    return query.order_by(BanhoTosaAgendamento.data_hora_inicio.asc()).limit(20).all()


def _serializar_atendimento(item: BanhoTosaAtendimento) -> dict:
    avaliacao = next((av for av in item.avaliacoes or [] if av.cliente_id == item.cliente_id), None)
    agendamento = item.agendamento
    return {
        "tipo": "atendimento",
        "atendimento_id": item.id,
        "agendamento_id": item.agendamento_id,
        "pet_id": item.pet_id,
        "pet_nome": item.pet.nome if item.pet else None,
        "status": item.status,
        "status_label": STATUS_LABELS.get(item.status, item.status),
        "progresso_percentual": STATUS_PROGRESSO.get(item.status, 40),
        "etapa_atual": _etapa_atual(item),
        "data_hora_inicio": _iso(getattr(agendamento, "data_hora_inicio", None)),
        "data_hora_fim_prevista": _iso(getattr(agendamento, "data_hora_fim_prevista", None)),
        "checkin_em": _iso(item.checkin_em),
        "inicio_em": _iso(item.inicio_em),
        "fim_em": _iso(item.fim_em),
        "entregue_em": _iso(item.entregue_em),
        "servicos": _servicos(agendamento),
        "valor_previsto": _decimal(getattr(agendamento, "valor_previsto", None)),
        "pode_avaliar": item.status == "entregue" and not avaliacao,
        "avaliacao": _serializar_avaliacao(avaliacao) if avaliacao else None,
        "ordenacao": _iso(item.checkin_em) or "",
    }


def _serializar_agendamento(item: BanhoTosaAgendamento) -> dict:
    return {
        "tipo": "agendamento",
        "atendimento_id": None,
        "agendamento_id": item.id,
        "pet_id": item.pet_id,
        "pet_nome": item.pet.nome if item.pet else None,
        "status": item.status,
        "status_label": STATUS_LABELS.get(item.status, item.status),
        "progresso_percentual": STATUS_PROGRESSO.get(item.status, 10),
        "etapa_atual": "Aguardando check-in",
        "data_hora_inicio": _iso(item.data_hora_inicio),
        "data_hora_fim_prevista": _iso(item.data_hora_fim_prevista),
        "servicos": _servicos(item),
        "valor_previsto": _decimal(item.valor_previsto),
        "pode_avaliar": False,
        "avaliacao": None,
        "ordenacao": _iso(item.data_hora_inicio) or "",
    }


def _servicos(agendamento) -> list[dict]:
    if not agendamento:
        return []
    return [{"nome": item.nome_servico_snapshot, "quantidade": _decimal(item.quantidade)} for item in agendamento.servicos or []]


def _etapa_atual(atendimento: BanhoTosaAtendimento) -> str:
    ativa = next((et for et in atendimento.etapas or [] if et.inicio_em and not et.fim_em), None)
    return STATUS_LABELS.get(atendimento.status, atendimento.status) if not ativa else ativa.tipo.replace("_", " ").title()


def _serializar_avaliacao(avaliacao) -> Optional[dict]:
    if not avaliacao:
        return None
    return {
        "id": avaliacao.id,
        "nota_nps": avaliacao.nota_nps,
        "nota_servico": avaliacao.nota_servico,
        "comentario": avaliacao.comentario,
        "origem": avaliacao.origem,
        "created_at": _iso(avaliacao.created_at),
    }


def _iso(valor) -> Optional[str]:
    return valor.isoformat() if valor else None


def _decimal(valor) -> float:
    if isinstance(valor, Decimal):
        return float(valor)
    return float(valor or 0)
