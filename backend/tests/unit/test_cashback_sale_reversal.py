"""Cancellation restores redeemed cashback with the original expiry dates."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.campaigns import cashback_sale_reversal
from app.campaigns.models import CampaignExecution, CashbackTransaction

NOW = datetime.now(timezone.utc)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def join(self, *args):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeDb:
    def __init__(self, redemption, credits):
        self.redemption = redemption
        self.credits = credits
        self.cashback_queries = 0
        self.added = []

    def query(self, model):
        if model is CashbackTransaction:
            self.cashback_queries += 1
            if self.cashback_queries == 1:
                return FakeQuery([self.redemption])
            if self.cashback_queries == 2:
                return FakeQuery(self.credits)
        if model is CampaignExecution:
            return FakeQuery([])
        return FakeQuery([])

    def add(self, row):
        self.added.append(row)

    def flush(self):
        pass


def test_cancelled_sale_refunds_only_its_redeemed_lots(monkeypatch):
    soon = NOW + timedelta(days=2)
    redemption = SimpleNamespace(id=20, amount=Decimal("-4.00"), created_at=NOW)
    credits = [
        SimpleNamespace(id=1, expires_at=soon),
        SimpleNamespace(id=2, expires_at=None),
    ]
    db = FakeDb(redemption, credits)
    monkeypatch.setattr(
        cashback_sale_reversal,
        "lock_cashback_customer",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        cashback_sale_reversal,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            allocations_by_debit={20: {1: Decimal("3.00"), 2: Decimal("1.00")}}
        ),
    )

    cashback_sale_reversal.reverse_cashback_for_sale(
        db, tenant_id="tenant-a", sale_id=99, customer_id=42
    )

    assert [(row.amount, row.expires_at, row.source_id) for row in db.added] == [
        (Decimal("3.00"), soon, 20),
        (Decimal("1.00"), None, 20),
    ]


def test_cancelled_sale_revokes_only_unspent_reward(monkeypatch):
    earned = SimpleNamespace(id=50, amount=Decimal("5.00"))

    class EarnedDb(FakeDb):
        def __init__(self):
            super().__init__(None, [])
            self.execution = SimpleNamespace(id=9, reward_meta={})

        def query(self, model):
            if model is CashbackTransaction:
                self.cashback_queries += 1
                return FakeQuery([earned] if self.cashback_queries == 2 else [])
            if model is CampaignExecution:
                return FakeQuery([self.execution])
            return FakeQuery([])

    db = EarnedDb()
    monkeypatch.setattr(
        cashback_sale_reversal,
        "lock_cashback_customer",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        cashback_sale_reversal,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            allocations_by_debit={},
            remaining_by_credit={50: Decimal("1.00")},
        ),
    )

    cashback_sale_reversal.reverse_cashback_for_sale(
        db, tenant_id="tenant-a", sale_id=99, customer_id=42
    )

    assert len(db.added) == 1
    assert db.added[0].amount == Decimal("-1.00")
    assert db.added[0].source_id == 50
    assert db.execution.reward_meta["cashback_sale_revoked"] is True


def test_cancelled_sale_revokes_refund_descended_from_its_reward(monkeypatch):
    earned = SimpleNamespace(id=50, amount=Decimal("5.00"))
    refund = SimpleNamespace(id=60, amount=Decimal("4.00"), origin_credit_id=50)

    class DescendantDb(FakeDb):
        def __init__(self):
            super().__init__(None, [])
            self.execution = SimpleNamespace(id=9, reward_meta={})

        def query(self, model):
            if model is CashbackTransaction:
                self.cashback_queries += 1
                rows = {1: [], 2: [earned], 3: [refund]}.get(self.cashback_queries, [])
                return FakeQuery(rows)
            if model is CampaignExecution:
                return FakeQuery([self.execution])
            return FakeQuery([])

    db = DescendantDb()
    monkeypatch.setattr(
        cashback_sale_reversal, "lock_cashback_customer", lambda *a, **k: None
    )
    monkeypatch.setattr(
        cashback_sale_reversal,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            allocations_by_debit={},
            remaining_by_credit={50: Decimal("0.00"), 60: Decimal("4.00")},
        ),
    )

    cashback_sale_reversal.reverse_cashback_for_sale(
        db, tenant_id="tenant-a", sale_id=99, customer_id=42
    )

    assert [(row.amount, row.source_id) for row in db.added] == [(Decimal("-4.00"), 60)]
    assert db.execution.reward_meta["cashback_sale_revoked"] is True


def test_refund_does_not_recreate_reward_from_cancelled_sale(monkeypatch):
    redemption = SimpleNamespace(id=20, amount=Decimal("-4.00"), created_at=NOW)
    earned_credit = SimpleNamespace(
        id=50,
        amount=Decimal("4.00"),
        expires_at=None,
        source_type=cashback_sale_reversal.CashbackSourceTypeEnum.campaign,
        source_id=9,
        origin_credit_id=None,
    )

    class RevokedDb(FakeDb):
        def __init__(self):
            super().__init__(redemption, [earned_credit])
            self.execution_queries = 0

        def query(self, model):
            if model is CampaignExecution:
                self.execution_queries += 1
                return FakeQuery(
                    [SimpleNamespace(id=9, reward_meta={"cashback_sale_revoked": True})]
                    if self.execution_queries == 1
                    else []
                )
            return super().query(model)

    db = RevokedDb()
    monkeypatch.setattr(
        cashback_sale_reversal, "lock_cashback_customer", lambda *a, **k: None
    )
    monkeypatch.setattr(
        cashback_sale_reversal,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            allocations_by_debit={20: {50: Decimal("4.00")}},
        ),
    )

    cashback_sale_reversal.reverse_cashback_for_sale(
        db, tenant_id="tenant-a", sale_id=99, customer_id=42
    )

    assert len(db.added) == 1
    assert db.added[0].amount == Decimal("0.00")
    assert db.added[0].tx_type == "closed"
