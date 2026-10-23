import pytest

from app.comissoes_demonstrativo_detail import montar_detalhe_comissao_snapshot


def _registro(**campos):
    return {
        "id": 1,
        "venda_id": 10,
        "numero_venda": "202610220001",
        "total_venda": 20,
        "data_venda": None,
        "funcionario_id": 2,
        "produto_id": 3,
        "venda_item_id": 4,
        "quantidade": 1.538,
        "item_quantidade": 1.538,
        "item_preco_unitario": 13,
        "item_subtotal": 20,
        "item_desconto": 0,
        "valor_venda": 20,
        "valor_custo": 7.69,
        "valor_base_original": 20,
        "valor_base_comissionada": 20,
        "valor_base_calculo": 20,
        "tipo_calculo": "venda",
        "percentual_comissao": 10,
        "valor_comissao": 2,
        "valor_comissao_gerada": 2,
        "percentual_aplicado": 100,
        "parcela_numero": 1,
        "percentual_pago": 100,
        "valor_pago_referencia": 20,
        "valor_pago": 2,
        "saldo_restante": 0,
        "data_pagamento": None,
        "forma_pagamento": "Pix",
        "status": "pendente",
        "data_estorno": None,
        "motivo_estorno": None,
        "observacao_pagamento": None,
        **campos,
    }


@pytest.mark.parametrize("desconto_item, desconto_geral", [(0, 0), (1, 2)])
def test_demonstrativo_preserva_bruto_digitado_e_descontos_reais(
    desconto_item, desconto_geral
):
    valor_venda = 20 - desconto_item - desconto_geral
    detalhe = montar_detalhe_comissao_snapshot(
        _registro(
            item_subtotal=20 - desconto_item,
            item_desconto=desconto_item,
            valor_venda=valor_venda,
            valor_base_calculo=valor_venda,
        )
    )

    assert detalhe["origem_base_calculo"]["valor_inicial"] == 20
    assert detalhe["deducoes"]["valor_bruto"] == 20
    assert detalhe["deducoes"]["desconto"] == desconto_item + desconto_geral
    assert detalhe["calculo"]["valor_comissao"] == 2


def test_demonstrativo_sem_subtotal_legado_calcula_bruto_pelo_peso():
    registro = _registro(valor_venda=19.99, valor_base_calculo=19.99)
    registro.pop("item_subtotal")
    registro.pop("item_desconto")

    detalhe = montar_detalhe_comissao_snapshot(registro)

    assert detalhe["deducoes"]["valor_bruto"] == 19.99
    assert detalhe["deducoes"]["desconto"] == 0
