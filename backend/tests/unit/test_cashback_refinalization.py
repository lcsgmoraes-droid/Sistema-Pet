"""A re-finalized sale cannot grant cashback already spent before reopening."""

from decimal import Decimal
from types import SimpleNamespace

import app.financeiro_models  # noqa: F401 - registers Venda's mapped relationships
import app.produtos_models  # noqa: F401 - registers VendaItem's mapped relationships
from app.campaigns.handlers import cashback as cashback_handler
from app.campaigns.models import (
    CampaignExecution,
    CashbackTransaction,
    CustomerRankHistory,
)
from app.models import Cliente
from app.vendas_models import Venda


class Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def with_for_update(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class Db:
    def __init__(self, revoked):
        self.execution = SimpleNamespace(
            id=8, reward_meta={"cashback_sale_revoked": revoked}
        )
        self.sale = SimpleNamespace(
            id=99, cliente_id=42, status="finalizada", total=Decimal("100.00")
        )
        self.prior = SimpleNamespace(id=50, amount=Decimal("10.00"))
        self.added = []
        self.cashback_queries = 0

    def query(self, model):
        if model is Venda:
            return Query([self.sale])
        if model is CampaignExecution:
            return Query([self.execution])
        if model is CustomerRankHistory:
            return Query([])
        if model is CashbackTransaction:
            self.cashback_queries += 1
            return Query([self.prior] if self.cashback_queries == 1 else [])
        if model is CashbackTransaction.amount:
            return Query([(Decimal("-6.00"),)])
        if model is Cliente:
            return Query([])
        raise AssertionError(f"Unexpected query: {model}")

    def add(self, row):
        self.added.append(row)

    def flush(self):
        pass


def test_refinalization_grants_only_the_part_revoked_on_reopen(monkeypatch):
    db = Db(revoked=True)
    monkeypatch.setattr(
        cashback_handler, "lock_cashback_customer", lambda *a, **k: None
    )
    monkeypatch.setattr(
        cashback_handler,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(expected_expiration_by_credit={}),
    )
    campaign = SimpleNamespace(
        id=3, tenant_id="tenant-a", params={"bronze_percent": 10}
    )

    rewarded = cashback_handler.CashbackHandler()._process(db, campaign, 42, 99, 123)

    assert rewarded == 1
    assert len(db.added) == 1
    assert db.added[0].amount == Decimal("6.00")
    assert db.execution.reward_meta["cashback_sale_revoked"] is False


def test_duplicate_purchase_event_does_not_grant_twice(monkeypatch):
    db = Db(revoked=False)
    monkeypatch.setattr(
        cashback_handler, "lock_cashback_customer", lambda *a, **k: None
    )
    campaign = SimpleNamespace(id=3, tenant_id="tenant-a")

    rewarded = cashback_handler.CashbackHandler()._process(db, campaign, 42, 99, 123)

    assert rewarded == 0
    assert db.added == []
