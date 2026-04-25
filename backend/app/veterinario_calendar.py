"""Helpers de calendario da agenda veterinaria.

Este modulo concentra geracao de token, payload de calendario e arquivo ICS.
As rotas continuam em ``veterinario_routes.py`` para preservar os contratos
publicos enquanto o monolito e quebrado em etapas seguras.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .models import Cliente, User
from .veterinario_models import AgendamentoVet


CALENDARIO_VET_DIAS_PASSADOS = 30
CALENDARIO_VET_DIAS_FUTUROS = 180

TIPO_AGENDAMENTO_LABEL = {
    "consulta": "Consulta",
    "retorno": "Retorno",
    "vacina": "Vacina",
    "exame": "Exame",
}

STATUS_AGENDAMENTO_LABEL = {
    "agendado": "Agendado",
    "confirmado": "Confirmado",
    "aguardando": "Aguardando",
    "em_atendimento": "Em atendimento",
    "finalizado": "Finalizado",
    "cancelado": "Cancelado",
}


def gerar_token_calendario_vet(db: Session) -> str:
    while True:
        token = secrets.token_urlsafe(32)
        existe = db.query(User.id).filter(User.vet_calendar_token == token).first()
        if not existe:
            return token


def garantir_token_calendario_vet(db: Session, user: User) -> str:
    if getattr(user, "vet_calendar_token", None):
        return user.vet_calendar_token
    user.vet_calendar_token = gerar_token_calendario_vet(db)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.vet_calendar_token


def resolver_veterinario_por_usuario(db: Session, tenant_id, user: Optional[User]) -> Optional[Cliente]:
    email = (getattr(user, "email", None) or "").strip().lower()
    if not email:
        return None

    return (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "veterinario",
            Cliente.ativo == True,
            func.lower(Cliente.email) == email,
        )
        .order_by(Cliente.id.asc())
        .first()
    )


def montar_urls_calendario_vet(request: Request, token: str) -> tuple[str, str]:
    base_url = str(request.base_url).rstrip("/")
    feed_url = f"{base_url}/api/vet/agenda/feed/{token}.ics"
    if feed_url.startswith("https://"):
        webcal_url = f"webcal://{feed_url[len('https://'):]}"
    elif feed_url.startswith("http://"):
        webcal_url = f"webcal://{feed_url[len('http://'):]}"
    else:
        webcal_url = feed_url
    return feed_url, webcal_url


def buscar_agendamentos_para_calendario(
    db: Session,
    *,
    tenant_id,
    veterinario_id: Optional[int] = None,
) -> list[AgendamentoVet]:
    data_inicio = datetime.now() - timedelta(days=CALENDARIO_VET_DIAS_PASSADOS)
    data_fim = datetime.now() + timedelta(days=CALENDARIO_VET_DIAS_FUTUROS)
    consulta = (
        db.query(AgendamentoVet)
        .options(
            joinedload(AgendamentoVet.pet),
            joinedload(AgendamentoVet.cliente),
            joinedload(AgendamentoVet.veterinario),
            joinedload(AgendamentoVet.consultorio),
        )
        .filter(
            AgendamentoVet.tenant_id == tenant_id,
            AgendamentoVet.data_hora >= data_inicio,
            AgendamentoVet.data_hora <= data_fim,
            AgendamentoVet.status != "cancelado",
        )
    )
    if veterinario_id:
        consulta = consulta.filter(AgendamentoVet.veterinario_id == veterinario_id)
    return consulta.order_by(AgendamentoVet.data_hora.asc()).all()


def escape_ics(value: Optional[str]) -> str:
    texto = str(value or "")
    texto = texto.replace("\\", "\\\\")
    texto = texto.replace(";", "\\;")
    texto = texto.replace(",", "\\,")
    texto = texto.replace("\r\n", "\\n").replace("\n", "\\n")
    return texto


def formatar_datetime_ics(data_hora: datetime) -> str:
    if data_hora.tzinfo:
        return data_hora.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return data_hora.strftime("%Y%m%dT%H%M%S")


def gerar_calendario_ics(
    agendamentos: list[AgendamentoVet],
    *,
    nome_calendario: str,
) -> str:
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sistema Pet//Agenda Veterinaria//PT-BR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + escape_ics(nome_calendario),
        "X-WR-TIMEZONE:America/Sao_Paulo",
    ]

    for ag in agendamentos:
        data_inicio = ag.data_hora
        data_fim = data_inicio + timedelta(minutes=ag.duracao_minutos or 30)
        pet_nome = ag.pet.nome if ag.pet else f"Pet #{ag.pet_id}"
        tutor_nome = ag.cliente.nome if ag.cliente else None
        vet_nome = ag.veterinario.nome if ag.veterinario else None
        consultorio_nome = ag.consultorio.nome if ag.consultorio else None
        tipo_label = TIPO_AGENDAMENTO_LABEL.get(ag.tipo, (ag.tipo or "Consulta").title())
        status_label = STATUS_AGENDAMENTO_LABEL.get(ag.status, ag.status or "Agendado")

        detalhes = [
            f"Tipo: {tipo_label}",
            f"Status: {status_label}",
        ]
        if tutor_nome:
            detalhes.append(f"Tutor: {tutor_nome}")
        if vet_nome:
            detalhes.append(f"Veterinario: {vet_nome}")
        if consultorio_nome:
            detalhes.append(f"Consultorio: {consultorio_nome}")
        if ag.motivo:
            detalhes.append(f"Motivo: {ag.motivo}")
        if ag.observacoes:
            detalhes.append(f"Observacoes: {ag.observacoes}")

        linhas.extend([
            "BEGIN:VEVENT",
            f"UID:vet-agendamento-{ag.id}@sistemapet",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{formatar_datetime_ics(data_inicio)}",
            f"DTEND:{formatar_datetime_ics(data_fim)}",
            "SUMMARY:" + escape_ics(f"{tipo_label} - {pet_nome}"),
            "DESCRIPTION:" + escape_ics("\n".join(detalhes)),
            "STATUS:CONFIRMED",
        ])
        if consultorio_nome:
            linhas.append("LOCATION:" + escape_ics(consultorio_nome))
        linhas.append("END:VEVENT")

    linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas)


def montar_payload_calendario_vet(
    db: Session,
    request: Request,
    *,
    user: User,
    tenant_id,
) -> dict:
    token = garantir_token_calendario_vet(db, user)
    feed_url, webcal_url = montar_urls_calendario_vet(request, token)
    veterinario = resolver_veterinario_por_usuario(db, tenant_id, user)
    if veterinario:
        escopo = "veterinario"
        veterinario_id = veterinario.id
        veterinario_nome = veterinario.nome
        mensagem_escopo = "O calendario exibe apenas os agendamentos vinculados ao seu usuario veterinario."
    else:
        escopo = "tenant"
        veterinario_id = None
        veterinario_nome = None
        mensagem_escopo = "Nao encontramos um cadastro de veterinario com o mesmo e-mail deste usuario. O calendario vai mostrar a agenda geral da empresa."

    return {
        "feed_token": token,
        "feed_url": feed_url,
        "webcal_url": webcal_url,
        "escopo": escopo,
        "veterinario_id": veterinario_id,
        "veterinario_nome": veterinario_nome,
        "mensagem_escopo": mensagem_escopo,
        "janela_dias_passados": CALENDARIO_VET_DIAS_PASSADOS,
        "janela_dias_futuros": CALENDARIO_VET_DIAS_FUTUROS,
    }
