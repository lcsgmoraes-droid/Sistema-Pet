"""Relatório por eventos de recebimento; a data da venda é apenas referência."""

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import unicodedata

from app.financeiro.recebimentos_vendas_queries import carregar_fontes_recebimentos


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _sem_dinheiro_novo(*valores):
    texto = " ".join(str(v or "") for v in valores).lower().replace("_", " ")
    texto = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return "cashback" in texto or ("credito" in texto and "cliente" in texto)


def _evento(origem, ident, data, valor, venda, cliente, forma, tipo="recebimento"):
    data_venda = venda.data_venda
    if isinstance(data_venda, datetime):
        data_venda = data_venda.date()
    return {
        "id": f"{origem}-{ident}",
        "origem": origem,
        "tipo": tipo,
        "data_recebimento": data.isoformat(),
        "data_venda": data_venda.isoformat(),
        "venda_id": venda.id,
        "numero_venda": venda.numero_venda,
        "cliente_nome": cliente or "Cliente avulso",
        "forma_pagamento": forma or "Não informada",
        "valor": float(_money(valor)),
    }


def montar_relatorio_recebimentos(db, tenant_id, inicio, fim, canal=None):
    baixas, contas, conciliacoes, devolucoes = carregar_fontes_recebimentos(
        db, tenant_id, inicio, fim, canal
    )
    eventos = []
    for baixa, conta, venda, cliente, forma, tipo in baixas:
        if _sem_dinheiro_novo(forma, tipo, conta.descricao):
            continue
        eventos.append(
            _evento(
                "baixa",
                baixa.id,
                baixa.data_recebimento,
                baixa.valor_recebido,
                venda,
                cliente,
                forma,
            )
        )
    for conta, venda, cliente, forma, tipo in contas:
        if _sem_dinheiro_novo(forma, tipo, conta.descricao):
            continue
        eventos.append(
            _evento(
                "conta",
                conta.id,
                conta.data_liquidacao or conta.data_recebimento,
                conta.valor_recebido,
                venda,
                cliente,
                forma,
            )
        )
    for conciliacao, venda, cliente in conciliacoes:
        eventos.append(
            _evento(
                "conciliacao",
                conciliacao.id,
                conciliacao.data_recebimento,
                conciliacao.valor,
                venda,
                cliente,
                conciliacao.adquirente or "Cartão conciliado",
            )
        )
    for devolucao, venda, cliente in devolucoes:
        eventos.append(
            _evento(
                "devolucao",
                devolucao.id,
                devolucao.data_lancamento,
                -_money(devolucao.valor),
                venda,
                cliente,
                "Dinheiro",
                "devolucao",
            )
        )

    por_dia = defaultdict(lambda: Decimal("0.00"))
    entradas_por_dia = defaultdict(lambda: Decimal("0.00"))
    devolucoes_por_dia = defaultdict(lambda: Decimal("0.00"))
    entradas = Decimal("0.00")
    saidas = Decimal("0.00")
    for evento in eventos:
        valor = _money(evento["valor"])
        por_dia[evento["data_recebimento"]] += valor
        if valor >= 0:
            entradas += valor
            entradas_por_dia[evento["data_recebimento"]] += valor
        else:
            saidas -= valor
            devolucoes_por_dia[evento["data_recebimento"]] -= valor
    dias = (fim - inicio).days + 1
    return {
        "visao_comercial": "recebimento",
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "resumo": {
            "recebimentos": float(entradas),
            "devolucoes": float(saidas),
            "total": float(entradas - saidas),
        },
        "por_dia": [
            {
                "data": (inicio + timedelta(days=i)).isoformat(),
                "entradas": float(
                    entradas_por_dia[(inicio + timedelta(days=i)).isoformat()]
                ),
                "devolucoes": float(
                    devolucoes_por_dia[(inicio + timedelta(days=i)).isoformat()]
                ),
                "valor": float(por_dia[(inicio + timedelta(days=i)).isoformat()]),
            }
            for i in range(dias)
        ],
        "movimentos": sorted(
            eventos, key=lambda e: (e["data_recebimento"], e["id"]), reverse=True
        ),
    }
