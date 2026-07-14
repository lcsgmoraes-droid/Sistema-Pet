"""Rotas de analise gerencial de contas a pagar."""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from decimal import Decimal
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
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


def _aplicar_filtros_analise(
    query,
    *,
    fornecedor_ids: Optional[List[int]],
    fornecedor_modo: str,
    tipo_despesa_id: Optional[int],
    tipo_custo: Optional[str],
    origem: Optional[str],
    ocultar_taxas_cartao: bool,
    apenas_taxas_cartao: bool,
    data_inicio: Optional[date],
    data_fim: Optional[date],
):
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
        query = query.filter(
            ContaPagar.categoria.has(CategoriaFinanceira.tipo_custo == tipo_custo)
        )

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

    return query, fornecedor_ids, fornecedor_modo_normalizado


def _aplicar_grupo_detalhe(query, grupo: str, grupo_id: Optional[str], hoje: date):
    grupo_id = (grupo_id or "").strip()
    caixa_pdv_condition = ContaPagar.observacoes.ilike(
        f"%{CAIXA_PDV_OBSERVACAO_MARKER}%"
    )

    if grupo == "todos":
        return query
    if grupo == "fornecedor":
        if grupo_id == "sem_fornecedor":
            return query.filter(ContaPagar.fornecedor_id.is_(None))
        if grupo_id.isdigit():
            return query.filter(ContaPagar.fornecedor_id == int(grupo_id))
    elif grupo == "tipo_despesa":
        if grupo_id == "sem_tipo":
            return query.filter(ContaPagar.tipo_despesa_id.is_(None))
        if grupo_id.isdigit():
            return query.filter(ContaPagar.tipo_despesa_id == int(grupo_id))
    elif grupo == "origem":
        if grupo_id == "caixa_pdv":
            return query.filter(caixa_pdv_condition)
        if grupo_id == "nota_entrada":
            return query.filter(ContaPagar.nota_entrada_id.isnot(None))
        if grupo_id == "manual":
            return query.filter(
                ContaPagar.nota_entrada_id.is_(None),
                or_(ContaPagar.observacoes.is_(None), ~caixa_pdv_condition),
            )
    elif grupo == "tipo_custo":
        if grupo_id == "sem_tipo_custo":
            return query.filter(
                or_(
                    ContaPagar.categoria_id.is_(None),
                    ~ContaPagar.categoria.has(
                        CategoriaFinanceira.tipo_custo.in_(["fixo", "variavel"])
                    ),
                )
            )
        if grupo_id in ("fixo", "variavel"):
            return query.filter(
                ContaPagar.categoria.has(CategoriaFinanceira.tipo_custo == grupo_id)
            )
    elif grupo == "periodo":
        if grupo_id == "vencido":
            return query.filter(ContaPagar.data_vencimento < hoje)
        if grupo_id == "hoje":
            return query.filter(ContaPagar.data_vencimento == hoje)
        if grupo_id == "amanha":
            return query.filter(ContaPagar.data_vencimento == hoje + timedelta(days=1))
        if grupo_id == "proximos_7_dias":
            return query.filter(
                ContaPagar.data_vencimento >= hoje,
                ContaPagar.data_vencimento <= hoje + timedelta(days=7),
            )
        if grupo_id == "mes_atual":
            return query.filter(
                ContaPagar.data_vencimento >= _first_day_month(hoje),
                ContaPagar.data_vencimento <= _last_day_month(hoje),
            )
        if grupo_id == "proximos_12_meses":
            fim = _last_day_month(_add_months(_first_day_month(hoje), 11))
            return query.filter(
                ContaPagar.data_vencimento >= hoje,
                ContaPagar.data_vencimento <= fim,
            )
    elif grupo == "mes" and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", grupo_id):
        inicio = date.fromisoformat(f"{grupo_id}-01")
        return query.filter(
            ContaPagar.data_vencimento >= inicio,
            ContaPagar.data_vencimento <= _last_day_month(inicio),
        )

    raise HTTPException(status_code=422, detail="Grupo de detalhamento invalido")


def _referencia_origem(conta: ContaPagar, origem_info: dict) -> str:
    if origem_info["origem_lancamento"] == "caixa_pdv":
        return origem_info.get("caixa_referencia") or "Caixa/PDV"
    if origem_info["origem_lancamento"] == "nota_entrada":
        if conta.nfe_numero:
            return f"NF {conta.nfe_numero}"
        return f"Nota de entrada #{conta.nota_entrada_id}"
    return conta.documento or "Lancamento manual"


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
    query = db.query(ContaPagar).filter(
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.status.notin_(["pago", "cancelado"]),
        saldo_expr > 0,
    )
    query, fornecedor_ids, fornecedor_modo_normalizado = _aplicar_filtros_analise(
        query,
        fornecedor_ids=fornecedor_ids,
        fornecedor_modo=fornecedor_modo,
        tipo_despesa_id=tipo_despesa_id,
        tipo_custo=tipo_custo,
        origem=origem,
        ocultar_taxas_cartao=ocultar_taxas_cartao,
        apenas_taxas_cartao=apenas_taxas_cartao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    contas = (
        query.options(
            joinedload(ContaPagar.fornecedor),
            joinedload(ContaPagar.tipo_despesa),
            joinedload(ContaPagar.categoria),
        )
        .order_by(ContaPagar.data_vencimento.asc(), ContaPagar.id.asc())
        .all()
    )

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


@router.get("/analise-abertos/detalhes")
def detalhar_contas_pagar_abertas(
    grupo: str = Query(
        "todos",
        pattern="^(todos|periodo|mes|fornecedor|tipo_despesa|origem|tipo_custo)$",
    ),
    grupo_id: Optional[str] = Query(None),
    fornecedor_ids: Optional[List[int]] = Query(None),
    fornecedor_modo: str = Query("incluir", pattern="^(incluir|excluir)$"),
    tipo_despesa_id: Optional[int] = Query(None),
    tipo_custo: Optional[str] = Query(None),
    origem: Optional[str] = Query(None),
    ocultar_taxas_cartao: bool = Query(True),
    apenas_taxas_cartao: bool = Query(False),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista os lancamentos que formam uma linha da analise de contas a pagar."""
    _, tenant_id = user_and_tenant
    saldo_expr = ContaPagar.valor_final - ContaPagar.valor_pago
    query = db.query(ContaPagar).filter(
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.status.notin_(["pago", "cancelado"]),
        saldo_expr > 0,
    )
    query, _, _ = _aplicar_filtros_analise(
        query,
        fornecedor_ids=fornecedor_ids,
        fornecedor_modo=fornecedor_modo,
        tipo_despesa_id=tipo_despesa_id,
        tipo_custo=tipo_custo,
        origem=origem,
        ocultar_taxas_cartao=ocultar_taxas_cartao,
        apenas_taxas_cartao=apenas_taxas_cartao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    query = _aplicar_grupo_detalhe(query, grupo, grupo_id, date.today())

    total_itens = query.order_by(None).count()
    total = query.order_by(None).with_entities(func.sum(saldo_expr)).scalar()
    pages = max(1, ceil(total_itens / page_size))
    contas = (
        query.options(
            joinedload(ContaPagar.fornecedor),
            joinedload(ContaPagar.tipo_despesa),
            joinedload(ContaPagar.categoria),
        )
        .order_by(ContaPagar.data_vencimento.asc(), ContaPagar.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for conta in contas:
        origem_info = _identificar_origem_conta_pagar(conta)
        saldo_aberto = _as_money((conta.valor_final or 0) - (conta.valor_pago or 0))
        fornecedor_nome = (
            conta.fornecedor.nome if isinstance(conta.fornecedor, Cliente) else None
        ) or "Sem fornecedor"
        items.append(
            {
                "id": conta.id,
                "descricao": conta.descricao,
                "fornecedor_nome": fornecedor_nome,
                "documento": conta.documento or conta.nfe_numero,
                "data_emissao": conta.data_emissao,
                "data_vencimento": conta.data_vencimento,
                "valor_final": _as_money(conta.valor_final),
                "valor_pago": _as_money(conta.valor_pago),
                "saldo_aberto": saldo_aberto,
                "status": conta.status or "pendente",
                "tipo_despesa_nome": (
                    conta.tipo_despesa.nome if conta.tipo_despesa else "Sem tipo"
                ),
                "tipo_custo": (
                    conta.categoria.tipo_custo
                    if conta.categoria
                    and conta.categoria.tipo_custo in ("fixo", "variavel")
                    else None
                ),
                "origem_referencia": _referencia_origem(conta, origem_info),
                **origem_info,
            }
        )

    return {
        "grupo": grupo,
        "grupo_id": grupo_id,
        "total": _as_money(total),
        "total_itens": total_itens,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "items": items,
    }
