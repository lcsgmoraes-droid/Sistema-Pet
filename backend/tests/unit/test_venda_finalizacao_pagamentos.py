from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.vendas.service import _calcular_pagamentos_finalizacao


def test_calcular_pagamentos_finalizacao_permite_venda_ja_quitada_sem_novo_pagamento():
    existente = SimpleNamespace(valor=Decimal("90.00"))

    resultado = _calcular_pagamentos_finalizacao(
        total_venda=Decimal("90.00"),
        pagamentos_existentes=[existente],
        pagamentos_novos=[],
    )

    assert resultado["total_ja_pago"] == 90.0
    assert resultado["total_novos_pagamentos"] == 0.0
    assert resultado["total_pagamentos"] == 90.0
    assert resultado["valor_restante"] == 0.0


@pytest.mark.parametrize("forma", ["PIX", "Crédito Cliente", "Cashback", "Dinheiro"])
@pytest.mark.parametrize("total", ["28.99", "34.89"])
def test_um_centavo_excedente_nao_pode_ser_aplicado_a_venda(forma, total):
    with pytest.raises(HTTPException, match="excede o saldo"):
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal(total),
            pagamentos_existentes=[],
            pagamentos_novos=[
                {"forma_pagamento": forma, "valor": Decimal(total) + Decimal("0.01")}
            ],
        )


def test_pagamentos_mistos_usam_centavos_exatos():
    pagamentos = [
        {"forma_pagamento": "Cashback", "valor": 0.1},
        {"forma_pagamento": "PIX", "valor": 0.2},
    ]
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=Decimal("0.30"),
        pagamentos_existentes=[],
        pagamentos_novos=pagamentos,
    )
    assert resultado["total_pagamentos"] == 0.30
    assert pagamentos[0]["valor_recebido"] == 0.10
    assert pagamentos[0]["troco"] == 0


def test_dinheiro_aplica_so_divida_e_calcula_troco_do_centavo():
    pagamento = {"forma_pagamento": "Dinheiro", "valor": 28.99, "valor_recebido": 29}
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=Decimal("28.99"),
        pagamentos_existentes=[],
        pagamentos_novos=[pagamento],
    )
    assert resultado["total_pagamentos"] == 28.99
    assert pagamento["valor_recebido"] == 29
    assert pagamento["troco"] == 0.01


@pytest.mark.parametrize(
    "recebido,troco", [(28, None), (29, 0), (29, 0.02), (float("nan"), None)]
)
def test_dinheiro_rejeita_recebido_ou_troco_inconsistente(recebido, troco):
    with pytest.raises(HTTPException):
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("28.99"),
            pagamentos_existentes=[],
            pagamentos_novos=[
                {
                    "forma_pagamento": "Dinheiro",
                    "valor": 28.99,
                    "valor_recebido": recebido,
                    "troco": troco,
                }
            ],
        )


@pytest.mark.parametrize("forma", ["Cashback", "Crédito Cliente", "credito_cliente"])
def test_beneficio_nao_pode_gerar_troco_ou_registrar_debito_maior(forma):
    with pytest.raises(HTTPException):
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("34.89"),
            pagamentos_existentes=[],
            pagamentos_novos=[
                {
                    "forma_pagamento": forma,
                    "valor": 34.89,
                    "valor_recebido": 34.90,
                    "troco": 0.01,
                }
            ],
        )


def test_ultimo_centavo_pode_ser_pago():
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=Decimal("28.99"),
        pagamentos_existentes=[SimpleNamespace(valor=Decimal("28.98"))],
        pagamentos_novos=[{"forma_pagamento": "PIX", "valor": 0.01}],
    )
    assert resultado["valor_restante"] == 0.01
    assert resultado["total_pagamentos"] == 28.99


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), "abc"])
def test_pagamentos_nao_finitos_ou_invalidos_sao_rejeitados(valor):
    with pytest.raises(HTTPException):
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("28.99"),
            pagamentos_existentes=[],
            pagamentos_novos=[{"forma_pagamento": "PIX", "valor": valor}],
        )


def test_calcular_pagamentos_finalizacao_exige_pagamento_quando_venda_nao_esta_quitada():
    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("90.00"),
            pagamentos_existentes=[],
            pagamentos_novos=[],
        )

    assert exc.value.status_code == 400
    assert "Informe pelo menos uma forma de pagamento" in exc.value.detail


@pytest.mark.parametrize("valor", [0, -1, 0.001])
def test_calcular_pagamentos_finalizacao_rejeita_item_sem_valor(valor):
    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("179.90"),
            pagamentos_existentes=[],
            pagamentos_novos=[
                {"forma_pagamento": "Cartão de débito", "valor": 179.90},
                {"forma_pagamento": "Cartão de débito", "valor": valor},
            ],
        )

    assert exc.value.status_code == 400
    assert "cada pagamento" in exc.value.detail


def test_calcular_pagamentos_finalizacao_rejeita_novo_pagamento_em_venda_ja_quitada():
    existente = SimpleNamespace(valor=Decimal("90.00"))

    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("90.00"),
            pagamentos_existentes=[existente],
            pagamentos_novos=[{"forma_pagamento": "PIX", "valor": 10.0}],
        )

    assert exc.value.status_code == 400
    assert "totalmente paga" in exc.value.detail


@pytest.mark.parametrize("total_editado", [Decimal("20.00"), Decimal("0.00")])
def test_reducao_preserva_pagamentos_anteriores_e_permite_refinalizar(total_editado):
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=total_editado,
        pagamentos_existentes=[SimpleNamespace(valor=Decimal("60.00"))],
        pagamentos_novos=[],
    )
    assert resultado == {
        "total_ja_pago": 60.0,
        "total_novos_pagamentos": 0.0,
        "total_pagamentos": 60.0,
        "valor_restante": 0.0,
    }


def test_reducao_nao_autoriza_receber_novo_pagamento():
    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("20.00"),
            pagamentos_existentes=[SimpleNamespace(valor=Decimal("60.00"))],
            pagamentos_novos=[{"forma_pagamento": "PIX", "valor": 1}],
        )
    assert exc.value.status_code == 400
    assert "totalmente paga" in exc.value.detail


@pytest.mark.parametrize(
    "status", [" ESTORNADO ", "Recusado", "cancelado", "cancelada"]
)
def test_pagamento_invalidado_nao_abate_complemento_da_venda(status):
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=Decimal("80.00"),
        pagamentos_existentes=[
            SimpleNamespace(valor=Decimal("60.00"), status=status),
            SimpleNamespace(valor=Decimal("20.00"), status="pendente"),
        ],
        pagamentos_novos=[{"forma_pagamento": "PIX", "valor": 60.0}],
    )

    assert resultado == {
        "total_ja_pago": 20.0,
        "total_novos_pagamentos": 60.0,
        "total_pagamentos": 80.0,
        "valor_restante": 60.0,
    }


def test_apenas_pagamento_estornado_exige_recebimento_na_refinalizacao():
    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("80.00"),
            pagamentos_existentes=[
                SimpleNamespace(valor=Decimal("80.00"), status="estornado")
            ],
            pagamentos_novos=[],
        )
    assert exc.value.status_code == 400
    assert "Informe pelo menos uma forma de pagamento" in exc.value.detail


def test_plano_crediario_valido_mantem_alocacao_na_finalizacao():
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=Decimal("80.00"),
        pagamentos_existentes=[
            SimpleNamespace(
                valor=Decimal("80.00"),
                forma_pagamento="Crediario",
                intervalo_crediario="mensal",
                status="pendente",
            )
        ],
        pagamentos_novos=[],
    )
    assert resultado["total_ja_pago"] == 80.0
    assert resultado["valor_restante"] == 0.0
