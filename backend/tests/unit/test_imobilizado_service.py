from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.financeiro.imobilizado_service import calcular_valores_bem, meses_decorridos


def _bem(**overrides):
    dados = {
        "data_aquisicao": date(2025, 1, 15),
        "data_baixa": None,
        "valor_aquisicao": Decimal("12000.00"),
        "valor_residual": Decimal("0.00"),
        "depreciar": True,
        "vida_util_meses": 60,
    }
    dados.update(overrides)
    return SimpleNamespace(**dados)


def test_meses_decorridos_considera_apenas_meses_completos():
    assert meses_decorridos(date(2025, 1, 15), date(2025, 2, 14)) == 0
    assert meses_decorridos(date(2025, 1, 15), date(2025, 2, 15)) == 1
    assert meses_decorridos(date(2024, 1, 31), date(2024, 2, 29)) == 1


def test_calcula_depreciacao_linear_e_valor_contabil():
    valores = calcular_valores_bem(_bem(), date(2026, 1, 15))

    assert valores["meses_depreciados"] == 12
    assert valores["depreciacao_acumulada"] == Decimal("2400.00")
    assert valores["valor_contabil"] == Decimal("9600.00")


def test_depreciacao_respeita_valor_residual_e_vida_util():
    bem = _bem(valor_residual=Decimal("2000.00"), vida_util_meses=10)
    valores = calcular_valores_bem(bem, date(2026, 1, 15))

    assert valores["meses_depreciados"] == 10
    assert valores["depreciacao_acumulada"] == Decimal("10000.00")
    assert valores["valor_contabil"] == Decimal("2000.00")


def test_bem_sem_depreciacao_mantem_valor_de_aquisicao():
    valores = calcular_valores_bem(
        _bem(depreciar=False, vida_util_meses=None),
        date(2026, 1, 15),
    )

    assert valores["meses_depreciados"] == 0
    assert valores["depreciacao_acumulada"] == Decimal("0.00")
    assert valores["valor_contabil"] == Decimal("12000.00")
