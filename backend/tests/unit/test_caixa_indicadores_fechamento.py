from app.caixa.conferencia import indicadores_vendas_recebimentos


def test_vendido_e_recebido_nao_somam_crediario_ou_boleto():
    resultado = indicadores_vendas_recebimentos(
        250.00,
        {
            "Dinheiro": {"total": 50.10},
            "PIX": {"total": 49.90},
            "Crediário": {"total": 100.00},
            "Boleto": {"total": 50.00},
        },
    )

    assert resultado["total_vendido"] == 250.00
    assert resultado["total_recebido"] == 100.00
    assert set(resultado["recebimentos_por_forma_pagamento"]) == {"Dinheiro", "PIX"}


def test_indicadores_sem_vendas_ou_pagamentos():
    resultado = indicadores_vendas_recebimentos(None, {})
    assert resultado["total_vendido"] == 0
    assert resultado["total_recebido"] == 0
