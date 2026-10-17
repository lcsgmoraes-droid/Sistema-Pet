"""Regras de capacidade e ocupacao da agenda de Banho & Tosa."""

from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_api.utils import (
    STATUS_AGENDAMENTO_FINAIS,
    obter_ou_criar_configuracao,
)
from app.banho_tosa_datetime import normalizar_data_operacional
from app.banho_tosa_models import BanhoTosaAgendamento, BanhoTosaRecurso
from app.models import Cliente


def validar_capacidade_agenda(
    db: Session,
    tenant_id,
    *,
    pet_id: int,
    inicio: datetime,
    fim: datetime,
    profissional_principal_id: Optional[int] = None,
    banhista_id: Optional[int] = None,
    tosador_id: Optional[int] = None,
    recurso_id: Optional[int] = None,
    ignorar_agendamento_id: Optional[int] = None,
) -> Optional[BanhoTosaRecurso]:
    """Valida conflitos por pet, equipe e capacidade do recurso."""
    equipe_ids = {
        item for item in [profissional_principal_id, banhista_id, tosador_id] if item
    }
    if equipe_ids:
        profissionais = (
            db.query(Cliente.id)
            .filter(
                Cliente.id.in_(equipe_ids),
                Cliente.tenant_id == tenant_id,
                Cliente.ativo.is_(True),
            )
            .all()
        )
        if {item[0] for item in profissionais} != equipe_ids:
            raise HTTPException(
                status_code=404,
                detail="Profissional nao encontrado ou inativo nesta loja",
            )

    query = _query_sobreposicao(db, tenant_id, inicio, fim, ignorar_agendamento_id)

    conflito_pet = query.filter(BanhoTosaAgendamento.pet_id == pet_id).first()
    if conflito_pet:
        raise HTTPException(
            status_code=409, detail="Pet ja possui agendamento nesse horario"
        )

    if equipe_ids:
        conflito_equipe = query.filter(
            or_(
                BanhoTosaAgendamento.profissional_principal_id.in_(equipe_ids),
                BanhoTosaAgendamento.banhista_id.in_(equipe_ids),
                BanhoTosaAgendamento.tosador_id.in_(equipe_ids),
            )
        ).first()
        if conflito_equipe:
            raise HTTPException(
                status_code=409,
                detail="Profissional ja possui agendamento nesse horario",
            )

    if not recurso_id:
        return None

    recurso = (
        db.query(BanhoTosaRecurso)
        .filter(
            BanhoTosaRecurso.id == recurso_id,
            BanhoTosaRecurso.tenant_id == tenant_id,
            BanhoTosaRecurso.ativo.is_(True),
        )
        .first()
    )
    if not recurso:
        raise HTTPException(status_code=404, detail="Recurso nao encontrado ou inativo")

    agendamentos_recurso = query.filter(
        BanhoTosaAgendamento.recurso_id == recurso.id
    ).all()
    ocupacao_recurso = ocupacao_maxima_intervalo(agendamentos_recurso, inicio, fim)
    capacidade = max(int(recurso.capacidade_simultanea or 1), 1)
    if ocupacao_recurso >= capacidade:
        raise HTTPException(
            status_code=409, detail="Recurso sem capacidade nesse horario"
        )

    return recurso


def ocupacao_maxima_intervalo(agendamentos, inicio: datetime, fim: datetime) -> int:
    """Pico simultaneo dentro do intervalo; fronteiras adjacentes nao conflitam."""
    inicio = normalizar_data_operacional(inicio)
    fim = normalizar_data_operacional(fim)
    janelas = []
    for agendamento in agendamentos:
        ag_inicio = normalizar_data_operacional(agendamento.data_hora_inicio)
        ag_fim = (
            normalizar_data_operacional(agendamento.data_hora_fim_prevista) or ag_inicio
        )
        inicio_comum, fim_comum = max(inicio, ag_inicio), min(fim, ag_fim)
        if inicio_comum < fim_comum:
            janelas.append((inicio_comum, fim_comum))
    return _calcular_pico(janelas)


def montar_capacidade_dia(db: Session, tenant_id, data_ref: date) -> dict:
    config = obter_ou_criar_configuracao(db, tenant_id)
    inicio_dia = datetime.combine(data_ref, time.min)
    fim_dia = inicio_dia + timedelta(days=1)
    janela_inicio, janela_fim, minutos_disponiveis = _janela_operacional(config)

    recursos = (
        db.query(BanhoTosaRecurso)
        .filter(
            BanhoTosaRecurso.tenant_id == tenant_id,
            BanhoTosaRecurso.ativo.is_(True),
        )
        .order_by(BanhoTosaRecurso.tipo.asc(), BanhoTosaRecurso.nome.asc())
        .all()
    )

    agendamentos = (
        _query_sobreposicao(db, tenant_id, inicio_dia, fim_dia, None)
        .options(joinedload(BanhoTosaAgendamento.recurso))
        .all()
    )

    por_recurso = {
        recurso.id: _base_recurso(recurso, minutos_disponiveis) for recurso in recursos
    }
    janelas_por_recurso = {recurso.id: [] for recurso in recursos}
    sem_recurso = 0

    for agendamento in agendamentos:
        if not agendamento.recurso_id or agendamento.recurso_id not in por_recurso:
            sem_recurso += 1
            continue

        inicio_original = normalizar_data_operacional(agendamento.data_hora_inicio)
        fim_original = (
            normalizar_data_operacional(agendamento.data_hora_fim_prevista)
            or inicio_original
        )
        inicio, fim = max(inicio_original, inicio_dia), min(fim_original, fim_dia)
        duracao = _duracao_minutos(inicio, fim)
        item = por_recurso[agendamento.recurso_id]
        item["agendamentos"] += 1
        item["minutos_ocupados"] += duracao
        item["intervalos_ocupados"].append(
            {"data_hora_inicio": inicio, "data_hora_fim_prevista": fim}
        )
        janelas_por_recurso[agendamento.recurso_id].append((inicio, fim))

    alertas = []
    for recurso_id, item in por_recurso.items():
        capacidade = max(int(item["capacidade_simultanea"] or 1), 1)
        disponivel = max(minutos_disponiveis * capacidade, 1)
        item["pico_simultaneo"] = _calcular_pico(janelas_por_recurso[recurso_id])
        item["ocupacao_percentual"] = round(
            (item["minutos_ocupados"] / disponivel) * 100, 2
        )
        item["capacidade_excedida"] = item["pico_simultaneo"] > capacidade
        if item["capacidade_excedida"]:
            alertas.append(
                f"{item['recurso_nome']} ultrapassou a capacidade simultanea"
            )

    if not recursos:
        alertas.append("Cadastre recursos para controlar capacidade da agenda")
    if sem_recurso:
        alertas.append(f"{sem_recurso} agendamento(s) sem recurso definido")

    return {
        "data": data_ref,
        "janela_inicio": janela_inicio,
        "janela_fim": janela_fim,
        "total_agendamentos": len(agendamentos),
        "agendamentos_sem_recurso": sem_recurso,
        "recursos": list(por_recurso.values()),
        "alertas": alertas,
    }


def _query_sobreposicao(
    db: Session, tenant_id, inicio: datetime, fim: datetime, ignorar_id: Optional[int]
):
    query = db.query(BanhoTosaAgendamento).filter(
        BanhoTosaAgendamento.tenant_id == tenant_id,
        BanhoTosaAgendamento.status.notin_(list(STATUS_AGENDAMENTO_FINAIS)),
        BanhoTosaAgendamento.data_hora_inicio < fim,
        func.coalesce(
            BanhoTosaAgendamento.data_hora_fim_prevista,
            BanhoTosaAgendamento.data_hora_inicio,
        )
        > inicio,
    )
    if ignorar_id:
        query = query.filter(BanhoTosaAgendamento.id != ignorar_id)
    return query


def _janela_operacional(config) -> tuple[str, str, int]:
    inicio = _parse_hora(config.horario_inicio, time(8, 0))
    fim = _parse_hora(config.horario_fim, time(18, 0))
    minutos = max(
        int(
            (
                datetime.combine(date.today(), fim)
                - datetime.combine(date.today(), inicio)
            ).total_seconds()
            // 60
        ),
        60,
    )
    return inicio.strftime("%H:%M"), fim.strftime("%H:%M"), minutos


def _parse_hora(valor: str, fallback: time) -> time:
    try:
        hora, minuto = str(valor or "").split(":")[:2]
        return time(int(hora), int(minuto))
    except (TypeError, ValueError):
        return fallback


def _base_recurso(recurso: BanhoTosaRecurso, minutos_disponiveis: int) -> dict:
    return {
        "recurso_id": recurso.id,
        "recurso_nome": recurso.nome,
        "recurso_tipo": recurso.tipo,
        "capacidade_simultanea": max(int(recurso.capacidade_simultanea or 1), 1),
        "agendamentos": 0,
        "minutos_ocupados": 0,
        "minutos_disponiveis": minutos_disponiveis,
        "ocupacao_percentual": 0,
        "pico_simultaneo": 0,
        "capacidade_excedida": False,
        "intervalos_ocupados": [],
    }


def _duracao_minutos(inicio: datetime, fim: datetime) -> int:
    inicio_normalizado = normalizar_data_operacional(inicio)
    fim_normalizado = normalizar_data_operacional(fim)
    return max(int((fim_normalizado - inicio_normalizado).total_seconds() // 60), 0)


def _calcular_pico(janelas: list[tuple[datetime, datetime]]) -> int:
    eventos = []
    for inicio, fim in janelas:
        eventos.append((normalizar_data_operacional(inicio), 1))
        eventos.append((normalizar_data_operacional(fim), -1))

    atual = 0
    pico = 0
    for _, delta in sorted(eventos, key=lambda item: (item[0], item[1])):
        atual += delta
        pico = max(pico, atual)
    return pico
