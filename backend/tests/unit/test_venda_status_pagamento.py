from types import SimpleNamespace

from app.vendas.status_pagamento import calcular_resumo_pagamento_venda


def _conta(*, valor_final=50, valor_recebido=0, status="pendente"):
    return SimpleNamespace(
        valor_final=valor_final,
        valor_recebido=valor_recebido,
        status=status,
    )


def test_crediario_aberto_nao_conta_plano_como_pagamento():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[_conta(), _conta()],
        pagamentos=[SimpleNamespace(valor=100)],
    )

    assert resumo["status_pagamento"] == "em_aberto"
    assert resumo["valor_pago"] == 0
    assert resumo["valor_restante"] == 100


def test_crediario_fica_parcial_depois_da_primeira_baixa():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[
            _conta(valor_final=50, valor_recebido=20, status="parcial"),
            _conta(),
        ],
        pagamentos=[SimpleNamespace(valor=100)],
    )

    assert resumo["status_pagamento"] == "parcial"
    assert resumo["valor_pago"] == 20
    assert resumo["valor_restante"] == 80


def test_crediario_fica_pago_quando_todas_as_parcelas_foremd_baixadas():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[
            _conta(valor_final=50, valor_recebido=50, status="recebido"),
            _conta(valor_final=50, valor_recebido=50, status="recebido"),
        ],
        pagamentos=[SimpleNamespace(valor=100)],
    )

    assert resumo["status_pagamento"] == "pago"
    assert resumo["valor_pago"] == 100
    assert resumo["valor_restante"] == 0
