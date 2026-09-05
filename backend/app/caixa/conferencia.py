"""Valores de caixa físico e referência preservada na abertura."""

from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func

from app.caixa_models import Caixa


def instante_fechamento_sql():
    # updated_at tem fuso e, nos caixas legados, registra a gravação do fechamento.
    # data_fechamento mistura Brasília/UTC em encerramentos operacionais antigos.
    return func.coalesce(Caixa.fechamento_em, Caixa.updated_at)


def instante_fechamento(caixa):
    return (
        getattr(caixa, "fechamento_em", None)
        or getattr(caixa, "updated_at", None)
        or caixa.data_fechamento
    )


def moeda(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def totais_dinheiro(valor_abertura, movimentacoes) -> dict:
    totais = {
        tipo: Decimal("0.00")
        for tipo in (
            "vendas",
            "suprimentos",
            "sangrias",
            "despesas",
            "transferencias",
            "devolucoes",
        )
    }
    campos = dict(
        zip(
            ("venda", "suprimento", "sangria", "despesa", "transferencia", "devolucao"),
            totais,
        )
    )
    for mov in movimentacoes:
        forma = str(mov.forma_pagamento or "").strip().casefold()
        # Movimentações manuais antigas não tinham forma; vendas sempre têm.
        if forma != "dinheiro" and (forma or mov.tipo == "venda"):
            continue
        if mov.tipo in campos:
            totais[campos[mov.tipo]] += moeda(mov.valor)
    totais["saldo_atual"] = (
        moeda(valor_abertura)
        + totais["vendas"]
        + totais["suprimentos"]
        - totais["sangrias"]
        - totais["despesas"]
        - totais["transferencias"]
        - totais["devolucoes"]
    )
    return {campo: float(valor) for campo, valor in totais.items()}


def referencia_fechamento(caixa) -> dict | None:
    if caixa is None:
        return None
    return {
        "caixa_id": caixa.id,
        "numero_caixa": caixa.numero_caixa,
        "valor_fechamento": float(moeda(caixa.valor_informado)),
        "data_fechamento": instante_fechamento(caixa).isoformat()
        if instante_fechamento(caixa)
        else None,
        "usuario_fechamento_nome": caixa.usuario_fechamento_nome or caixa.usuario_nome,
    }


def snapshot_abertura(caixa_anterior, valor_abertura) -> dict | None:
    referencia = referencia_fechamento(caixa_anterior)
    if referencia is None:
        return None
    return {
        **referencia,
        "valor_abertura": float(moeda(valor_abertura)),
        "diferenca": float(
            moeda(valor_abertura) - moeda(referencia["valor_fechamento"])
        ),
    }
