"""Editing quantities preserves benefit history and does not duplicate rewards."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import insert

from app.campaigns import (
    cashback_sale_reversal,
    loyalty_service,
    sale_reopening_service,
)
from app.campaigns.handlers import quick_repurchase
from app.campaigns.models import (
    CampaignTypeEnum,
    CashbackSourceTypeEnum,
    Coupon,
    CouponStatusEnum,
    CouponTypeEnum,
)
from app.campaigns.sale_return_service import _reconcile_cashback


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def filter(self, *clauses):
        self.filters.extend(clauses)
        return self

    def with_for_update(self):
        return self

    def order_by(self, *clauses):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


def test_reopening_revokes_rest_of_previously_partially_reversed_lot():
    added = []
    db = SimpleNamespace(add=added.append)
    args = {
        "tenant_id": "tenant-a",
        "sale_id": 9,
        "customer_id": 2,
        "credit": SimpleNamespace(id=11),
    }

    cashback_sale_reversal._revoke_credit_if_unspent(
        db, **args, wallet=SimpleNamespace(remaining_by_credit={11: Decimal("8.00")})
    )
    cashback_sale_reversal._revoke_credit_if_unspent(
        db, **args, wallet=SimpleNamespace(remaining_by_credit={11: Decimal("0.00")})
    )

    assert [(tx.amount, tx.source_id, tx.tenant_id) for tx in added] == [
        (Decimal("-8.00"), 11, "tenant-a")
    ]


@pytest.mark.parametrize(
    "old_reversed,new_grant,expected_reversal",
    [
        ("10", "20", "10"),  # old award fully revoked, quantity doubled
        ("6", "16", "10"),  # four already consumed before reopening
    ],
)
def test_return_after_quantity_increase_reconciles_combined_award(
    monkeypatch, old_reversed, new_grant, expected_reversal
):
    execution = SimpleNamespace(
        id=21, reward_meta={"venda_total_base": 200, "cashback_entitlement": 20}
    )
    old = SimpleNamespace(id=12, amount=Decimal("10"))
    new = SimpleNamespace(id=13, amount=Decimal(new_grant))
    reversal = SimpleNamespace(
        amount=-Decimal(old_reversed), source_type=CashbackSourceTypeEnum.reversal
    )
    queries = [
        Query([execution]),
        Query([old, new]),
        Query([]),
        Query([reversal]),
        Query([]),
    ]
    added = []
    wallet = SimpleNamespace(
        remaining_by_credit={12: Decimal("0"), 13: Decimal(new_grant)},
        expected_expiration_by_credit={},
    )
    monkeypatch.setattr(
        "app.campaigns.cashback_wallet.lock_cashback_customer", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "app.campaigns.cashback_wallet.get_cashback_wallet", lambda *a, **k: wallet
    )
    db = SimpleNamespace(
        query=lambda *args: queries.pop(0), add=added.append, flush=lambda: None
    )

    amount = _reconcile_cashback(
        db,
        tenant_id="tenant-a",
        venda=SimpleNamespace(id=9, cliente_id=2, total=Decimal("200")),
        evento_devolucao=SimpleNamespace(id=7),
        retained=Decimal("100"),
    )

    assert amount == Decimal(expected_reversal)
    assert [(tx.amount, tx.source_id) for tx in added] == [(Decimal("-10"), 13)]


def test_return_also_revokes_refund_from_same_reward_without_touching_other_lots(
    monkeypatch,
):
    execution = SimpleNamespace(id=21, reward_meta={"venda_total_base": 100})
    grant = SimpleNamespace(id=12, amount=Decimal("10"))
    refund = SimpleNamespace(id=15, amount=Decimal("8"), origin_credit_id=12)
    queries = [
        Query([execution]),
        Query([grant]),
        Query([refund]),
        Query([]),
        Query([]),
    ]
    added = []
    monkeypatch.setattr(
        "app.campaigns.cashback_wallet.lock_cashback_customer", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "app.campaigns.cashback_wallet.get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            remaining_by_credit={
                12: Decimal("0"),
                15: Decimal("8"),
                99: Decimal("200"),
            },
            expected_expiration_by_credit={},
        ),
    )
    db = SimpleNamespace(
        query=lambda *args: queries.pop(0), add=added.append, flush=lambda: None
    )

    amount = _reconcile_cashback(
        db,
        tenant_id="tenant-a",
        venda=SimpleNamespace(id=9, cliente_id=2, total=Decimal("100")),
        evento_devolucao=SimpleNamespace(id=7),
        retained=Decimal("0"),
    )

    assert amount == Decimal("8")
    assert [(tx.source_id, tx.amount) for tx in added] == [(15, Decimal("-8"))]


def test_loyalty_stamps_follow_increase_reduction_removal_and_repeat(monkeypatch):
    stamps = []
    audit = []
    db = SimpleNamespace(
        query=lambda *args: Query(stamps), add=stamps.append, flush=lambda: None
    )
    campaign = SimpleNamespace(
        id=3, tenant_id="tenant-a", name="Cartao", params={"min_purchase_value": 100}
    )

    def sync_rewards(db, **kwargs):
        count = sum(stamp.voided_at is None for stamp in stamps)
        return dict(
            total_stamps=count,
            available_stamps=count,
            converted_stamps=0,
            debt_stamps=0,
            awarded=0,
            revoked=0,
        )

    monkeypatch.setattr(
        loyalty_service, "sync_loyalty_rewards_for_customer", sync_rewards
    )
    monkeypatch.setattr(
        loyalty_service, "log_campaign_event", lambda **kwargs: audit.append(kwargs)
    )

    def sync(total):
        return loyalty_service.sync_loyalty_stamps_for_sale(
            db,
            campaign=campaign,
            customer_id=2,
            venda_id=9,
            venda_total=total,
            reason="Edicao de quantidades",
        )

    assert sync(200)["stamps_added"] == 2
    for index, stamp in enumerate(stamps):
        stamp.id = index + 1
    # Changing current settings must not alter the historical value per stamp.
    campaign.params["min_purchase_value"] = 50
    assert sync(100)["stamps_voided"] == 1
    assert sync(300)["expected_stamps"] == 3
    assert len(stamps) == 3
    assert sync(0)["stamps_voided"] == 3
    assert sync(100)["stamps_reactivated"] == 1
    assert sync(100)["stamps_added"] == 0
    assert len(stamps) == 3
    assert sum(stamp.voided_at is None for stamp in stamps) == 1
    assert all(stamp.stamp_value_snapshot == Decimal("100") for stamp in stamps)
    assert all(row["tenant_id"] == "tenant-a" for row in audit)


def coupon(status=CouponStatusEnum.active, **meta):
    return SimpleNamespace(
        id=7,
        code="VOLTE",
        status=status,
        valid_until=datetime.now(timezone.utc) + timedelta(days=2),
        discount_value=Decimal("25"),
        meta={
            "source_kind": "quick_repurchase",
            "source_venda_id": 9,
            "min_purchase_value_snapshot": "150",
            **meta,
        },
    )


def test_reopening_suspends_only_coupon_issued_by_edited_sale(monkeypatch):
    issued = coupon()
    unrelated = coupon(source_venda_id=10)
    query = Query([issued, unrelated])
    audit = []
    monkeypatch.setattr(
        sale_reopening_service, "log_campaign_event", lambda **kw: audit.append(kw)
    )

    count = sale_reopening_service.void_quick_repurchase_coupons_for_sale(
        SimpleNamespace(query=lambda *a: query), tenant_id="tenant-a", venda_id=9
    )

    assert count == 1
    assert issued.status == CouponStatusEnum.voided
    assert unrelated.status == CouponStatusEnum.active
    assert audit[0]["metadata"]["source_venda_id"] == 9
    assert "coupons.tenant_id" in str(query.filters[0])


@pytest.mark.parametrize("new_total,expected", [(100, 0), (200, 1)])
def test_edited_sale_reuses_same_coupon_with_original_minimum_and_expiry(
    monkeypatch, new_total, expected
):
    issued = coupon(CouponStatusEnum.voided, voided_reason="venda_reaberta")
    expiry = issued.valid_until
    campaign = SimpleNamespace(
        id=3,
        tenant_id="tenant-a",
        campaign_type=CampaignTypeEnum.quick_repurchase,
        params={"min_purchase_value": 0, "coupon_value": 90, "cooldown_days": 0},
    )
    event = SimpleNamespace(
        id=10,
        event_type="purchase_completed",
        payload={"customer_id": 2, "venda_id": 9, "venda_total": new_total},
    )
    db = SimpleNamespace(query=lambda *a: Query([issued]))
    monkeypatch.setattr(quick_repurchase, "log_campaign_event", lambda **kw: None)
    monkeypatch.setattr(
        quick_repurchase,
        "create_coupon",
        lambda *a, **kw: pytest.fail("Nao deve duplicar cupom"),
    )

    result = quick_repurchase.QuickRepurchaseHandler().run(db, campaign, event)

    assert result["rewarded"] == expected
    assert issued.valid_until == expiry
    assert issued.discount_value == Decimal("25")
    assert (
        quick_repurchase.QuickRepurchaseHandler().run(db, campaign, event)["rewarded"]
        == 0
    )


@pytest.mark.parametrize(
    "status", [CouponStatusEnum.used, CouponStatusEnum.expired, CouponStatusEnum.voided]
)
def test_repeated_sale_never_replaces_used_expired_or_manually_voided_coupon(
    monkeypatch, status
):
    issued = coupon(status, voided_reason="manual")
    campaign = SimpleNamespace(
        id=3,
        tenant_id="tenant-a",
        campaign_type=CampaignTypeEnum.quick_repurchase,
        params={"cooldown_days": 0},
    )
    event = SimpleNamespace(
        id=10,
        event_type="purchase_completed",
        payload={"customer_id": 2, "venda_id": 9, "venda_total": 200},
    )
    db = SimpleNamespace(query=lambda *a: Query([issued]))
    monkeypatch.setattr(
        quick_repurchase,
        "create_coupon",
        lambda *a, **kw: pytest.fail("Nao deve duplicar cupom"),
    )

    assert (
        quick_repurchase.QuickRepurchaseHandler().run(db, campaign, event)["rewarded"]
        == 0
    )
    assert issued.status == status


def test_coupon_edit_flow_preserves_rows_and_isolates_tenants(
    db_session, tenant_context, monkeypatch
):
    tenant_a, tenant_b = uuid4(), uuid4()
    expiry = datetime.now(timezone.utc) + timedelta(days=2)
    for index, tenant in enumerate([tenant_a, tenant_b], start=1):
        tenant_context(tenant)
        db_session.execute(
            insert(Coupon).values(
                id=91000 + index,
                tenant_id=tenant,
                campaign_id=3,
                customer_id=2,
                code="VOLTE",
                coupon_type=CouponTypeEnum.fixed,
                discount_value=Decimal("25"),
                valid_until=expiry,
                status=CouponStatusEnum.active,
                meta={
                    "source_kind": "quick_repurchase",
                    "source_venda_id": 9,
                    "min_purchase_value_snapshot": "150",
                },
            )
        )
        db_session.flush()
    tenant_context(tenant_a)
    monkeypatch.setattr(sale_reopening_service, "log_campaign_event", lambda **kw: None)
    monkeypatch.setattr(quick_repurchase, "log_campaign_event", lambda **kw: None)
    monkeypatch.setattr(
        quick_repurchase,
        "create_coupon",
        lambda *a, **kw: pytest.fail("Nao deve duplicar cupom"),
    )

    assert (
        sale_reopening_service.void_quick_repurchase_coupons_for_sale(
            db_session, tenant_id=tenant_a, venda_id=9
        )
        == 1
    )
    db_session.flush()
    original = db_session.query(Coupon).filter(Coupon.id == 91001).one()
    original_expiry = original.valid_until
    assert original.status == CouponStatusEnum.voided
    campaign = SimpleNamespace(
        id=3,
        tenant_id=tenant_a,
        campaign_type=CampaignTypeEnum.quick_repurchase,
        params={"cooldown_days": 0},
    )
    event = SimpleNamespace(
        id=10,
        event_type="purchase_completed",
        payload={"customer_id": 2, "venda_id": 9, "venda_total": 100},
    )
    assert (
        quick_repurchase.QuickRepurchaseHandler().run(db_session, campaign, event)[
            "rewarded"
        ]
        == 0
    )
    event.payload["venda_total"] = 200
    assert (
        quick_repurchase.QuickRepurchaseHandler().run(db_session, campaign, event)[
            "rewarded"
        ]
        == 1
    )
    assert original.valid_until == original_expiry
    assert db_session.query(Coupon).count() == 1
    tenant_context(tenant_b)
    assert (
        db_session.query(Coupon).filter(Coupon.id == 91002).one().status
        == CouponStatusEnum.active
    )
