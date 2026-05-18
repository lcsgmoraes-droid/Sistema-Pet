"""Rotas do App Mobile para o perfil veterinario.

Prefixo : /app/vet
Auth    : token JWT "ecommerce_customer" (mesmo fluxo do app mobile atual)
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.db import get_session
from app.models import Cliente, User
from app.routes.ecommerce_auth import _activate_user_tenant_context, _get_current_ecommerce_user
from app.veterinario_agendamentos import _agendamento_to_dict
from app.veterinario_core import _serializar_datetime_vet, _vet_now
from app.veterinario_internacao import (
    _separar_evolucoes_e_procedimentos,
    _serializar_procedimento_agenda_internacao,
    _split_motivo_baia,
)
from app.veterinario_models import (
    AgendamentoVet,
    EvolucaoInternacao,
    InternacaoProcedimentoAgenda,
    InternacaoVet,
    MedicamentoCatalogo,
)

router = APIRouter(prefix="/app/vet", tags=["App Mobile - Veterinario"])


class ConcluirProcedimentoMobilePayload(BaseModel):
    observacao_execucao: Optional[str] = None


def _get_mobile_veterinario_or_403(db: Session, current_user: User) -> tuple[Cliente, str]:
    tenant_id = str(_activate_user_tenant_context(current_user))
    email = (getattr(current_user, "email", None) or "").strip().lower()

    query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "veterinario",
        Cliente.ativo == True,  # noqa: E712
    )
    if email:
        query = query.filter(
            or_(
                Cliente.user_id == current_user.id,
                func.lower(Cliente.email) == email,
            )
        )
    else:
        query = query.filter(Cliente.user_id == current_user.id)

    veterinario = query.order_by(Cliente.id.asc()).first()
    if not veterinario:
        raise HTTPException(status_code=403, detail="Usuario nao possui perfil veterinario neste tenant")

    return veterinario, tenant_id


def _day_bounds(data: Optional[date]) -> tuple[datetime, datetime]:
    dia = data or date.today()
    return datetime.combine(dia, time.min), datetime.combine(dia, time.max)


def _agendamento_mobile_dict(ag: AgendamentoVet) -> dict:
    item = _agendamento_to_dict(ag)
    item.update({
        "pet_codigo": getattr(ag.pet, "codigo", None) if ag.pet else None,
        "pet_especie": getattr(ag.pet, "especie", None) if ag.pet else None,
        "pet_raca": getattr(ag.pet, "raca", None) if ag.pet else None,
        "cliente_telefone": getattr(ag.cliente, "telefone", None) if ag.cliente else None,
        "cliente_email": getattr(ag.cliente, "email", None) if ag.cliente else None,
    })
    return item


def _internacao_mobile_dict(internacao: InternacaoVet) -> dict:
    motivo, baia = _split_motivo_baia(internacao.motivo)
    pet = internacao.pet
    return {
        "id": internacao.id,
        "pet_id": internacao.pet_id,
        "pet_nome": getattr(pet, "nome", None) or f"Pet #{internacao.pet_id}",
        "pet_codigo": getattr(pet, "codigo", None) if pet else None,
        "pet_especie": getattr(pet, "especie", None) if pet else None,
        "consulta_id": internacao.consulta_id,
        "veterinario_id": internacao.veterinario_id,
        "data_entrada": _serializar_datetime_vet(internacao.data_entrada),
        "data_saida": _serializar_datetime_vet(internacao.data_saida),
        "motivo": motivo,
        "baia": baia or "Sem baia",
        "status": internacao.status,
        "observacoes": internacao.observacoes,
    }


def _medicamento_mobile_dict(medicamento: MedicamentoCatalogo) -> dict:
    return {
        "id": medicamento.id,
        "nome": medicamento.nome,
        "nome_comercial": medicamento.nome_comercial,
        "principio_ativo": medicamento.principio_ativo,
        "fabricante": medicamento.fabricante,
        "forma_farmaceutica": medicamento.forma_farmaceutica,
        "concentracao": medicamento.concentracao,
        "especies_indicadas": medicamento.especies_indicadas or [],
        "indicacoes": medicamento.indicacoes,
        "contraindicacoes": medicamento.contraindicacoes,
        "interacoes": medicamento.interacoes,
        "posologia_referencia": medicamento.posologia_referencia,
        "dose_min_mgkg": medicamento.dose_min_mgkg,
        "dose_max_mgkg": medicamento.dose_max_mgkg,
        "eh_antibiotico": medicamento.eh_antibiotico,
        "eh_controlado": medicamento.eh_controlado,
        "observacoes": medicamento.observacoes,
    }


@router.get("/resumo")
def resumo_veterinario_mobile(
    data: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    veterinario, tenant_id = _get_mobile_veterinario_or_403(db, current_user)
    inicio, fim = _day_bounds(data)
    agora = datetime.now()
    limite_procedimentos = agora + timedelta(hours=24)

    agendamentos = _query_agendamentos(db, tenant_id, veterinario.id, inicio, fim).all()
    internacoes = _query_internacoes(db, tenant_id, veterinario.id).all()
    procedimentos = (
        _query_procedimentos_agenda(db, tenant_id, veterinario.id)
        .filter(InternacaoProcedimentoAgenda.horario_agendado <= limite_procedimentos)
        .limit(8)
        .all()
    )

    return {
        "veterinario": {
            "id": veterinario.id,
            "nome": veterinario.nome,
            "crmv": getattr(veterinario, "crmv", None),
            "email": veterinario.email,
        },
        "data": (data or date.today()).isoformat(),
        "agendamentos_hoje": [_agendamento_mobile_dict(ag) for ag in agendamentos],
        "internacoes_ativas": [_internacao_mobile_dict(item) for item in internacoes],
        "procedimentos_pendentes": [
            _serializar_procedimento_agenda_internacao(item)
            for item in procedimentos
        ],
    }


@router.get("/agendamentos")
def listar_agendamentos_vet_mobile(
    data: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    veterinario, tenant_id = _get_mobile_veterinario_or_403(db, current_user)
    inicio, fim = _day_bounds(data)
    agendamentos = _query_agendamentos(db, tenant_id, veterinario.id, inicio, fim).all()
    return [_agendamento_mobile_dict(ag) for ag in agendamentos]


@router.get("/internacoes")
def listar_internacoes_vet_mobile(
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    veterinario, tenant_id = _get_mobile_veterinario_or_403(db, current_user)
    internacoes = _query_internacoes(db, tenant_id, veterinario.id).all()
    return [_internacao_mobile_dict(item) for item in internacoes]


@router.get("/internacoes/{internacao_id}")
def obter_internacao_vet_mobile(
    internacao_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    veterinario, tenant_id = _get_mobile_veterinario_or_403(db, current_user)
    internacao = (
        _query_internacoes(db, tenant_id, veterinario.id)
        .filter(InternacaoVet.id == internacao_id)
        .first()
    )
    if not internacao:
        raise HTTPException(status_code=404, detail="Internacao nao encontrada")

    evolucoes = (
        db.query(EvolucaoInternacao)
        .filter(
            EvolucaoInternacao.tenant_id == tenant_id,
            EvolucaoInternacao.internacao_id == internacao_id,
        )
        .order_by(EvolucaoInternacao.data_hora.desc())
        .all()
    )
    evolucoes_formatadas, procedimentos_realizados = _separar_evolucoes_e_procedimentos(evolucoes)

    procedimentos_agenda = (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .filter(
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
            InternacaoProcedimentoAgenda.internacao_id == internacao_id,
        )
        .order_by(InternacaoProcedimentoAgenda.horario_agendado.asc())
        .all()
    )

    pet = internacao.pet
    tutor = getattr(pet, "cliente", None) if pet else None
    payload = _internacao_mobile_dict(internacao)
    payload.update({
        "tutor_id": getattr(tutor, "id", None),
        "tutor_nome": getattr(tutor, "nome", None),
        "pet_raca": getattr(pet, "raca", None) if pet else None,
        "evolucoes": evolucoes_formatadas,
        "procedimentos_realizados": procedimentos_realizados,
        "procedimentos_agenda": [
            _serializar_procedimento_agenda_internacao(item)
            for item in procedimentos_agenda
        ],
    })
    return payload


@router.get("/procedimentos-agenda")
def listar_procedimentos_agenda_vet_mobile(
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    veterinario, tenant_id = _get_mobile_veterinario_or_403(db, current_user)
    procedimentos = _query_procedimentos_agenda(db, tenant_id, veterinario.id).limit(50).all()
    return [_serializar_procedimento_agenda_internacao(item) for item in procedimentos]


@router.patch("/procedimentos-agenda/{agenda_id}/concluir")
def concluir_procedimento_agenda_vet_mobile(
    agenda_id: int,
    payload: ConcluirProcedimentoMobilePayload | None = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    veterinario, tenant_id = _get_mobile_veterinario_or_403(db, current_user)
    item = _query_procedimentos_agenda(db, tenant_id, veterinario.id).filter(
        InternacaoProcedimentoAgenda.id == agenda_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Procedimento pendente nao encontrado")

    item.status = "concluido"
    item.horario_execucao = _vet_now()
    item.executado_por = veterinario.nome or getattr(current_user, "nome", None) or current_user.email
    item.observacao_execucao = payload.observacao_execucao if payload else None
    if item.quantidade_executada is None:
        item.quantidade_executada = item.quantidade_prevista

    db.commit()
    db.refresh(item)
    return _serializar_procedimento_agenda_internacao(item)


@router.get("/catalogo/medicamentos")
def listar_medicamentos_vet_mobile(
    busca: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    _, tenant_id = _get_mobile_veterinario_or_403(db, current_user)
    query = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa: E712
    )
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                MedicamentoCatalogo.nome.ilike(termo),
                MedicamentoCatalogo.nome_comercial.ilike(termo),
                MedicamentoCatalogo.principio_ativo.ilike(termo),
            )
        )

    medicamentos = query.order_by(MedicamentoCatalogo.nome.asc()).limit(80).all()
    return [_medicamento_mobile_dict(item) for item in medicamentos]


def _query_agendamentos(
    db: Session,
    tenant_id: str,
    veterinario_id: int,
    inicio: datetime,
    fim: datetime,
):
    return (
        db.query(AgendamentoVet)
        .options(
            joinedload(AgendamentoVet.pet),
            joinedload(AgendamentoVet.cliente),
            joinedload(AgendamentoVet.veterinario),
            joinedload(AgendamentoVet.consultorio),
        )
        .filter(
            AgendamentoVet.tenant_id == tenant_id,
            AgendamentoVet.veterinario_id == veterinario_id,
            AgendamentoVet.status.notin_(["cancelado", "faltou"]),
            AgendamentoVet.data_hora >= inicio,
            AgendamentoVet.data_hora <= fim,
        )
        .order_by(AgendamentoVet.data_hora.asc())
    )


def _query_internacoes(db: Session, tenant_id: str, veterinario_id: int):
    return (
        db.query(InternacaoVet)
        .options(joinedload(InternacaoVet.pet))
        .filter(
            InternacaoVet.tenant_id == tenant_id,
            InternacaoVet.status == "internado",
            or_(InternacaoVet.veterinario_id == veterinario_id, InternacaoVet.veterinario_id.is_(None)),
        )
        .order_by(InternacaoVet.data_entrada.asc())
    )


def _query_procedimentos_agenda(db: Session, tenant_id: str, veterinario_id: int):
    return (
        db.query(InternacaoProcedimentoAgenda)
        .options(
            joinedload(InternacaoProcedimentoAgenda.internacao),
            joinedload(InternacaoProcedimentoAgenda.pet),
        )
        .join(InternacaoVet, InternacaoVet.id == InternacaoProcedimentoAgenda.internacao_id)
        .filter(
            InternacaoProcedimentoAgenda.tenant_id == tenant_id,
            InternacaoProcedimentoAgenda.status == "agendado",
            InternacaoVet.status == "internado",
            or_(InternacaoVet.veterinario_id == veterinario_id, InternacaoVet.veterinario_id.is_(None)),
        )
        .order_by(InternacaoProcedimentoAgenda.horario_agendado.asc())
    )
