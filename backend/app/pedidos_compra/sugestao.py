from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional


JANELAS_GIRO_SUGESTAO = (7, 15, 30, 60, 90)
MIN_VENDAS_AJUSTE_RUPTURA = 3
MIN_DIAS_COM_ESTOQUE_AJUSTE_RUPTURA = 7
MAX_MULTIPLICADOR_AJUSTE_RUPTURA = 2.0
MARGEM_SEGURANCA_COMPRA_DIAS = 7


def _float_seguro_sugestao(valor, padrao: float = 0.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if math.isfinite(numero) else padrao


def _round_seguro_sugestao(valor, casas: int = 2, padrao: float = 0.0) -> float:
    return round(_float_seguro_sugestao(valor, padrao), casas)


def _sanitizar_json_sugestao(valor):
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else 0.0
    if isinstance(valor, dict):
        return {chave: _sanitizar_json_sugestao(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_sanitizar_json_sugestao(item) for item in valor]
    return valor


def _datetime_naive_utc_sugestao(valor: Optional[datetime]) -> Optional[datetime]:
    if not valor:
        return None

    if valor.tzinfo is not None and valor.utcoffset() is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)

    return valor


def _formatar_origem_venda(canal: Optional[str]) -> str:
    canal_normalizado = str(canal or "loja_fisica").strip().lower()
    nomes = {
        "loja_fisica": "Loja",
        "pdv": "Loja",
        "mercado_livre": "Mercado Livre",
        "shopee": "Shopee",
        "amazon": "Amazon",
        "site": "Site",
        "instagram": "Instagram",
        "bling": "Bling/online",
        "venda_bling": "Bling/online",
        "granel": "Granel",
        "granel_kit": "Granel/kit",
        "kit_virtual": "Granel/kit",
        "movimentacao": "Mov. estoque",
    }
    return nomes.get(canal_normalizado, canal_normalizado.replace("_", " ").title())


def _nova_stats_venda_sugestao() -> dict:
    return {
        "vendas_periodo": 0.0,
        "janelas": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
        "granel_kg_periodo": 0.0,
        "granel_pacotes_periodo": 0.0,
        "granel_janelas_kg": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
        "granel_janelas_pacotes": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
        "granel_itens": defaultdict(lambda: {"kg": 0.0, "pacotes": 0.0}),
        "origens": defaultdict(float),
        "fontes": set(),
        "pares_venda_produto": set(),
    }


def _somar_venda_sugestao(
    stats_por_produto: dict,
    produto_id: int,
    quantidade: float,
    data_ref: Optional[datetime],
    data_inicio_periodo: datetime,
    data_fim: datetime,
    origem: str,
    fonte: str,
):
    if not produto_id or not data_ref:
        return

    data_ref = _datetime_naive_utc_sugestao(data_ref)
    data_inicio_periodo = _datetime_naive_utc_sugestao(data_inicio_periodo)
    data_fim = _datetime_naive_utc_sugestao(data_fim)
    if not data_ref or not data_inicio_periodo or not data_fim:
        return

    quantidade = _float_seguro_sugestao(quantidade)
    if quantidade <= 0:
        return

    stats = stats_por_produto[produto_id]
    if data_ref >= data_inicio_periodo:
        stats["vendas_periodo"] += quantidade

    dias_decorridos = max(0.0, (data_fim - data_ref).total_seconds() / 86400)
    for dias in JANELAS_GIRO_SUGESTAO:
        if dias_decorridos <= dias:
            stats["janelas"][str(dias)] += quantidade

    stats["origens"][_formatar_origem_venda(origem)] += quantidade
    stats["fontes"].add(fonte)


def _somar_conversao_granel_sugestao(
    stats_por_produto: dict,
    produto_pai_id: int,
    produto_granel_id: int,
    produto_granel_nome: str | None,
    quantidade_kg: float,
    quantidade_pacotes: float,
    peso_pacote_kg: float,
    data_ref: Optional[datetime],
    data_inicio_periodo: datetime,
    data_fim: datetime,
):
    data_ref = _datetime_naive_utc_sugestao(data_ref)
    data_inicio_periodo = _datetime_naive_utc_sugestao(data_inicio_periodo)
    data_fim = _datetime_naive_utc_sugestao(data_fim)

    quantidade_kg = _float_seguro_sugestao(quantidade_kg)
    quantidade_pacotes = _float_seguro_sugestao(quantidade_pacotes)
    peso_pacote_kg = _float_seguro_sugestao(peso_pacote_kg)
    produto_pai_id = int(produto_pai_id or 0)
    if quantidade_kg <= 0 or quantidade_pacotes <= 0 or not produto_pai_id:
        return

    _somar_venda_sugestao(
        stats_por_produto,
        produto_pai_id,
        quantidade_pacotes,
        data_ref,
        data_inicio_periodo,
        data_fim,
        "granel",
        "conversao_granel",
    )

    if not data_ref or not data_inicio_periodo or not data_fim:
        return

    stats = stats_por_produto[produto_pai_id]
    if data_ref >= data_inicio_periodo:
        stats["granel_kg_periodo"] += quantidade_kg
        stats["granel_pacotes_periodo"] += quantidade_pacotes

    dias_decorridos = max(0.0, (data_fim - data_ref).total_seconds() / 86400)
    for dias in JANELAS_GIRO_SUGESTAO:
        if dias_decorridos <= dias:
            stats["granel_janelas_kg"][str(dias)] += quantidade_kg
            stats["granel_janelas_pacotes"][str(dias)] += quantidade_pacotes

    produto_granel_id = int(produto_granel_id or 0)
    item = stats["granel_itens"][produto_granel_id]
    item["produto_id"] = produto_granel_id
    item["produto_nome"] = produto_granel_nome
    item["peso_pacote_kg"] = peso_pacote_kg
    item["kg"] += quantidade_kg
    item["pacotes"] += quantidade_pacotes
