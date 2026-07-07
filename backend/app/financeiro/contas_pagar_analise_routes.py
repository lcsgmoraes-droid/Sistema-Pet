"""Rotas de analise gerencial de contas a pagar."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.contas_pagar_common import _expressao_texto_busca
from app.financeiro.contas_pagar_origem import (
    CAIXA_PDV_OBSERVACAO_MARKER,
    _identificar_origem_conta_pagar,
)
from app.financeiro_models import CategoriaFinanceira, ContaPagar
from app.models import Cliente

router = APIRouter()


def _as_money(valor) -> float:
    return float(Decimal(valor or 0).quantize(Decimal("0.01")))


def _add_months(base: date, meses: int) -> date:
    mes_base = base.month - 1 + meses
    ano = base.year + mes_base // 12
    mes = mes_base % 12 + 1
    dia = min(base.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def _first_day_month(data: date) -> date:
    return data.replace(day=1)


def _last_day_month(data: date) -> date:
    return data.replace(day=calendar.monthrange(data.year, data.month)[1])


def _month_label(data: date) -> str:
    meses = [
        "jan",
        "fev",
        "mar",
        "abr",
        "mai",
        "jun",
        "jul",
        "ago",
        "set",
        "out",
        "nov",
        "dez",
    ]
    return f"{meses[data.month - 1]}/{data.year}"


def _taxa_cartao_condition():
    return or_(
        _expressao_texto_busca(ContaPagar.descricao).like("%taxa credito%"),
        _expressao_texto_busca(ContaPagar.descricao).like("%taxa debito%"),
        _expressao_texto_busca(ContaPagar.descricao).like("%taxa cartao%"),
        _expressao_texto_busca(ContaPagar.documento).like("%taxa credito%"),
        _expressao_texto_busca(ContaPagar.documento).like("%taxa debito%"),
        _expressao_texto_busca(ContaPagar.documento).like("%taxa cartao%"),
    )


def _ordenar_grupo_por_total(grupos: dict) -> list[dict]:
    return sorted(
        grupos.values(),
        key=lambda item: (-float(item["total_aberto"] or 0.0), str(item["nome"] or "")),
    )


def _novo_grupo(chave, nome: str) -> dict:
    return {
        "id": chave,
        "nome": nome,
        "quantidade": 0,
        "total_aberto": 0.0,
    }


@router.get("/analise-abertos")
def analisar_contas_pagar_abertas(
    fornecedor_ids: Optional[List[int]] = Query(None),
    fornecedor_modo: str = Query("incluir", pattern="^(incluir|excluir)$"),
    tipo_despesa_id: Optional[int] = Query(None),
    tipo_custo: Optional[str] = Query(None),
    origem: Optional[str] = Query(None),
    ocultar_taxas_cartao: bool = Query(True),
    apenas_taxas_cartao: bool = Query(False),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Analise de saldos em aberto por vencimento, tipo e fornecedor."""
    _, tenant_id = user_and_tenant
    hoje = date.today()
    amanha = hoje + timedelta(days=1)
    limite_7_dias = hoje + timedelta(days=7)
    inicio_mes = _first_day_month(hoje)
    fim_mes = _last_day_month(hoje)
    inicio_agenda = inicio_mes
    fim_agenda = _last_day_month(_add_months(inicio_mes, 11))

    saldo_expr = ContaPagar.valor_final - ContaPagar.valor_pago
    query = (
        db.query(ContaPagar)
        .options(
            joinedload(ContaPagar.fornecedor),
            joinedload(ContaPagar.tipo_despesa),
            joinedload(ContaPagar.categoria),
        )
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.status.notin_(["pago", "cancelado"]),
            saldo_expr > 0,
        )
    )

    fornecedor_ids = list(
        dict.fromkeys(int(item) for item in fornecedor_ids or [] if item)
    )
    fornecedor_modo_normalizado = (fornecedor_modo or "incluir").strip().lower()
    if fornecedor_ids and fornecedor_modo_normalizado == "excluir":
        query = query.filter(
            or_(
                ContaPagar.fornecedor_id.is_(None),
                ContaPagar.fornecedor_id.notin_(fornecedor_ids),
            )
        )
    elif fornecedor_ids:
        query = query.filter(ContaPagar.fornecedor_id.in_(fornecedor_ids))

    if tipo_despesa_id:
        query = query.filter(ContaPagar.tipo_despesa_id == tipo_despesa_id)

    if tipo_custo in ("fixo", "variavel"):
        query = query.join(
            CategoriaFinanceira,
            ContaPagar.categoria_id == CategoriaFinanceira.id,
            isouter=True,
        ).filter(CategoriaFinanceira.tipo_custo == tipo_custo)

    origem_normalizada = (origem or "").strip().lower()
    caixa_pdv_condition = ContaPagar.observacoes.ilike(
        f"%{CAIXA_PDV_OBSERVACAO_MARKER}%"
    )
    if origem_normalizada == "caixa_pdv":
        query = query.filter(caixa_pdv_condition)
    elif origem_normalizada == "nota_entrada":
        query = query.filter(ContaPagar.nota_entrada_id.isnot(None))
    elif origem_normalizada == "manual":
        query = query.filter(
            ContaPagar.nota_entrada_id.is_(None),
            or_(ContaPagar.observacoes.is_(None), ~caixa_pdv_condition),
        )

    taxa_cartao_condition = _taxa_cartao_condition()
    if apenas_taxas_cartao:
        query = query.filter(taxa_cartao_condition)
    elif ocultar_taxas_cartao:
        query = query.filter(~taxa_cartao_condition)

    if data_inicio:
        query = query.filter(ContaPagar.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(ContaPagar.data_vencimento <= data_fim)

    contas = query.order_by(ContaPagar.data_vencimento.asc(), ContaPagar.id.asc()).all()

    resumo = {
        "quantidade": 0,
        "total_aberto": 0.0,
        "vencido": {"quantidade": 0, "total_aberto": 0.0},
        "hoje": {"quantidade": 0, "total_aberto": 0.0},
        "amanha": {"quantidade": 0, "total_aberto": 0.0},
        "proximos_7_dias": {"quantidade": 0, "total_aberto": 0.0},
        "mes_atual": {"quantidade": 0, "total_aberto": 0.0},
        "proximos_12_meses": {"quantidade": 0, "total_aberto": 0.0},
    }
    por_fornecedor = {}
    por_tipo_despesa = {}
    por_origem = {}
    por_tipo_custo = {}
    agenda_mensal = {}
    for indice in range(12):
        mes_inicio = _add_months(inicio_agenda, indice)
        chave = f"{mes_inicio.year:04d}-{mes_inicio.month:02d}"
        agenda_mensal[chave] = {
            "mes": chave,
            "label": _month_label(mes_inicio),
            "quantidade": 0,
            "total_aberto": 0.0,
        }

    for conta in contas:
        saldo = _as_money((conta.valor_final or 0) - (conta.valor_pago or 0))
        vencimento = conta.data_vencimento
        resumo["quantidade"] += 1
        resumo["total_aberto"] = _as_money(resumo["total_aberto"] + saldo)

        if vencimento < hoje:
            bucket = resumo["vencido"]
            bucket["quantidade"] += 1
            bucket["total_aberto"] = _as_money(bucket["total_aberto"] + saldo)
        if vencimento == hoje:
            bucket = resumo["hoje"]
            bucket["quantidade"] += 1
            bucket["total_aberto"] = _as_money(bucket["total_aberto"] + saldo)
        if vencimento == amanha:
            bucket = resumo["amanha"]
            bucket["quantidade"] += 1
            bucket["total_aberto"] = _as_money(bucket["total_aberto"] + saldo)
        if hoje <= vencimento <= limite_7_dias:
            bucket = resumo["proximos_7_dias"]
            bucket["quantidade"] += 1
            bucket["total_aberto"] = _as_money(bucket["total_aberto"] + saldo)
        if inicio_mes <= vencimento <= fim_mes:
            bucket = resumo["mes_atual"]
            bucket["quantidade"] += 1
            bucket["total_aberto"] = _as_money(bucket["total_aberto"] + saldo)
        if hoje <= vencimento <= fim_agenda:
            bucket = resumo["proximos_12_meses"]
            bucket["quantidade"] += 1
            bucket["total_aberto"] = _as_money(bucket["total_aberto"] + saldo)

        if inicio_agenda <= vencimento <= fim_agenda:
            chave_mes = f"{vencimento.year:04d}-{vencimento.month:02d}"
            if chave_mes in agenda_mensal:
                bucket = agenda_mensal[chave_mes]
                bucket["quantidade"] += 1
                bucket["total_aberto"] = _as_money(bucket["total_aberto"] + saldo)

        fornecedor_id = conta.fornecedor_id or "sem_fornecedor"
        fornecedor_nome = (
            conta.fornecedor.nome if isinstance(conta.fornecedor, Cliente) else None
        ) or "Sem fornecedor"
        grupo_fornecedor = por_fornecedor.setdefault(
            fornecedor_id,
            _novo_grupo(fornecedor_id, fornecedor_nome),
        )
        grupo_fornecedor["quantidade"] += 1
        grupo_fornecedor["total_aberto"] = _as_money(
            grupo_fornecedor["total_aberto"] + saldo
        )

        tipo_id = conta.tipo_despesa_id or "sem_tipo"
        tipo_nome = conta.tipo_despesa.nome if conta.tipo_despesa else "Sem tipo"
        grupo_tipo = por_tipo_despesa.setdefault(
            tipo_id, _novo_grupo(tipo_id, tipo_nome)
        )
        grupo_tipo["quantidade"] += 1
        grupo_tipo["total_aberto"] = _as_money(grupo_tipo["total_aberto"] + saldo)

        origem_info = _identificar_origem_conta_pagar(conta)
        origem_id = origem_info["origem_lancamento"]
        grupo_origem = por_origem.setdefault(
            origem_id,
            _novo_grupo(origem_id, origem_info["origem_lancamento_label"]),
        )
        grupo_origem["quantidade"] += 1
        grupo_origem["total_aberto"] = _as_money(grupo_origem["total_aberto"] + saldo)

        tipo_custo_id = (
            conta.categoria.tipo_custo
            if conta.categoria and conta.categoria.tipo_custo in ("fixo", "variavel")
            else "sem_tipo_custo"
        )
        tipo_custo_nome = {
            "fixo": "Fixo",
            "variavel": "Variavel",
            "sem_tipo_custo": "Sem tipo de custo",
        }[tipo_custo_id]
        grupo_custo = por_tipo_custo.setdefault(
            tipo_custo_id,
            _novo_grupo(tipo_custo_id, tipo_custo_nome),
        )
        grupo_custo["quantidade"] += 1
        grupo_custo["total_aberto"] = _as_money(grupo_custo["total_aberto"] + saldo)

    return {
        "filtros": {
            "fornecedor_ids": fornecedor_ids,
            "fornecedor_modo": fornecedor_modo_normalizado,
            "tipo_despesa_id": tipo_despesa_id,
            "tipo_custo": tipo_custo or "todos",
            "origem": origem or "todos",
            "ocultar_taxas_cartao": ocultar_taxas_cartao,
            "apenas_taxas_cartao": apenas_taxas_cartao,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
        "resumo": resumo,
        "por_fornecedor": _ordenar_grupo_por_total(por_fornecedor),
        "por_tipo_despesa": _ordenar_grupo_por_total(por_tipo_despesa),
        "por_origem": _ordenar_grupo_por_total(por_origem),
        "por_tipo_custo": _ordenar_grupo_por_total(por_tipo_custo),
        "agenda_mensal": list(agenda_mensal.values()),
    }
