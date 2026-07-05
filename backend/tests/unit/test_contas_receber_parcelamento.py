from decimal import Decimal

from app.financeiro.contas_receber_service import ContasReceberService


def test_distribuir_valor_parcelas_preserva_total_com_centavos():
    parcelas = ContasReceberService._distribuir_valor_parcelas(
        Decimal("200.00"),
        3,
    )

    assert parcelas == [Decimal("66.67"), Decimal("66.67"), Decimal("66.66")]
    assert sum(parcelas) == Decimal("200.00")


def test_distribuir_valor_parcelas_ultima_parcela_absorve_resto_positivo():
    parcelas = ContasReceberService._distribuir_valor_parcelas(
        Decimal("354.26"),
        4,
    )

    assert parcelas == [
        Decimal("88.57"),
        Decimal("88.57"),
        Decimal("88.57"),
        Decimal("88.55"),
    ]
    assert sum(parcelas) == Decimal("354.26")
