from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.campaigns.coupon_service import (
    consume_coupon_redemption,
    preview_coupon_redemption,
    reverse_coupon_redemptions_for_sale,
)
from app.campaigns.models import Coupon, CouponRedemption, CouponStatusEnum, CouponTypeEnum


def test_preview_coupon_redemption_only_validates_and_never_consumes():
    db = MagicMock()
    coupon = SimpleNamespace(
        code="FIEL-TESTE",
        coupon_type=CouponTypeEnum.fixed,
        discount_value=Decimal("25.00"),
        discount_percent=None,
    )

    with (
        patch(
            "app.campaigns.coupon_service._validate_coupon_for_redemption",
            return_value=coupon,
        ),
        patch(
            "app.campaigns.coupon_service._calculate_coupon_discount",
            return_value=Decimal("12.50"),
        ),
    ):
        result = preview_coupon_redemption(
            db,
            tenant_id="tenant-1",
            code="FIEL-TESTE",
            venda_total=100,
            customer_id=123,
        )

    assert result["preview_only"] is True
    assert result["discount_applied"] == 12.5
    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_consume_coupon_redemption_marks_coupon_used_and_links_sale():
    db = MagicMock()
    coupon = SimpleNamespace(
        id=10,
        code="FIEL-TESTE",
        status=CouponStatusEnum.active,
    )
    created = {}

    def fake_redemption(**kwargs):
        redemption = SimpleNamespace(id=77, **kwargs)
        created["redemption"] = redemption
        return redemption

    with (
        patch(
            "app.campaigns.coupon_service._validate_coupon_for_redemption",
            return_value=coupon,
        ),
        patch(
            "app.campaigns.coupon_service._calculate_coupon_discount",
            return_value=Decimal("25.00"),
        ),
        patch(
            "app.campaigns.coupon_service.CouponRedemption",
            side_effect=fake_redemption,
        ),
    ):
        result = consume_coupon_redemption(
            db,
            tenant_id="tenant-1",
            code="FIEL-TESTE",
            venda_total=100,
            customer_id=123,
            venda_id=999,
            expected_discount_applied=25,
        )

    assert coupon.status == CouponStatusEnum.used
    assert created["redemption"].venda_id == 999
    assert created["redemption"].customer_id == 123
    db.add.assert_called_once_with(created["redemption"])
    db.flush.assert_called_once()
    assert result == {
        "coupon_id": 10,
        "coupon_code": "FIEL-TESTE",
        "discount_applied": 25.0,
        "redemption_id": 77,
    }


def test_reverse_coupon_redemptions_for_sale_voids_loyalty_and_restores_regular():
    db = MagicMock()
    loyalty_redemption = SimpleNamespace(
        id=1,
        coupon_id=101,
        voided_at=None,
        voided_reason=None,
    )
    regular_redemption = SimpleNamespace(
        id=2,
        coupon_id=202,
        voided_at=None,
        voided_reason=None,
    )
    loyalty_coupon = SimpleNamespace(
        id=101,
        tenant_id="tenant-1",
        status=CouponStatusEnum.used,
        valid_until=None,
    )
    regular_coupon = SimpleNamespace(
        id=202,
        tenant_id="tenant-1",
        status=CouponStatusEnum.used,
        valid_until=datetime.now(timezone.utc) + timedelta(days=5),
    )

    redemptions_query = MagicMock()
    redemptions_query.filter.return_value = redemptions_query
    redemptions_query.order_by.return_value = redemptions_query
    redemptions_query.all.return_value = [loyalty_redemption, regular_redemption]

    coupons_query = MagicMock()
    coupons_query.filter.return_value = coupons_query
    coupons_query.first.side_effect = [loyalty_coupon, regular_coupon]

    def query_side_effect(model):
        if model is CouponRedemption:
            return redemptions_query
        if model is Coupon:
            return coupons_query
        raise AssertionError(f"Unexpected model queried: {model}")

    db.query.side_effect = query_side_effect

    with patch(
        "app.campaigns.loyalty_service.revoke_loyalty_reward_by_coupon",
        side_effect=lambda _db, tenant_id, coupon_id, reason: {
            "matched": coupon_id == 101,
            "revoked": coupon_id == 101,
        },
    ):
        result = reverse_coupon_redemptions_for_sale(
            db,
            tenant_id="tenant-1",
            venda_id=999,
            reason="Venda reaberta para ajuste",
        )

    assert loyalty_redemption.voided_at is not None
    assert loyalty_redemption.voided_reason == "Venda reaberta para ajuste"
    assert regular_redemption.voided_at is not None
    assert regular_redemption.voided_reason == "Venda reaberta para ajuste"
    assert loyalty_coupon.status == CouponStatusEnum.voided
    assert regular_coupon.status == CouponStatusEnum.active
    db.flush.assert_called_once()
    assert result == {
        "redemptions_voided": 2,
        "loyalty_rewards_reversed": 1,
        "regular_coupons_restored": 1,
    }
