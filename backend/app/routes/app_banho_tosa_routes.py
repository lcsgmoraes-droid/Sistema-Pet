"""Rotas do Banho & Tosa para o app do tutor."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_api.agenda_routes import criar_agendamento as criar_agendamento_erp
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaAvaliacao,
    BanhoTosaConfiguracao,
    BanhoTosaRecurso,
    BanhoTosaServico,
)
from app.banho_tosa_api.fluxo import estado_operacional_atendimento, etapa_ativa
from app.banho_tosa_api.utils import (
    STATUS_AGENDAMENTO_FINAIS,
    obter_ou_criar_configuracao,
)
from app.banho_tosa_schemas import (
    BanhoTosaAgendamentoCreate,
    BanhoTosaAgendamentoServicoInput,
)
from app.db import get_session
from app.models import User
from app.routes.app_mobile_routes import _get_cliente_or_404
from app.routes.ecommerce_auth import _get_current_ecommerce_user
from app.utils.timezone import now_brasilia

router = APIRouter(prefix="/app/banho-tosa", tags=["App Mobile - Banho & Tosa"])

STATUS_LABELS = {
    "agendado": "Agendado",
    "confirmado": "Confirmado",
    "chegou": "Pet recebido",
    "em_banho": "Em banho",
    "em_tosa": "Em tosa",
    "em_secagem": "Secagem",
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
    "em_secagem": 70,
    "secagem": 70,
    "em_tosa": 78,
    "pronto": 90,
    "entregue": 100,
}


class BanhoTosaAvaliacaoInput(BaseModel):
    nota_nps: int = Field(..., ge=0, le=10)
    nota_servico: Optional[int] = Field(default=None, ge=1, le=5)
    comentario: Optional[str] = Field(default=None, max_length=1000)


class BanhoTosaAgendamentoClienteInput(BaseModel):
    pet_id: int = Field(..., gt=0)
    servico_id: int = Field(..., gt=0)
    data_agendamento: date
    horario_inicio: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    observacoes: Optional[str] = Field(default=None, max_length=500)


@router.get("/calendario")
def obter_calendario_banho_tosa(
    data_inicio: Optional[str] = None,
    dias: int = 7,
    servico_id: Optional[int] = None,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Mostra disponibilidade para o app sem revelar pets/tutores agendados."""
    tenant_id = current_user.tenant_id
    config = obter_ou_criar_configuracao(db, tenant_id)
    servicos = (
        db.query(BanhoTosaServico)
        .filter(
            BanhoTosaServico.tenant_id == tenant_id,
            BanhoTosaServico.ativo.is_(True),
        )
        .order_by(BanhoTosaServico.nome.asc())
        .all()
    )

    if not getattr(config, "mostrar_calendario_cliente", False):
        return {
            "visivel": False,
            "whatsapp": getattr(config, "whatsapp_agendamento", None),
            "servicos": [_serializar_servico(item) for item in servicos],
            "dias": [],
        }

    dias = max(1, min(int(dias or 7), 14))
    agora = now_brasilia()
    inicio = _parse_data(data_inicio) or agora.date()
    servico = (
        next((item for item in servicos if item.id == servico_id), None)
        if servico_id
        else None
    )
    duracao_minutos = int(getattr(servico, "duracao_padrao_minutos", None) or 60)
    slot_minutos = max(int(getattr(config, "intervalo_slot_minutos", None) or 30), 5)
    recursos = (
        db.query(BanhoTosaRecurso)
        .filter(
            BanhoTosaRecurso.tenant_id == tenant_id,
            BanhoTosaRecurso.ativo.is_(True),
        )
        .all()
    )
    capacidade_total = (
        sum(max(int(item.capacidade_simultanea or 1), 1) for item in recursos) or 1
    )
    data_fim = inicio + timedelta(days=dias)
    agendamentos = (
        db.query(BanhoTosaAgendamento)
        .filter(
            BanhoTosaAgendamento.tenant_id == tenant_id,
            BanhoTosaAgendamento.status.notin_(["cancelado", "no_show", "entregue"]),
            BanhoTosaAgendamento.data_hora_inicio >= datetime.combine(inicio, time.min),
            BanhoTosaAgendamento.data_hora_inicio
            < datetime.combine(data_fim, time.min),
        )
        .all()
    )

    calendario = []
    for offset in range(dias):
        dia = inicio + timedelta(days=offset)
        if not _dia_funciona(config, dia):
            calendario.append({"data": dia.isoformat(), "funciona": False, "slots": []})
            continue
        slots = []
        cursor = datetime.combine(dia, _parse_hora(config.horario_inicio) or time(8, 0))
        fim_dia = datetime.combine(dia, _parse_hora(config.horario_fim) or time(18, 0))
        while cursor + timedelta(minutes=duracao_minutos) <= fim_dia:
            slot_fim = cursor + timedelta(minutes=duracao_minutos)
            if cursor <= agora:
                vagas = 0
            else:
                ocupados = sum(
                    1
                    for item in agendamentos
                    if _intervalos_sobrepoem(cursor, slot_fim, item)
                )
                vagas = max(capacidade_total - ocupados, 0)
            slots.append(
                {
                    "horario_inicio": cursor.strftime("%H:%M"),
                    "horario_fim": slot_fim.strftime("%H:%M"),
                    "status": "disponivel" if vagas > 0 else "ocupado",
                    "vagas": vagas,
                }
            )
            cursor += timedelta(minutes=slot_minutos)
        calendario.append({"data": dia.isoformat(), "funciona": True, "slots": slots})

    return {
        "visivel": True,
        "whatsapp": getattr(config, "whatsapp_agendamento", None),
        "servicos": [_serializar_servico(item) for item in servicos],
        "dias": calendario,
    }


@router.get("/status")
def listar_status_banho_tosa(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    cliente = _get_cliente_or_404(db, current_user)
    tenant_id = current_user.tenant_id
    config = obter_ou_criar_configuracao(db, tenant_id)
    atendimentos = _listar_atendimentos_visiveis(db, tenant_id, cliente.id)
    agendamento_ids = {
        item.agendamento_id for item in atendimentos if item.agendamento_id
    }
    agendamentos = _listar_agendamentos_visiveis(
        db, tenant_id, cliente.id, agendamento_ids
    )
    itens = [_serializar_atendimento(item, config) for item in atendimentos]
    itens.extend(_serializar_agendamento(item) for item in agendamentos)
    itens = sorted(itens, key=lambda item: item.get("ordenacao") or "", reverse=True)
    return {
        "total": len(itens),
        "itens": [
            {k: v for k, v in item.items() if k != "ordenacao"} for item in itens
        ],
    }


@router.post("/agendamentos", status_code=201)
def criar_agendamento_cliente_banho_tosa(
    payload: BanhoTosaAgendamentoClienteInput,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Permite ao tutor reservar um horario livre para um pet da propria conta."""
    cliente = _get_cliente_or_404(db, current_user)
    tenant_id = current_user.tenant_id
    config = obter_ou_criar_configuracao(db, tenant_id)
    if not getattr(config, "mostrar_calendario_cliente", False):
        raise HTTPException(
            status_code=403,
            detail="A loja ainda nao liberou agendamentos pelo app.",
        )
    config = (
        db.query(BanhoTosaConfiguracao)
        .filter(
            BanhoTosaConfiguracao.id == config.id,
            BanhoTosaConfiguracao.tenant_id == tenant_id,
        )
        .with_for_update()
        .one()
    )

    servico = (
        db.query(BanhoTosaServico)
        .filter(
            BanhoTosaServico.id == payload.servico_id,
            BanhoTosaServico.tenant_id == tenant_id,
            BanhoTosaServico.ativo.is_(True),
        )
        .first()
    )
    if not servico:
        raise HTTPException(status_code=404, detail="Servico nao encontrado.")

    horario = _parse_hora(payload.horario_inicio)
    if not horario:
        raise HTTPException(status_code=422, detail="Horario invalido.")
    inicio = datetime.combine(payload.data_agendamento, horario)
    duracao = max(int(servico.duracao_padrao_minutos or 60), 1)
    fim = inicio + timedelta(minutes=duracao)
    _validar_slot_cliente(config, inicio, fim)
    recurso_id = _resolver_recurso_slot(db, tenant_id, inicio, fim)

    body = BanhoTosaAgendamentoCreate(
        cliente_id=cliente.id,
        pet_id=payload.pet_id,
        data_hora_inicio=inicio,
        data_hora_fim_prevista=fim,
        recurso_id=recurso_id,
        origem="app",
        observacoes=(payload.observacoes or "").strip() or None,
        valor_previsto=servico.preco_base or Decimal("0"),
        servicos=[
            BanhoTosaAgendamentoServicoInput(
                servico_id=servico.id,
                quantidade=Decimal("1"),
                valor_unitario=servico.preco_base or Decimal("0"),
                tempo_previsto_minutos=duracao,
            )
        ],
    )
    return criar_agendamento_erp(
        body=body,
        db=db,
        current=(current_user, tenant_id),
    )


@router.post("/atendimentos/{atendimento_id}/avaliacao")
def avaliar_atendimento_banho_tosa(
    atendimento_id: int,
    payload: BanhoTosaAvaliacaoInput,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    cliente = _get_cliente_or_404(db, current_user)
    atendimento = (
        db.query(BanhoTosaAtendimento)
        .filter(
            BanhoTosaAtendimento.tenant_id == current_user.tenant_id,
            BanhoTosaAtendimento.id == atendimento_id,
            BanhoTosaAtendimento.cliente_id == cliente.id,
        )
        .first()
    )
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado.")
    if atendimento.status != "entregue":
        raise HTTPException(
            status_code=422, detail="Avaliacao liberada apenas apos a entrega do pet."
        )
    avaliacao = (
        db.query(BanhoTosaAvaliacao)
        .filter(
            BanhoTosaAvaliacao.tenant_id == current_user.tenant_id,
            BanhoTosaAvaliacao.atendimento_id == atendimento.id,
            BanhoTosaAvaliacao.cliente_id == cliente.id,
        )
        .first()
    )
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


def _serializar_servico(item: BanhoTosaServico) -> dict:
    return {
        "id": item.id,
        "nome": item.nome,
        "duracao_padrao_minutos": item.duracao_padrao_minutos,
        "preco_base": _decimal(item.preco_base),
    }


def _parse_data(valor: Optional[str]) -> Optional[date]:
    if not valor:
        return None
    try:
        return datetime.strptime(valor[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_hora(valor: Optional[str]) -> Optional[time]:
    if not valor:
        return None
    try:
        horas, minutos = str(valor)[:5].split(":")
        return time(int(horas), int(minutos))
    except (ValueError, TypeError):
        return None


def _dia_funciona(config, dia: date) -> bool:
    dias = getattr(config, "dias_funcionamento", None) or []
    if not dias:
        return True
    nomes = {
        0: {"segunda", "seg"},
        1: {"terca", "terça", "ter"},
        2: {"quarta", "qua"},
        3: {"quinta", "qui"},
        4: {"sexta", "sex"},
        5: {"sabado", "sábado", "sab"},
        6: {"domingo", "dom"},
    }
    configurados = {str(item).strip().lower() for item in dias}
    return bool(nomes.get(dia.weekday(), set()) & configurados)


def _validar_slot_cliente(config, inicio: datetime, fim: datetime) -> None:
    agora = now_brasilia()
    if inicio <= agora:
        raise HTTPException(status_code=422, detail="Escolha um horario futuro.")
    if inicio.date() > agora.date() + timedelta(days=13):
        raise HTTPException(
            status_code=422,
            detail="Escolha um horario dentro dos proximos 14 dias.",
        )
    if not _dia_funciona(config, inicio.date()):
        raise HTTPException(status_code=422, detail="A loja nao funciona neste dia.")

    abertura = datetime.combine(
        inicio.date(), _parse_hora(config.horario_inicio) or time(8, 0)
    )
    fechamento = datetime.combine(
        inicio.date(), _parse_hora(config.horario_fim) or time(18, 0)
    )
    if inicio < abertura or fim > fechamento:
        raise HTTPException(
            status_code=422,
            detail="O horario esta fora da janela de atendimento da loja.",
        )

    intervalo = max(int(getattr(config, "intervalo_slot_minutos", None) or 30), 5)
    minutos_desde_abertura = int((inicio - abertura).total_seconds() // 60)
    if minutos_desde_abertura % intervalo:
        raise HTTPException(status_code=422, detail="Horario fora da grade da agenda.")


def _resolver_recurso_slot(
    db: Session, tenant_id, inicio: datetime, fim: datetime
) -> Optional[int]:
    recursos = (
        db.query(BanhoTosaRecurso)
        .filter(
            BanhoTosaRecurso.tenant_id == tenant_id,
            BanhoTosaRecurso.ativo.is_(True),
        )
        .order_by(BanhoTosaRecurso.id.asc())
        .all()
    )
    sobrepostos = db.query(BanhoTosaAgendamento).filter(
        BanhoTosaAgendamento.tenant_id == tenant_id,
        BanhoTosaAgendamento.status.notin_(list(STATUS_AGENDAMENTO_FINAIS)),
        BanhoTosaAgendamento.data_hora_inicio < fim,
        func.coalesce(
            BanhoTosaAgendamento.data_hora_fim_prevista,
            BanhoTosaAgendamento.data_hora_inicio,
        )
        > inicio,
    )
    capacidade_total = (
        sum(max(int(item.capacidade_simultanea or 1), 1) for item in recursos) or 1
    )
    if sobrepostos.count() >= capacidade_total:
        raise HTTPException(
            status_code=409,
            detail="Este horario acabou de ser ocupado. Escolha outro.",
        )

    if not recursos:
        return None
    for recurso in recursos:
        ocupacao = sobrepostos.filter(
            BanhoTosaAgendamento.recurso_id == recurso.id
        ).count()
        if ocupacao < max(int(recurso.capacidade_simultanea or 1), 1):
            return recurso.id
    raise HTTPException(
        status_code=409,
        detail="Nenhum recurso esta livre neste horario. Escolha outro.",
    )


def _intervalos_sobrepoem(
    inicio: datetime, fim: datetime, agendamento: BanhoTosaAgendamento
) -> bool:
    ag_inicio = agendamento.data_hora_inicio
    if not ag_inicio:
        return False
    ag_fim = agendamento.data_hora_fim_prevista or (ag_inicio + timedelta(minutes=60))
    ag_inicio = _datetime_compativel(ag_inicio, inicio)
    ag_fim = _datetime_compativel(ag_fim, inicio)
    return bool(ag_inicio and ag_inicio < fim and ag_fim > inicio)


def _datetime_compativel(valor: datetime, referencia: datetime) -> datetime:
    """Evita erro ao comparar datas timezone-aware do banco com slots locais do calendario."""
    valor_tem_tz = valor.tzinfo is not None and valor.utcoffset() is not None
    referencia_tem_tz = (
        referencia.tzinfo is not None and referencia.utcoffset() is not None
    )
    if valor_tem_tz == referencia_tem_tz:
        return valor
    if referencia_tem_tz:
        return valor.replace(tzinfo=referencia.tzinfo)
    return valor.replace(tzinfo=None)


def _listar_atendimentos_visiveis(db: Session, tenant_id, cliente_id: int):
    corte = datetime.now() - timedelta(days=45)
    return (
        db.query(BanhoTosaAtendimento)
        .options(
            joinedload(BanhoTosaAtendimento.pet),
            joinedload(BanhoTosaAtendimento.avaliacoes),
            joinedload(BanhoTosaAtendimento.etapas),
            joinedload(BanhoTosaAtendimento.agendamento).joinedload(
                BanhoTosaAgendamento.servicos
            ),
        )
        .filter(
            BanhoTosaAtendimento.tenant_id == tenant_id,
            BanhoTosaAtendimento.cliente_id == cliente_id,
            BanhoTosaAtendimento.status.notin_(["cancelado", "no_show"]),
            BanhoTosaAtendimento.checkin_em >= corte,
        )
        .order_by(BanhoTosaAtendimento.checkin_em.desc())
        .limit(20)
        .all()
    )


def _listar_agendamentos_visiveis(
    db: Session, tenant_id, cliente_id: int, ignorar_ids: set[int]
):
    inicio = datetime.now() - timedelta(hours=12)
    query = (
        db.query(BanhoTosaAgendamento)
        .options(
            joinedload(BanhoTosaAgendamento.pet),
            joinedload(BanhoTosaAgendamento.servicos),
        )
        .filter(
            BanhoTosaAgendamento.tenant_id == tenant_id,
            BanhoTosaAgendamento.cliente_id == cliente_id,
            BanhoTosaAgendamento.status.in_(["agendado", "confirmado"]),
            BanhoTosaAgendamento.data_hora_inicio >= inicio,
        )
    )
    if ignorar_ids:
        query = query.filter(BanhoTosaAgendamento.id.notin_(ignorar_ids))
    return query.order_by(BanhoTosaAgendamento.data_hora_inicio.asc()).limit(20).all()


def _serializar_atendimento(item: BanhoTosaAtendimento, config=None) -> dict:
    avaliacao = next(
        (av for av in item.avaliacoes or [] if av.cliente_id == item.cliente_id), None
    )
    agendamento = item.agendamento
    estado = estado_operacional_atendimento(item, config)
    ativa = etapa_ativa(item)
    return {
        "tipo": "atendimento",
        "atendimento_id": item.id,
        "agendamento_id": item.agendamento_id,
        "pet_id": item.pet_id,
        "pet_nome": item.pet.nome if item.pet else None,
        "status": item.status,
        "status_label": STATUS_LABELS.get(item.status, item.status),
        "progresso_percentual": STATUS_PROGRESSO.get(item.status, 40),
        "etapa_atual": estado.get("etapa_atual_label") or _etapa_atual(item),
        "etapa_atual_codigo": estado.get("etapa_atual_codigo"),
        "etapa_atual_label": estado.get("etapa_atual_label"),
        "proxima_etapa_codigo": estado.get("proxima_etapa_codigo"),
        "proxima_etapa_label": estado.get("proxima_etapa_label"),
        "etapa_inicio_em": _iso(getattr(ativa, "inicio_em", None)),
        "etapa_tempo_previsto_minutos": estado.get("tempo_previsto_minutos"),
        "etapa_tempo_decorrido_segundos": estado.get("tempo_decorrido_segundos"),
        "etapa_tempo_restante_segundos": estado.get("tempo_restante_segundos"),
        "etapa_atraso_segundos": estado.get("atraso_segundos"),
        "etapa_atrasada": estado.get("atrasado"),
        "data_hora_inicio": _iso(getattr(agendamento, "data_hora_inicio", None)),
        "data_hora_fim_prevista": _iso(
            getattr(agendamento, "data_hora_fim_prevista", None)
        ),
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
    return [
        {"nome": item.nome_servico_snapshot, "quantidade": _decimal(item.quantidade)}
        for item in agendamento.servicos or []
    ]


def _etapa_atual(atendimento: BanhoTosaAtendimento) -> str:
    ativa = next(
        (et for et in atendimento.etapas or [] if et.inicio_em and not et.fim_em), None
    )
    return (
        STATUS_LABELS.get(atendimento.status, atendimento.status)
        if not ativa
        else ativa.tipo.replace("_", " ").title()
    )


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
