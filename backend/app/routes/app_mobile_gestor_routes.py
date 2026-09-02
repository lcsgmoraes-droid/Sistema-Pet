"""Resumo executivo, somente leitura, para o perfil Gestor do app mobile."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.dre_canais.base import CANAIS_CONFIG
from app.dre_canais.routes import gerar_dre_por_canais
from app.financeiro.fluxo_caixa_routes import get_fluxo_caixa
from app.financeiro_models import ContaPagar, ContaReceber
from app.models import User
from app.relatorio_vendas_common import (
    _total_recebido_venda,
    _valores_operacionais_venda,
)
from app.routes.ecommerce_auth import (
    _activate_user_tenant_context,
    _get_current_ecommerce_user,
)
from app.services.app_access_profile_service import resolve_user_app_profiles
from app.utils.serialization import safe_decimal_to_float_zero
from app.utils.timezone import now_brasilia
from app.vendas_models import Venda

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gestor", tags=["App Mobile - Gestor"])

OPEN_ACCOUNT_STATUSES = (
    "pendente",
    "parcial",
    "vencido",
    "vencida",
    "atrasado",
)


class GestorVendasResumo(BaseModel):
    faturamento_bruto: float = 0
    faturamento_liquido: float = 0
    recebido: float = 0
    descontos: float = 0
    quantidade_vendas: int = 0
    unidades_vendidas: float = 0
    produtos_distintos: int = 0
    ticket_medio: float = 0


class GestorContaResumo(BaseModel):
    total_aberto: float = 0
    quantidade_abertas: int = 0
    vencido: float = 0
    quantidade_vencidas: int = 0
    vence_hoje: float = 0
    quantidade_vence_hoje: int = 0
    no_periodo: float = 0
    quantidade_no_periodo: int = 0


class GestorFluxoDiaResumo(BaseModel):
    data: date
    disponivel: bool = True
    saldo_inicial: float = 0
    saldo_do_dia: float = 0
    saldo_previsto_do_dia: float = 0
    entradas_realizadas: float = 0
    saidas_realizadas: float = 0
    saldo_realizado: float = 0
    entradas_previstas: float = 0
    saidas_previstas: float = 0
    saldo_projetado: float = 0


class GestorDREResumo(BaseModel):
    disponivel: bool = True
    periodo: str
    criterio: str
    receita_bruta: float = 0
    descontos: float = 0
    impostos: float = 0
    deducoes_total: float = 0
    receita_liquida: float = 0
    cmv: float = 0
    despesas_variaveis: float = 0
    despesas_operacionais: float = 0
    despesas_fixas_operacionais: float = 0
    lucro_bruto: float = 0
    resultado_operacional: float = 0
    lucro_liquido: float = 0
    margem_bruta: float = 0
    margem_liquida: float = 0


class GestorResumoResponse(BaseModel):
    data_inicio: date
    data_fim: date
    atualizado_em: datetime
    vendas: GestorVendasResumo
    fluxo_hoje: GestorFluxoDiaResumo
    contas_pagar: GestorContaResumo
    contas_receber: GestorContaResumo
    dre: GestorDREResumo
    avisos: list[str] = Field(default_factory=list)


def _get_gestor_tenant_or_403(db: Session, user: User) -> str:
    tenant_id = _activate_user_tenant_context(user)
    active_profile = (
        str(getattr(user, "_active_app_profile", None) or "cliente").strip().casefold()
    )
    if active_profile != "gestor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selecione o acesso Gestor para consultar estes dados.",
        )

    available_profiles = resolve_user_app_profiles(db, user)
    if "gestor" not in {profile["type"] for profile in available_profiles}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso Gestor nao liberado para esta conta.",
        )
    return tenant_id


def _date_bounds(data_inicio: date, data_fim: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(data_inicio, time.min),
        datetime.combine(data_fim + timedelta(days=1), time.min),
    )


def _resumir_vendas(vendas: list[Venda]) -> GestorVendasResumo:
    bruto = 0.0
    liquido = 0.0
    recebido = 0.0
    descontos = 0.0
    unidades = 0.0
    produtos_ids: set[int] = set()

    for venda in vendas:
        valores = _valores_operacionais_venda(venda)
        bruto += valores["valor_bruto"]
        liquido += valores["valor_liquido"]
        recebido += _total_recebido_venda(venda)
        descontos += valores["desconto"]
        for item in list(getattr(venda, "itens", []) or []):
            unidades += safe_decimal_to_float_zero(getattr(item, "quantidade", 0))
            produto_id = getattr(item, "produto_id", None)
            if produto_id is not None:
                produtos_ids.add(int(produto_id))

    quantidade = len(vendas)
    return GestorVendasResumo(
        faturamento_bruto=round(bruto, 2),
        faturamento_liquido=round(liquido, 2),
        recebido=round(recebido, 2),
        descontos=round(descontos, 2),
        quantidade_vendas=quantidade,
        unidades_vendidas=round(unidades, 3),
        produtos_distintos=len(produtos_ids),
        ticket_medio=round(liquido / quantidade, 2) if quantidade else 0,
    )


def _resumir_contas(
    db: Session,
    model: type[ContaPagar] | type[ContaReceber],
    *,
    tenant_id: str,
    hoje: date,
    data_inicio: date,
    data_fim: date,
    paid_field: Any,
) -> GestorContaResumo:
    valor_base = func.coalesce(model.valor_final, model.valor_original, 0)
    saldo = valor_base - func.coalesce(paid_field, 0)
    vencimento = model.data_vencimento

    row = (
        db.query(
            func.count(model.id).label("quantidade_abertas"),
            func.coalesce(func.sum(saldo), 0).label("total_aberto"),
            func.coalesce(func.sum(case((vencimento < hoje, saldo), else_=0)), 0).label(
                "vencido"
            ),
            func.coalesce(func.sum(case((vencimento < hoje, 1), else_=0)), 0).label(
                "quantidade_vencidas"
            ),
            func.coalesce(
                func.sum(case((vencimento == hoje, saldo), else_=0)), 0
            ).label("vence_hoje"),
            func.coalesce(func.sum(case((vencimento == hoje, 1), else_=0)), 0).label(
                "quantidade_vence_hoje"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(vencimento >= data_inicio, vencimento <= data_fim),
                            saldo,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("no_periodo"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(vencimento >= data_inicio, vencimento <= data_fim), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("quantidade_no_periodo"),
        )
        .filter(
            model.tenant_id == tenant_id,
            model.status.in_(OPEN_ACCOUNT_STATUSES),
        )
        .one()
    )

    return GestorContaResumo(
        total_aberto=round(safe_decimal_to_float_zero(row.total_aberto), 2),
        quantidade_abertas=int(row.quantidade_abertas or 0),
        vencido=round(safe_decimal_to_float_zero(row.vencido), 2),
        quantidade_vencidas=int(row.quantidade_vencidas or 0),
        vence_hoje=round(safe_decimal_to_float_zero(row.vence_hoje), 2),
        quantidade_vence_hoje=int(row.quantidade_vence_hoje or 0),
        no_periodo=round(safe_decimal_to_float_zero(row.no_periodo), 2),
        quantidade_no_periodo=int(row.quantidade_no_periodo or 0),
    )


def _resumo_fluxo_hoje(
    db: Session, current_user: User, tenant_id: str, hoje: date
) -> GestorFluxoDiaResumo:
    fluxo = get_fluxo_caixa(
        data_inicio=hoje.isoformat(),
        data_fim=hoje.isoformat(),
        conta_bancaria_id=None,
        agrupamento="dia",
        numero_venda=None,
        db=db,
        current_user_and_tenant=(current_user, tenant_id),
        _module_access=None,
    )
    realizado = fluxo.total_realizado_entradas - fluxo.total_realizado_saidas
    projetado = realizado + fluxo.total_previsto_entradas - fluxo.total_previsto_saidas
    return GestorFluxoDiaResumo(
        data=hoje,
        saldo_inicial=round(fluxo.saldo_inicial, 2),
        saldo_do_dia=round(fluxo.saldo_final, 2),
        saldo_previsto_do_dia=round(fluxo.saldo_previsto_final, 2),
        entradas_realizadas=round(fluxo.total_realizado_entradas, 2),
        saidas_realizadas=round(fluxo.total_realizado_saidas, 2),
        saldo_realizado=round(realizado, 2),
        entradas_previstas=round(fluxo.total_previsto_entradas, 2),
        saidas_previstas=round(fluxo.total_previsto_saidas, 2),
        saldo_projetado=round(projetado, 2),
    )


def _dre_periodo(data_inicio: date, data_fim: date) -> tuple[int, int, int, date, str]:
    if data_inicio.year == data_fim.year and data_inicio.day == 1:
        mes_inicial = data_inicio.month
        criterio = "periodo_selecionado"
    else:
        mes_inicial = data_fim.month
        criterio = "competencia_do_mes"
    return data_fim.year, data_fim.month, mes_inicial, data_fim, criterio


def _resumo_dre(
    db: Session,
    current_user: User,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
) -> GestorDREResumo:
    ano, mes, mes_inicial, dre_data_final, criterio = _dre_periodo(
        data_inicio, data_fim
    )
    dre = gerar_dre_por_canais(
        ano=ano,
        mes=mes,
        mes_inicial=mes_inicial,
        data_final=dre_data_final,
        canais=",".join(CANAIS_CONFIG.keys()),
        db=db,
        user_and_tenant=(current_user, tenant_id),
    )
    totais = dre.totais
    despesas_variaveis = float(totais.get("despesas_variaveis", 0))
    despesas_operacionais = float(totais.get("despesas_operacionais", 0))
    return GestorDREResumo(
        periodo=dre.periodo,
        criterio=criterio,
        receita_bruta=round(float(totais.get("receita_bruta", 0)), 2),
        descontos=round(float(totais.get("descontos", 0)), 2),
        impostos=round(float(totais.get("impostos", 0)), 2),
        deducoes_total=round(float(totais.get("deducoes_total", 0)), 2),
        receita_liquida=round(float(totais.get("receita_liquida", 0)), 2),
        cmv=round(float(totais.get("cmv", 0)), 2),
        despesas_variaveis=round(despesas_variaveis, 2),
        despesas_operacionais=round(despesas_operacionais, 2),
        despesas_fixas_operacionais=round(
            max(despesas_operacionais - despesas_variaveis, 0), 2
        ),
        lucro_bruto=round(float(totais.get("lucro_bruto", 0)), 2),
        resultado_operacional=round(float(totais.get("resultado_operacional", 0)), 2),
        lucro_liquido=round(float(totais.get("lucro_liquido", 0)), 2),
        margem_bruta=round(float(totais.get("margem_bruta", 0)), 2),
        margem_liquida=round(float(totais.get("margem_liquida", 0)), 2),
    )


@router.get("/resumo", response_model=GestorResumoResponse)
def obter_resumo_gestor_mobile(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    if data_fim < data_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data final deve ser igual ou posterior a data inicial.",
        )
    if (data_fim - data_inicio).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O periodo maximo para consulta e de 367 dias.",
        )

    tenant_id = _get_gestor_tenant_or_403(db, current_user)
    inicio, fim_exclusivo = _date_bounds(data_inicio, data_fim)
    vendas = (
        db.query(Venda)
        .options(selectinload(Venda.pagamentos), selectinload(Venda.itens))
        .filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio,
                Venda.data_venda < fim_exclusivo,
                or_(Venda.status.is_(None), Venda.status != "cancelada"),
            )
        )
        .all()
    )

    hoje = now_brasilia().date()
    avisos: list[str] = []
    try:
        fluxo_hoje = _resumo_fluxo_hoje(db, current_user, tenant_id, hoje)
    except Exception:
        logger.exception("Erro ao calcular fluxo do dia no resumo Gestor")
        avisos.append("O fluxo de caixa do dia nao pode ser atualizado agora.")
        fluxo_hoje = GestorFluxoDiaResumo(data=hoje, disponivel=False)

    try:
        dre = _resumo_dre(db, current_user, tenant_id, data_inicio, data_fim)
    except Exception:
        logger.exception("Erro ao calcular DRE no resumo Gestor")
        avisos.append("A DRE nao pode ser atualizada agora.")
        dre = GestorDREResumo(
            disponivel=False,
            periodo=f"{data_fim.month:02d}/{data_fim.year}",
            criterio="competencia_do_mes",
        )

    return GestorResumoResponse(
        data_inicio=data_inicio,
        data_fim=data_fim,
        atualizado_em=now_brasilia(),
        vendas=_resumir_vendas(vendas),
        fluxo_hoje=fluxo_hoje,
        contas_pagar=_resumir_contas(
            db,
            ContaPagar,
            tenant_id=tenant_id,
            hoje=hoje,
            data_inicio=data_inicio,
            data_fim=data_fim,
            paid_field=ContaPagar.valor_pago,
        ),
        contas_receber=_resumir_contas(
            db,
            ContaReceber,
            tenant_id=tenant_id,
            hoje=hoje,
            data_inicio=data_inicio,
            data_fim=data_fim,
            paid_field=ContaReceber.valor_recebido,
        ),
        dre=dre,
        avisos=avisos,
    )
