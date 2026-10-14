"""Historical repair plans compensate only the excess already posted."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.scripts import reconciliar_expiracao_cashback as repair


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, expiration, reversals):
        self.expiration = expiration
        self.reversals = reversals
        self.calls = 0

    def query(self, *args):
        self.calls += 1
        return FakeQuery([self.expiration] if self.calls == 1 else self.reversals)


def test_repair_plan_subtracts_existing_compensation(monkeypatch):
    expiration = SimpleNamespace(
        id=1754,
        customer_id=11752,
        source_id=24,
        amount=Decimal("-7.00"),
    )
    reversal = SimpleNamespace(source_id=1754, amount=Decimal("2.00"))
    monkeypatch.setattr(
        repair,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            expected_expiration_by_credit={24: Decimal("0.00")},
            posted_expiration_by_credit={24: Decimal("7.00")},
        ),
    )

    plan = repair.build_plan(
        FakeDb(expiration, [reversal]),
        tenant_id="tenant-a",
        as_of=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )

    assert plan == [repair.Correction(11752, 24, 1754, Decimal("5.00"))]
