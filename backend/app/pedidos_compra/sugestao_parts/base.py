"""Base e normalizadores da sugestao de compra."""

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
