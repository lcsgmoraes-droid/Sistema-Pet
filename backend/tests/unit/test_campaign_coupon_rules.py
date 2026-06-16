from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.campaigns.coupon_rules import (
    _calculate_coupon_discount,
    _coupon_is_expired,
    _normalize_coupon_code,
)
from app.campaigns.models import CouponTypeEnum


def test_normalize_coupon_code_limpa_e_padroniza():
    assert _normalize_coupon_code(" abc-123 ") == "ABC-123"
    assert _normalize_coupon_code(None) == ""


def test_calculate_coupon_discount_percentual_com_arredondamento():
    coupon = SimpleNamespace(
        coupon_type=CouponTypeEnum.percent,
        discount_percent=Decimal("12.5"),
        discount_value=None,
    )

    desconto = _calculate_coupon_discount(coupon, Decimal("99.99"))

    assert desconto == Decimal("12.50")


def test_calculate_coupon_discount_fixo_limitado_ao_total():
    coupon = SimpleNamespace(
        coupon_type=CouponTypeEnum.fixed,
        discount_percent=None,
        discount_value=Decimal("50.00"),
    )

    desconto = _calculate_coupon_discount(coupon, Decimal("30.00"))

    assert desconto == Decimal("30.00")


def test_coupon_is_expired_alinha_datetime_naive_e_aware():
    coupon = SimpleNamespace(valid_until=datetime(2026, 5, 16, 10, 0))

    assert (
        _coupon_is_expired(coupon, datetime(2026, 5, 16, 10, 1, tzinfo=timezone.utc))
        is True
    )
    assert (
        _coupon_is_expired(coupon, datetime(2026, 5, 16, 9, 59, tzinfo=timezone.utc))
        is False
    )
