from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.utils import STATUS_ATENDIMENTO_FINAIS
from app.banho_tosa_avaliacoes_metrics import calcular_nps_periodo
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaRecurso,
    BanhoTosaServico,
)
from app.banho_tosa_schemas import BanhoTosaDashboardResponse
from app.db import get_session
from app.veterinario_core import _get_tenant
from app.vendas_models import Venda


router = APIRouter()


@router.get("/dashboard", response_model=BanhoTosaDashboardResponse)
def obter_dashboard(
    data_referencia: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    data_ref = data_referencia or date.today()
    inicio = datetime.combine(data_ref, time.min)
    fim = datetime.combine(data_ref, time.max)

    agendamentos_abertos = db.query(func.count(BanhoTosaAgendamento.id)).filter(
        BanhoTosaAgendamento.tenant_id == tenant_id,
        BanhoTosaAgendamento.data_hora_inicio >= inicio,
        BanhoTosaAgendamento.data_hora_inicio <= fim,
        BanhoTosaAgendamento.status.notin_(["entregue", "cancelado", "no_show"]),
    ).scalar() or 0

    atendimentos_em_execucao = db.query(func.count(BanhoTosaAtendimento.id)).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.status.notin_(list(STATUS_ATENDIMENTO_FINAIS | {"pronto"})),
    ).scalar() or 0

    atendimentos_prontos = db.query(func.count(BanhoTosaAtendimento.id)).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.status == "pronto",
    ).scalar() or 0

    atendimentos_prontos_sem_venda = db.query(func.count(BanhoTosaAtendimento.id)).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.status == "pronto",
        BanhoTosaAtendimento.venda_id.is_(None),
        BanhoTosaAtendimento.pacote_credito_id.is_(None),
    ).scalar() or 0

    cobrancas_pendentes = db.query(func.count(BanhoTosaAtendimento.id)).join(
        Venda,
        BanhoTosaAtendimento.venda_id == Venda.id,
    ).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.status.in_(["pronto", "entregue"]),
        Venda.status.in_(["aberta", "baixa_parcial"]),
    ).scalar() or 0

    atendimentos_entregues = db.query(func.count(BanhoTosaAtendimento.id)).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.entregue_em >= inicio,
        BanhoTosaAtendimento.entregue_em <= fim,
    ).scalar() or 0

    servicos_ativos = db.query(func.count(BanhoTosaServico.id)).filter(
        BanhoTosaServico.tenant_id == tenant_id,
        BanhoTosaServico.ativo == True,
    ).scalar() or 0

    recursos_ativos = db.query(func.count(BanhoTosaRecurso.id)).filter(
        BanhoTosaRecurso.tenant_id == tenant_id,
        BanhoTosaRecurso.ativo == True,
    ).scalar() or 0
    nps = calcular_nps_periodo(db, tenant_id, inicio, fim)

    return {
        "data_referencia": inicio,
        "agendamentos_abertos": int(agendamentos_abertos),
        "atendimentos_em_execucao": int(atendimentos_em_execucao),
        "atendimentos_prontos": int(atendimentos_prontos),
        "atendimentos_prontos_sem_venda": int(atendimentos_prontos_sem_venda),
        "cobrancas_pendentes": int(cobrancas_pendentes),
        "atendimentos_entregues": int(atendimentos_entregues),
        "servicos_ativos": int(servicos_ativos),
        "recursos_ativos": int(recursos_ativos),
        "avaliacoes_hoje": nps["avaliacoes"],
        "nps_hoje": nps["nps"],
    }
