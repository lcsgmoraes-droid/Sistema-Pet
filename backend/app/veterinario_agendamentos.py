"""Helpers de agenda e consultas veterinarias."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from .models import Cliente
from .veterinario_core import _serializar_datetime_vet, _vet_now
from .veterinario_models import (
    AgendamentoVet,
    ConsultaVet,
    ConsultorioVet,
    ExameVet,
    FotoClinica,
    InternacaoVet,
    PesoRegistro,
    PrescricaoVet,
    ProcedimentoConsulta,
    VacinaRegistro,
)


def _sincronizar_marcos_agendamento(ag: AgendamentoVet) -> None:
    agora = _vet_now()
    if ag.status in {"agendado", "confirmado", "aguardando"}:
        ag.inicio_atendimento = None
        ag.fim_atendimento = None
        return
    if ag.status == "em_atendimento" and not ag.inicio_atendimento:
        ag.inicio_atendimento = agora
    if ag.status == "finalizado":
        if not ag.inicio_atendimento:
            ag.inicio_atendimento = agora
        if not ag.fim_atendimento:
            ag.fim_atendimento = agora


def _atualizar_status_agendamento(
    db: Session,
    *,
    tenant_id,
    agendamento_id: Optional[int],
    status_agendamento: str,
) -> Optional[AgendamentoVet]:
    if not agendamento_id:
        return None

    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        return None

    ag.status = status_agendamento
    _sincronizar_marcos_agendamento(ag)
    return ag


def _validar_veterinario_agendamento(db: Session, tenant_id, veterinario_id: Optional[int]) -> Optional[Cliente]:
    if not veterinario_id:
        return None

    veterinario = db.query(Cliente).filter(
        Cliente.id == veterinario_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == "veterinario",
        Cliente.ativo == True,
    ).first()
    if not veterinario:
        raise HTTPException(status_code=422, detail="Veterinario selecionado nao foi encontrado ou esta inativo")
    return veterinario


def _validar_consultorio_agendamento(db: Session, tenant_id, consultorio_id: Optional[int]) -> Optional[ConsultorioVet]:
    if not consultorio_id:
        return None

    consultorio = db.query(ConsultorioVet).filter(
        ConsultorioVet.id == consultorio_id,
        ConsultorioVet.tenant_id == tenant_id,
        ConsultorioVet.ativo == True,
    ).first()
    if not consultorio:
        raise HTTPException(status_code=422, detail="Consultorio selecionado nao foi encontrado ou esta inativo")
    return consultorio


def _agendamento_intervalo(data_hora: datetime, duracao_minutos: Optional[int]) -> tuple[datetime, datetime]:
    inicio = data_hora
    fim = data_hora + timedelta(minutes=max(int(duracao_minutos or 30), 1))
    return inicio, fim


def _garantir_sem_conflitos_agendamento(
    db: Session,
    *,
    tenant_id,
    data_hora: datetime,
    duracao_minutos: Optional[int],
    veterinario_id: Optional[int],
    consultorio_id: Optional[int],
    agendamento_id_ignorar: Optional[int] = None,
) -> None:
    if not veterinario_id and not consultorio_id:
        return

    consulta = db.query(AgendamentoVet).options(
        joinedload(AgendamentoVet.veterinario),
        joinedload(AgendamentoVet.consultorio),
    ).filter(
        AgendamentoVet.tenant_id == tenant_id,
        func.date(AgendamentoVet.data_hora) == data_hora.date(),
        AgendamentoVet.status != "cancelado",
    )

    if agendamento_id_ignorar:
        consulta = consulta.filter(AgendamentoVet.id != agendamento_id_ignorar)

    if veterinario_id and consultorio_id:
        consulta = consulta.filter(
            or_(
                AgendamentoVet.veterinario_id == veterinario_id,
                AgendamentoVet.consultorio_id == consultorio_id,
            )
        )
    elif veterinario_id:
        consulta = consulta.filter(AgendamentoVet.veterinario_id == veterinario_id)
    else:
        consulta = consulta.filter(AgendamentoVet.consultorio_id == consultorio_id)

    novo_inicio, novo_fim = _agendamento_intervalo(data_hora, duracao_minutos)
    conflito_veterinario = None
    conflito_consultorio = None

    for existente in consulta.all():
        existente_inicio, existente_fim = _agendamento_intervalo(existente.data_hora, existente.duracao_minutos)
        if novo_inicio >= existente_fim or novo_fim <= existente_inicio:
            continue

        if veterinario_id and existente.veterinario_id == veterinario_id and conflito_veterinario is None:
            conflito_veterinario = existente
        if consultorio_id and existente.consultorio_id == consultorio_id and conflito_consultorio is None:
            conflito_consultorio = existente

    mensagens = []
    if conflito_veterinario:
        nome_vet = conflito_veterinario.veterinario.nome if conflito_veterinario.veterinario else "O veterinario selecionado"
        mensagens.append(
            f"{nome_vet} ja possui outro agendamento em conflito nesse horario"
        )
    if conflito_consultorio:
        nome_consultorio = conflito_consultorio.consultorio.nome if conflito_consultorio.consultorio else "O consultorio selecionado"
        mensagens.append(
            f"{nome_consultorio} ja esta reservado nesse horario"
        )
    if mensagens:
        raise HTTPException(status_code=409, detail=". ".join(mensagens) + ".")


def _consulta_tem_conteudo_clinico(consulta: ConsultaVet) -> bool:
    campos_texto = [
        "historia_clinica",
        "exame_fisico",
        "hipotese_diagnostica",
        "diagnostico",
        "diagnostico_simples",
        "conduta",
        "asa_justificativa",
        "observacoes_internas",
        "observacoes_tutor",
    ]
    for campo in campos_texto:
        valor = getattr(consulta, campo, None)
        if isinstance(valor, str) and valor.strip():
            return True

    campos_numericos = [
        "peso_consulta",
        "temperatura",
        "frequencia_cardiaca",
        "frequencia_respiratoria",
        "nivel_dor",
        "saturacao_o2",
        "pressao_sistolica",
        "pressao_diastolica",
        "glicemia",
        "retorno_em_dias",
        "asa_score",
    ]
    for campo in campos_numericos:
        if getattr(consulta, campo, None) is not None:
            return True

    if getattr(consulta, "data_retorno", None) is not None:
        return True
    if getattr(consulta, "tpc", None):
        return True
    if getattr(consulta, "mucosas", None):
        return True
    if getattr(consulta, "hidratacao", None):
        return True
    return False


def _consulta_tem_dependencias(db: Session, tenant_id, consulta_id: int) -> bool:
    checagens = (
        db.query(PrescricaoVet.id).filter(PrescricaoVet.tenant_id == tenant_id, PrescricaoVet.consulta_id == consulta_id).first(),
        db.query(ExameVet.id).filter(ExameVet.tenant_id == tenant_id, ExameVet.consulta_id == consulta_id).first(),
        db.query(ProcedimentoConsulta.id).filter(ProcedimentoConsulta.tenant_id == tenant_id, ProcedimentoConsulta.consulta_id == consulta_id).first(),
        db.query(FotoClinica.id).filter(FotoClinica.tenant_id == tenant_id, FotoClinica.consulta_id == consulta_id).first(),
        db.query(VacinaRegistro.id).filter(VacinaRegistro.tenant_id == tenant_id, VacinaRegistro.consulta_id == consulta_id).first(),
        db.query(InternacaoVet.id).filter(InternacaoVet.tenant_id == tenant_id, InternacaoVet.consulta_id == consulta_id).first(),
        db.query(PesoRegistro.id).filter(PesoRegistro.tenant_id == tenant_id, PesoRegistro.consulta_id == consulta_id).first(),
    )
    return any(item is not None for item in checagens)


def _agendamento_to_dict(ag: AgendamentoVet) -> dict:
    return {
        "id": ag.id,
        "pet_id": ag.pet_id,
        "cliente_id": ag.cliente_id,
        "veterinario_id": ag.veterinario_id,
        "consultorio_id": ag.consultorio_id,
        "data_hora": _serializar_datetime_vet(ag.data_hora),
        "duracao_minutos": ag.duracao_minutos,
        "tipo": ag.tipo,
        "motivo": ag.motivo,
        "status": ag.status,
        "is_emergencia": ag.is_emergencia,
        "consulta_id": ag.consulta_id,
        "observacoes": ag.observacoes,
        "created_at": _serializar_datetime_vet(ag.created_at),
        "pet_nome": ag.pet.nome if ag.pet else None,
        "cliente_nome": ag.cliente.nome if ag.cliente else None,
        "veterinario_nome": ag.veterinario.nome if ag.veterinario else None,
        "consultorio_nome": ag.consultorio.nome if ag.consultorio else None,
    }
