"""Regras compartilhadas do fluxo de Taxi Dog."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.banho_tosa_models import BanhoTosaAgendamento, BanhoTosaAtendimento


TAXI_DOG_STATUS_FLOW = (
    "agendado",
    "motorista_a_caminho",
    "pet_coletado",
    "entregue_na_clinica",
    "aguardando_retorno",
    "retornando",
    "entregue_ao_tutor",
)

TAXI_DOG_STATUS_LABELS = {
    "agendado": "Agendado",
    "motorista_a_caminho": "Motorista a caminho",
    "pet_coletado": "Pet coletado",
    "entregue_na_clinica": "Pet entregue na loja",
    "aguardando_retorno": "Aguardando retorno",
    "retornando": "Retornando ao tutor",
    "entregue_ao_tutor": "Entregue ao tutor",
}


def fluxo_status_taxi_dog(tipo: str | None) -> tuple[str, ...]:
    tipo_normalizado = str(tipo or "ida_volta").strip().lower()
    if tipo_normalizado == "ida":
        return TAXI_DOG_STATUS_FLOW[:4]
    if tipo_normalizado == "volta":
        return (
            "agendado",
            "aguardando_retorno",
            "retornando",
            "entregue_ao_tutor",
        )
    return TAXI_DOG_STATUS_FLOW


def proximo_status_taxi_dog(status: str | None, tipo: str | None) -> str | None:
    fluxo = fluxo_status_taxi_dog(tipo)
    atual = str(status or "agendado").strip().lower()
    try:
        indice = fluxo.index(atual)
    except ValueError:
        return None
    if indice >= len(fluxo) - 1:
        return None
    return fluxo[indice + 1]


def validar_transicao_status_taxi_dog(
    status_atual: str | None,
    novo_status: str | None,
    tipo: str | None,
) -> str:
    atual = str(status_atual or "agendado").strip().lower()
    novo = str(novo_status or "").strip().lower()
    if novo == atual:
        return novo
    esperado = proximo_status_taxi_dog(atual, tipo)
    if not esperado or novo != esperado:
        esperado_label = TAXI_DOG_STATUS_LABELS.get(esperado or "", esperado or "finalizado")
        raise ValueError(f"Proxima etapa permitida: {esperado_label}")
    return novo


def sincronizar_chegada_taxi_dog(
    db: Session,
    tenant_id,
    *,
    agendamento_id: int | None,
) -> BanhoTosaAtendimento | None:
    """Coloca o pet na fila quando o motorista confirma a chegada na loja."""
    if not agendamento_id:
        return None

    agendamento = (
        db.query(BanhoTosaAgendamento)
        .filter(
            BanhoTosaAgendamento.tenant_id == tenant_id,
            BanhoTosaAgendamento.id == agendamento_id,
        )
        .first()
    )
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento do Taxi Dog nao encontrado")
    if agendamento.status in {"cancelado", "no_show", "entregue"}:
        raise HTTPException(
            status_code=422,
            detail="Agendamento finalizado nao pode entrar na fila",
        )

    atendimento = (
        db.query(BanhoTosaAtendimento)
        .filter(
            BanhoTosaAtendimento.tenant_id == tenant_id,
            BanhoTosaAtendimento.agendamento_id == agendamento.id,
        )
        .first()
    )
    if not atendimento:
        pet = agendamento.pet
        atendimento = BanhoTosaAtendimento(
            tenant_id=tenant_id,
            agendamento_id=agendamento.id,
            cliente_id=agendamento.cliente_id,
            pet_id=agendamento.pet_id,
            status="chegou",
            checkin_em=datetime.now(),
            porte_snapshot=pet.porte if pet else None,
            pelagem_snapshot=(pet.cor_pelagem or pet.cor) if pet else None,
            observacoes_entrada=agendamento.observacoes,
        )
        db.add(atendimento)

    agendamento.status = "em_atendimento"
    return atendimento
