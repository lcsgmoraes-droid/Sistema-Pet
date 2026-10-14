from decimal import Decimal

from app.campaigns.cashback_limit import cashback_amount_brl, cashback_available_in_sale


def test_cashback_limit_is_based_on_full_sale_and_previous_redemptions():
    assert cashback_available_in_sale(100, Decimal("20"), 0) == Decimal("20.00")
    assert cashback_available_in_sale(100, Decimal("20"), 7) == Decimal("13.00")
    assert cashback_available_in_sale(100, Decimal("20"), 20) == Decimal("0")


def test_cashback_limit_never_rounds_above_percent():
    assert cashback_available_in_sale("0.03", Decimal("20"), 0) == Decimal("0.00")
    assert cashback_amount_brl(Decimal("1234.50")) == "R$ 1.234,50"
