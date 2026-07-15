"""Calculos gerenciais do imobilizado."""

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


CENTAVOS = Decimal("0.01")


def decimal_moeda(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def meses_decorridos(inicio: date, fim: date) -> int:
    """Conta meses completos entre duas datas, sem aproximacao por dias."""
    if fim <= inicio:
        return 0
    meses = (fim.year - inicio.year) * 12 + fim.month - inicio.month
    ultimo_dia_fim = monthrange(fim.year, fim.month)[1]
    dia_equivalente = min(inicio.day, ultimo_dia_fim)
    if fim.day < dia_equivalente:
        meses -= 1
    return max(meses, 0)


def calcular_valores_bem(bem, data_referencia: date | None = None) -> dict:
    """Calcula depreciacao linear sem alterar o valor originalmente cadastrado."""
    referencia = data_referencia or date.today()
    data_final = min(
        referencia,
        getattr(bem, "data_baixa", None) or referencia,
    )
    aquisicao = decimal_moeda(getattr(bem, "valor_aquisicao", 0))
    residual = min(
        decimal_moeda(getattr(bem, "valor_residual", 0)),
        aquisicao,
    )
    vida_util = int(getattr(bem, "vida_util_meses", 0) or 0)
    deve_depreciar = bool(getattr(bem, "depreciar", True)) and vida_util > 0
    meses = (
        meses_decorridos(getattr(bem, "data_aquisicao"), data_final)
        if deve_depreciar
        else 0
    )
    meses_depreciados = min(meses, vida_util) if deve_depreciar else 0
    base_depreciavel = max(aquisicao - residual, Decimal("0"))
    depreciacao = (
        base_depreciavel * Decimal(meses_depreciados) / Decimal(vida_util)
        if deve_depreciar
        else Decimal("0")
    ).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    valor_contabil = max(aquisicao - depreciacao, residual).quantize(
        CENTAVOS,
        rounding=ROUND_HALF_UP,
    )
    return {
        "meses_depreciados": meses_depreciados,
        "depreciacao_acumulada": depreciacao,
        "valor_contabil": valor_contabil,
    }
