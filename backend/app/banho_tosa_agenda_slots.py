"""Sugestao de horarios livres para a agenda de Banho & Tosa."""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.banho_tosa_api.utils import STATUS_AGENDAMENTO_FINAIS, obter_ou_criar_configuracao
from app.banho_tosa_datetime import normalizar_data_operacional
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

    sugestoes.sort(key=lambda item: (item["ocupacao_no_slot"], item["horario_inicio"], item["recurso_nome"]))
    return sugestoes[:limit]


def _listar_recursos(db: Session, tenant_id, recurso_id: Optional[int]) -> list[BanhoTosaRecurso]:
    query = db.query(BanhoTosaRecurso).filter(
        BanhoTosaRecurso.tenant_id == tenant_id,
        BanhoTosaRecurso.ativo == True,
    )
    if recurso_id:
        query = query.filter(BanhoTosaRecurso.id == recurso_id)
    return query.order_by(BanhoTosaRecurso.tipo.asc(), BanhoTosaRecurso.nome.asc()).all()


def _listar_agendamentos_dia(db: Session, tenant_id, data_ref: date) -> list[BanhoTosaAgendamento]:
    inicio_dia = datetime.combine(data_ref, _parse_hora("00:00", 0, 0))
    fim_dia = datetime.combine(data_ref, _parse_hora("23:59", 23, 59))
    return db.query(BanhoTosaAgendamento).filter(
        BanhoTosaAgendamento.tenant_id == tenant_id,
        BanhoTosaAgendamento.status.notin_(list(STATUS_AGENDAMENTO_FINAIS)),
        BanhoTosaAgendamento.data_hora_inicio >= inicio_dia,
        BanhoTosaAgendamento.data_hora_inicio <= fim_dia,
    ).all()


def _avaliar_recursos_no_slot(recursos, agendamentos, inicio: datetime, fim: datetime) -> list[dict]:
    sugestoes = []
    for recurso in recursos:
        ocupacao = _ocupacao_recurso_no_slot(agendamentos, recurso.id, inicio, fim)
        capacidade = max(int(recurso.capacidade_simultanea or 1), 1)
        if ocupacao >= capacidade:
            continue
        sugestoes.append({
            "horario_inicio": inicio,
            "horario_fim": fim,
            "recurso_id": recurso.id,
            "recurso_nome": recurso.nome,
            "recurso_tipo": recurso.tipo,
            "capacidade_simultanea": capacidade,
            "ocupacao_no_slot": ocupacao,
            "vagas_disponiveis": capacidade - ocupacao,
            "motivo": "Livre" if ocupacao == 0 else "Encaixe com capacidade disponivel",
        })
    return sugestoes


def _ocupacao_recurso_no_slot(agendamentos, recurso_id: int, inicio: datetime, fim: datetime) -> int:
    total = 0
    inicio_slot = normalizar_data_operacional(inicio)
    fim_slot = normalizar_data_operacional(fim)
    for agendamento in agendamentos:
        if agendamento.recurso_id != recurso_id:
            continue
        ag_inicio = normalizar_data_operacional(agendamento.data_hora_inicio)
        ag_fim = normalizar_data_operacional(agendamento.data_hora_fim_prevista) or ag_inicio
        if ag_inicio < fim_slot and ag_fim > inicio_slot:
            total += 1
    return total


def _parse_hora(valor: str, hora_padrao: int, minuto_padrao: int):
    try:
        hora, minuto = str(valor or "").split(":")[:2]
        return datetime.strptime(f"{int(hora):02d}:{int(minuto):02d}", "%H:%M").time()
    except (TypeError, ValueError):
        return datetime.strptime(f"{hora_padrao:02d}:{minuto_padrao:02d}", "%H:%M").time()
