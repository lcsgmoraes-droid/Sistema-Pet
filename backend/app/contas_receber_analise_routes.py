"""Rotas de analise gerencial de contas a receber."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .financeiro_models import ContaReceber

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


def _novo_grupo(chave, nome: str) -> dict:
    return {
        "id": chave,
        "nome": nome,
        "quantidade": 0,
        "total_aberto": 0.0,
    }


def _ordenar_grupo_por_total(grupos: dict) -> list[dict]:
    return sorted(
        grupos.values(),
        key=lambda item: (-float(item["total_aberto"] or 0.0), str(item["nome"] or "")),
    )


def _label_canal(canal: str | None) -> str:
    labels = {
        "loja_fisica": "Loja fisica",
        "mercado_livre": "Mercado Livre",
        "shopee": "Shopee",
        "amazon": "Amazon",
        "ecommerce": "E-commerce",
        "transferencia_parceiro": "Transferencia parceiro",
    }
    return labels.get(canal or "", canal or "Sem canal")


@router.get("/analise-abertos")
def analisar_contas_receber_abertas(
    cliente_ids: Optional[List[int]] = Query(None),
    cliente_modo: str = Query("incluir", pattern="^(incluir|excluir)$"),
    forma_pagamento_id: Optional[int] = Query(None),
    canal: Optional[str] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Analise de saldos em aberto por vencimento, cliente, forma e canal."""
    _, tenant_id = user_and_tenant
    hoje = date.today()
    amanha = hoje + timedelta(days=1)
    limite_7_dias = hoje + timedelta(days=7)
    inicio_mes = _first_day_month(hoje)
    fim_mes = _last_day_month(hoje)
    inicio_agenda = inicio_mes
    fim_agenda = _last_day_month(_add_months(inicio_mes, 11))

    saldo_expr = ContaReceber.valor_final - ContaReceber.valor_recebido
    query = (
        db.query(ContaReceber)
        .options(
            joinedload(ContaReceber.cliente), joinedload(ContaReceber.forma_pagamento)
        )
        .filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.status.notin_(["recebido", "pago", "cancelado", "cancelada"]),
            saldo_expr > 0,
        )
    )

    cliente_ids = list(dict.fromkeys(int(item) for item in cliente_ids or [] if item))
    cliente_modo_normalizado = (cliente_modo or "incluir").strip().lower()
    if cliente_ids and cliente_modo_normalizado == "excluir":
        query = query.filter(
            or_(
                ContaReceber.cliente_id.is_(None),
                ContaReceber.cliente_id.notin_(cliente_ids),
            )
        )
    elif cliente_ids:
        query = query.filter(ContaReceber.cliente_id.in_(cliente_ids))

    if forma_pagamento_id:
        query = query.filter(ContaReceber.forma_pagamento_id == forma_pagamento_id)

    canal_normalizado = (canal or "").strip()
    if canal_normalizado and canal_normalizado != "todos":
        query = query.filter(ContaReceber.canal == canal_normalizado)

    if data_inicio:
        query = query.filter(ContaReceber.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_vencimento <= data_fim)

    contas = query.order_by(
        ContaReceber.data_vencimento.asc(), ContaReceber.id.asc()
    ).all()

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
    por_cliente = {}
    por_forma_pagamento = {}
    por_canal = {}
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
        saldo = _as_money((conta.valor_final or 0) - (conta.valor_recebido or 0))
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

        cliente_id = conta.cliente_id or "sem_cliente"
        cliente_nome = conta.cliente.nome if conta.cliente else "Sem cliente"
        grupo_cliente = por_cliente.setdefault(
            cliente_id,
            _novo_grupo(cliente_id, cliente_nome),
        )
        grupo_cliente["quantidade"] += 1
        grupo_cliente["total_aberto"] = _as_money(grupo_cliente["total_aberto"] + saldo)

        forma_id = conta.forma_pagamento_id or "sem_forma"
        forma_nome = (
            conta.forma_pagamento.nome if conta.forma_pagamento else "Sem forma"
        )
        grupo_forma = por_forma_pagamento.setdefault(
            forma_id,
            _novo_grupo(forma_id, forma_nome),
        )
        grupo_forma["quantidade"] += 1
        grupo_forma["total_aberto"] = _as_money(grupo_forma["total_aberto"] + saldo)

        canal_id = conta.canal or "sem_canal"
        grupo_canal = por_canal.setdefault(
            canal_id,
            _novo_grupo(canal_id, _label_canal(conta.canal)),
        )
        grupo_canal["quantidade"] += 1
        grupo_canal["total_aberto"] = _as_money(grupo_canal["total_aberto"] + saldo)

    return {
        "filtros": {
            "cliente_ids": cliente_ids,
            "cliente_modo": cliente_modo_normalizado,
            "forma_pagamento_id": forma_pagamento_id,
            "canal": canal_normalizado or "todos",
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
        "resumo": resumo,
        "por_cliente": _ordenar_grupo_por_total(por_cliente),
        "por_forma_pagamento": _ordenar_grupo_por_total(por_forma_pagamento),
        "por_canal": _ordenar_grupo_por_total(por_canal),
        "agenda_mensal": list(agenda_mensal.values()),
    }
