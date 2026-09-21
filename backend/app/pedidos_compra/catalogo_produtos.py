"""Calculos do catalogo de produtos usado na montagem de pedidos."""

from __future__ import annotations

from math import ceil
from typing import Any

from app.pedidos_compra.sugestao import _float_seguro_sugestao


DIAS_RISCO_ESTOQUE = 7
JANELAS_VENDAS_CATALOGO = (7, 15, 30, 60, 90)


def calcular_situacao_estoque_catalogo(
    *,
    estoque_atual: Any,
    estoque_minimo: Any,
    vendas_30d: Any,
    dias_risco: int = DIAS_RISCO_ESTOQUE,
) -> dict[str, Any]:
    """Classifica estoque baixo e risco considerando o giro recente."""
    atual = _float_seguro_sugestao(estoque_atual)
    minimo = max(0.0, _float_seguro_sugestao(estoque_minimo))
    vendas_30 = max(0.0, _float_seguro_sugestao(vendas_30d))
    media_diaria = vendas_30 / 30
    limite_risco = minimo + (media_diaria * max(0, dias_risco))

    estoque_baixo = atual <= minimo
    estoque_em_risco = not estoque_baixo and media_diaria > 0 and atual <= limite_risco
    if estoque_baixo:
        status = "baixo"
    elif estoque_em_risco:
        status = "risco"
    else:
        status = "normal"

    dias_ate_minimo = None
    if media_diaria > 0:
        dias_ate_minimo = max(0.0, (atual - minimo) / media_diaria)

    return {
        "status_estoque": status,
        "estoque_baixo": estoque_baixo,
        "estoque_em_risco": estoque_em_risco,
        "media_diaria_30": round(media_diaria, 3),
        "limite_risco": round(limite_risco, 2),
        "dias_ate_minimo": round(dias_ate_minimo, 1)
        if dias_ate_minimo is not None
        else None,
        "quantidade_sugerida": max(1, ceil(limite_risco - atual)),
    }


def montar_metricas_giro_catalogo(vendas_stats: dict | None) -> dict[str, Any]:
    stats = vendas_stats or {}
    janelas_origem = stats.get("janelas") or {}
    janelas = {
        str(dias): round(
            _float_seguro_sugestao(janelas_origem.get(str(dias))),
            3,
        )
        for dias in JANELAS_VENDAS_CATALOGO
    }
    return {
        "vendas_janelas": janelas,
        "vendas_7d": janelas["7"],
        "vendas_15d": janelas["15"],
        "vendas_30d": janelas["30"],
        "vendas_60d": janelas["60"],
        "vendas_90d": janelas["90"],
    }
