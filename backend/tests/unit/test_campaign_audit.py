from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.campaigns.audit import (
    build_coupon_audit_metadata,
    build_coupon_redemption_audit_metadata,
    build_loyalty_stamp_audit_metadata,
)
from app.campaigns.models import CouponChannelEnum, CouponStatusEnum, CouponTypeEnum


def test_build_coupon_audit_metadata_records_reconciliation_fields():
    coupon = SimpleNamespace(
        id=10,
        code="FIEL-ABC",
        campaign_id=3,
        customer_id=55,
        coupon_type=CouponTypeEnum.fixed,
        discount_value=Decimal("25.00"),
        discount_percent=None,
        channel=CouponChannelEnum.pdv,
        status=CouponStatusEnum.active,
        valid_until=datetime(2026, 6, 1, tzinfo=timezone.utc),
        min_purchase_value=Decimal("80.00"),
        meta={"reference_period": "cycle-1", "token": "secret"},
    )

    metadata = build_coupon_audit_metadata(coupon, source="loyalty_reward")

    assert metadata["coupon_id"] == 10
    assert metadata["coupon_code"] == "FIEL-ABC"
    assert metadata["campaign_id"] == 3
    assert metadata["customer_id"] == 55
    assert metadata["coupon_type"] == "fixed"
    assert metadata["coupon_value"] == 25.0
    assert metadata["coupon_value_kind"] == "fixed"
    assert metadata["channel"] == "pdv"
    assert metadata["status"] == "active"
    assert metadata["source"] == "loyalty_reward"
    assert metadata["meta"]["reference_period"] == "cycle-1"


def test_build_coupon_redemption_audit_metadata_links_sale_and_redemption():
    coupon = SimpleNamespace(id=10, code="PROMO10", campaign_id=3, customer_id=55)
    redemption = SimpleNamespace(
        id=77,
        venda_id=999,
        customer_id=55,
        discount_applied=Decimal("12.50"),
        redeemed_at=datetime(2026, 5, 16, tzinfo=timezone.utc),
        voided_at=None,
        voided_reason=None,
    )

    metadata = build_coupon_redemption_audit_metadata(
        coupon=coupon,
        redemption=redemption,
        reason="Venda finalizada",
    )

    assert metadata == {
        "coupon_id": 10,
        "coupon_code": "PROMO10",
        "campaign_id": 3,
        "customer_id": 55,
        "redemption_id": 77,
        "venda_id": 999,
        "discount_applied": 12.5,
        "redeemed_at": "2026-05-16T00:00:00Z",
        "voided_at": None,
        "voided_reason": None,
        "reason": "Venda finalizada",
    }


def test_build_loyalty_stamp_audit_metadata_includes_balance_snapshot():
    stamp = SimpleNamespace(
        id=501,
        campaign_id=8,
        customer_id=55,
        venda_id=None,
        stamp_index=1,
        is_manual=True,
        notes="Ajuste cartao fisico",
        voided_at=None,
    )
    campaign = SimpleNamespace(id=8, campaign_type="loyalty_stamp", name="Fidelidade")

    metadata = build_loyalty_stamp_audit_metadata(
        stamp=stamp,
        campaign=campaign,
        operation="manual_added",
        balance={
            "total_carimbos": 11,
            "total_carimbos_brutos": 21,
            "carimbos_comprometidos_total": 10,
        },
    )

    assert metadata["stamp_id"] == 501
    assert metadata["campaign_id"] == 8
    assert metadata["campaign_name"] == "Fidelidade"
    assert metadata["customer_id"] == 55
    assert metadata["operation"] == "manual_added"
    assert metadata["is_manual"] is True
    assert metadata["balance"]["total_carimbos"] == 11
