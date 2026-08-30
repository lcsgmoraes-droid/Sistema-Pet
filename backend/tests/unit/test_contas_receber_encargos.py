from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.contas_receber_encargos import (
    aplicar_encargos_automaticos,
    calcular_encargos_automaticos,
)


def _config(**overrides):
    valores = {
        "crediario_encargos_automaticos": True,
        "crediario_multa_percentual": Decimal("2.00"),
        "crediario_juros_mensal_percentual": Decimal("1.00"),
        "dias_tolerancia_atraso": 5,
    }
    valores.update(overrides)
    return SimpleNamespace(**valores)


def _conta(**overrides):
    valores = {
        "status": "pendente",
        "data_vencimento": date(2026, 1, 1),
        "valor_original": Decimal("100.00"),
        "valor_final": Decimal("100.00"),
        "valor_recebido": Decimal("0.00"),
        "valor_desconto": Decimal("0.00"),
        "valor_juros": Decimal("0.00"),
        "valor_multa": Decimal("0.00"),
        "data_ultimo_calculo_encargos": None,
        "multa_atraso_aplicada": False,
        "forma_pagamento": SimpleNamespace(tipo="crediario"),
    }
    valores.update(overrides)
    return SimpleNamespace(**valores)


def test_calcula_multa_unica_e_juros_proporcionais_apos_tolerancia():
    calculo = calcular_encargos_automaticos(_conta(), date(2026, 2, 5), _config())

    assert calculo["dias_atraso"] == 35
    assert calculo["dias_cobrados"] == 30
    assert calculo["valor_juros_calculado"] == Decimal("1.00")
    assert calculo["valor_multa_calculada"] == Decimal("2.00")
    assert calculo["saldo_atualizado"] == Decimal("103.00")


def test_nao_cobra_dentro_da_tolerancia_ou_fora_do_crediario():
    dentro_tolerancia = calcular_encargos_automaticos(
        _conta(), date(2026, 1, 6), _config()
    )
    outra_forma = calcular_encargos_automaticos(
        _conta(forma_pagamento=SimpleNamespace(tipo="pix")),
        date(2026, 2, 5),
        _config(),
    )

    assert dentro_tolerancia["saldo_atualizado"] == Decimal("100.00")
    assert dentro_tolerancia["dias_cobrados"] == 0
    assert outra_forma["encargos_automaticos_ativos"] is False
    assert outra_forma["saldo_atualizado"] == Decimal("100.00")


def test_calculo_incremental_nao_repete_multa_ja_aplicada():
    conta = _conta(
        valor_final=Decimal("102.50"),
        valor_juros=Decimal("0.50"),
        valor_multa=Decimal("2.00"),
        data_ultimo_calculo_encargos=date(2026, 1, 21),
        multa_atraso_aplicada=True,
    )
    calculo = calcular_encargos_automaticos(
        conta,
        date(2026, 1, 31),
        _config(dias_tolerancia_atraso=0),
    )

    assert calculo["dias_cobrados"] == 10
    assert calculo["valor_juros_calculado"] == Decimal("0.33")
    assert calculo["valor_multa_calculada"] == Decimal("0.00")
    assert calculo["saldo_atualizado"] == Decimal("102.83")


def test_aplicar_encargos_atualiza_controles_incrementais():
    conta = _conta()
    data_calculo = date(2026, 2, 5)
    calculo = calcular_encargos_automaticos(conta, data_calculo, _config())

    aplicar_encargos_automaticos(conta, calculo, data_calculo)

    assert conta.valor_final == Decimal("103.00")
    assert conta.valor_juros == Decimal("1.00")
    assert conta.valor_multa == Decimal("2.00")
    assert conta.data_ultimo_calculo_encargos == data_calculo
    assert conta.multa_atraso_aplicada is True
