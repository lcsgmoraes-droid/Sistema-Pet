"""Sugestao de horarios livres para a agenda de Banho & Tosa."""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.banho_tosa_api.utils import obter_ou_criar_configuracao
from app.banho_tosa_agenda_capacity import (
    _query_sobreposicao,
    ocupacao_maxima_intervalo,
)
from app.banho_tosa_models import BanhoTosaAgendamento, BanhoTosaRecurso


def sugerir_slots_agenda(
    db: Session,
    tenant_id,
    *,
    data_ref: date,
    duracao_minutos: int = 60,
    recurso_id: Optional[int] = None,
    limit: int = 12,
) -> list[dict]:
    config = obter_ou_criar_configuracao(db, tenant_id)
    recursos = _listar_recursos(db, tenant_id, recurso_id)
    if not recursos:
        return []

    inicio_janela = datetime.combine(data_ref, _parse_hora(config.horario_inicio, 8, 0))
    fim_janela = datetime.combine(data_ref, _parse_hora(config.horario_fim, 18, 0))
    intervalo = max(int(config.intervalo_slot_minutos or 30), 5)
    duracao = max(int(duracao_minutos or 60), intervalo)
    agendamentos = _listar_agendamentos_dia(db, tenant_id, data_ref)

    sugestoes = []
    cursor = inicio_janela
    while cursor + timedelta(minutes=duracao) <= fim_janela:
        slot_fim = cursor + timedelta(minutes=duracao)
        sugestoes.extend(
            _avaliar_recursos_no_slot(recursos, agendamentos, cursor, slot_fim)
        )
        cursor += timedelta(minutes=intervalo)

    sugestoes.sort(
        key=lambda item: (
            item["ocupacao_no_slot"],
            item["horario_inicio"],
            item["recurso_nome"],
        )
    )
    return sugestoes[:limit]


def _listar_recursos(
    db: Session, tenant_id, recurso_id: Optional[int]
) -> list[BanhoTosaRecurso]:
    query = db.query(BanhoTosaRecurso).filter(
        BanhoTosaRecurso.tenant_id == tenant_id,
        BanhoTosaRecurso.ativo.is_(True),
    )
    if recurso_id:
        query = query.filter(BanhoTosaRecurso.id == recurso_id)
    return query.order_by(
        BanhoTosaRecurso.tipo.asc(), BanhoTosaRecurso.nome.asc()
    ).all()


def _listar_agendamentos_dia(
    db: Session, tenant_id, data_ref: date
) -> list[BanhoTosaAgendamento]:
    inicio_dia = datetime.combine(data_ref, _parse_hora("00:00", 0, 0))
    fim_dia = inicio_dia + timedelta(days=1)
    return _query_sobreposicao(db, tenant_id, inicio_dia, fim_dia, None).all()


def _avaliar_recursos_no_slot(
    recursos, agendamentos, inicio: datetime, fim: datetime
) -> list[dict]:
    sugestoes = []
    for recurso in recursos:
        ocupacao = _ocupacao_recurso_no_slot(agendamentos, recurso.id, inicio, fim)
        capacidade = max(int(recurso.capacidade_simultanea or 1), 1)
        if ocupacao >= capacidade:
            continue
        sugestoes.append(
            {
                "horario_inicio": inicio,
                "horario_fim": fim,
                "recurso_id": recurso.id,
                "recurso_nome": recurso.nome,
                "recurso_tipo": recurso.tipo,
                "capacidade_simultanea": capacidade,
                "ocupacao_no_slot": ocupacao,
                "vagas_disponiveis": capacidade - ocupacao,
                "motivo": "Livre"
                if ocupacao == 0
                else "Encaixe com capacidade disponivel",
            }
        )
    return sugestoes


def _ocupacao_recurso_no_slot(
    agendamentos, recurso_id: int, inicio: datetime, fim: datetime
) -> int:
    return ocupacao_maxima_intervalo(
        [item for item in agendamentos if item.recurso_id == recurso_id], inicio, fim
    )


def _parse_hora(valor: str, hora_padrao: int, minuto_padrao: int):
    try:
        hora, minuto = str(valor or "").split(":")[:2]
        return datetime.strptime(f"{int(hora):02d}:{int(minuto):02d}", "%H:%M").time()
    except (TypeError, ValueError):
        return datetime.strptime(
            f"{hora_padrao:02d}:{minuto_padrao:02d}", "%H:%M"
        ).time()
