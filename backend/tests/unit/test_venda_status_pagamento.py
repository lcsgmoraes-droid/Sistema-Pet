from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.vendas.status_pagamento import calcular_resumo_pagamento_venda


def _conta(
    *,
    valor_final=50,
    valor_recebido=0,
    status="pendente",
    forma_pagamento_id=10,
):
    return SimpleNamespace(
        valor_final=valor_final,
        valor_recebido=valor_recebido,
        status=status,
        forma_pagamento_id=forma_pagamento_id,
    )


def _pagamento(*, valor, forma_pagamento, forma_pagamento_id=10):
    return SimpleNamespace(
        valor=valor,
        forma_pagamento=forma_pagamento,
        forma_pagamento_id=forma_pagamento_id,
        intervalo_crediario=None,
    )


@pytest.mark.parametrize("forma_pagamento", ["Débito", "Crédito", "PIX", "Dinheiro"])
def test_pagamento_do_cliente_fica_pago_mesmo_com_repasse_pendente(forma_pagamento):
    resumo = calcular_resumo_pagamento_venda(
        total=31.90,
        contas_receber=[_conta(valor_final=31.90, valor_recebido=0, status="pendente")],
        pagamentos=[_pagamento(valor=31.90, forma_pagamento=forma_pagamento)],
    )

    assert resumo["status_pagamento"] == "pago"
    assert resumo["valor_pago"] == Decimal("31.90")
    assert resumo["valor_restante"] == 0


def test_crediario_aberto_nao_conta_plano_como_pagamento():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[_conta(), _conta()],
        pagamentos=[_pagamento(valor=100, forma_pagamento="Crediário")],
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
        pagamentos=[_pagamento(valor=100, forma_pagamento="Crediário")],
    )

    assert resumo["status_pagamento"] == "parcial"
    assert resumo["valor_pago"] == 20
    assert resumo["valor_restante"] == 80


def test_crediario_fica_pago_quando_todas_as_parcelas_forem_baixadas():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[
            _conta(valor_final=50, valor_recebido=50, status="recebido"),
            _conta(valor_final=50, valor_recebido=50, status="recebido"),
        ],
        pagamentos=[_pagamento(valor=100, forma_pagamento="Crediário")],
    )

    assert resumo["status_pagamento"] == "pago"
    assert resumo["valor_pago"] == 100
    assert resumo["valor_restante"] == 0


def test_pagamento_misto_soma_parte_imediata_com_baixa_do_crediario():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[
            _conta(
                valor_final=30,
                valor_recebido=0,
                status="pendente",
                forma_pagamento_id=20,
            ),
            _conta(
                valor_final=70,
                valor_recebido=20,
                status="parcial",
                forma_pagamento_id=30,
            ),
        ],
        pagamentos=[
            _pagamento(
                valor=30,
                forma_pagamento="Débito",
                forma_pagamento_id=20,
            ),
            _pagamento(
                valor=70,
                forma_pagamento="Crediário",
                forma_pagamento_id=30,
            ),
        ],
    )

    assert resumo["status_pagamento"] == "parcial"
    assert resumo["valor_pago"] == 50
    assert resumo["valor_restante"] == 50
