"""A re-finalized sale cannot grant cashback already spent before reopening."""

from decimal import Decimal
from types import SimpleNamespace
import pytest

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
            id=8,
            reward_value=Decimal("10.00"),
            reward_meta={
                "cashback_sale_revoked": revoked,
                "percent": 10,
                "rank": "bronze",
                "venda_total_base": 100,
            },
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


@pytest.fixture(autouse=True)
def benefit_dependencies(monkeypatch):
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.remaining_sale_amount",
        lambda db, *, tenant_id, venda: Decimal(str(venda.total)),
    )
    monkeypatch.setattr(cashback_handler, "log_campaign_event", lambda **kwargs: None)


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
    assert db.execution.reward_value == Decimal("10.00")


@pytest.mark.parametrize(
    "new_total,expected_credit,expected_effective",
    [
        ("200.00", "16.00", "20.00"),
        ("50.00", "1.00", "5.00"),
        ("30.00", "0.00", "4.00"),
        ("0.00", "0.00", "4.00"),
    ],
)
def test_edited_sale_changes_only_its_remaining_cashback(
    monkeypatch, new_total, expected_credit, expected_effective
):
    db = Db(revoked=True)
    db.sale.total = Decimal(new_total)
    audit = []
    monkeypatch.setattr(
        cashback_handler, "log_campaign_event", lambda **kw: audit.append(kw)
    )
    monkeypatch.setattr(
        cashback_handler, "lock_cashback_customer", lambda *a, **k: None
    )
    monkeypatch.setattr(
        cashback_handler,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(expected_expiration_by_credit={}),
    )
    # Campaign settings may change while an old sale is being edited.
    campaign = SimpleNamespace(
        id=3, tenant_id="tenant-a", params={"bronze_percent": 50}
    )

    rewarded = cashback_handler.CashbackHandler()._process(db, campaign, 42, 99, 123)

    assert sum((row.amount for row in db.added), Decimal("0.00")) == Decimal(
        expected_credit
    )
    assert rewarded == int(Decimal(expected_credit) > 0)
    assert db.execution.reward_value == Decimal(expected_effective)
    assert db.execution.reward_meta["venda_total_base"] == float(new_total)
    assert db.execution.reward_meta["cashback_entitlement"] == float(
        Decimal(new_total) / 10
    )
    assert db.execution.reward_meta["cashback_sale_revoked"] is False
    assert audit[0]["tenant_id"] == "tenant-a"
    assert audit[0]["metadata"]["retained"] == 4.0
    assert audit[0]["metadata"]["consumed_excess"] == max(
        4.0 - float(Decimal(new_total) / 10), 0.0
    )
    assert (
        db.execution.reward_meta["cashback_consumed_excess"]
        == audit[0]["metadata"]["consumed_excess"]
    )
    assert cashback_handler.CashbackHandler()._process(db, campaign, 42, 99, 124) == 0


def test_duplicate_purchase_event_does_not_grant_twice(monkeypatch):
    db = Db(revoked=False)
    monkeypatch.setattr(
        cashback_handler, "lock_cashback_customer", lambda *a, **k: None
    )
    campaign = SimpleNamespace(id=3, tenant_id="tenant-a")

    rewarded = cashback_handler.CashbackHandler()._process(db, campaign, 42, 99, 123)

    assert rewarded == 0
    assert db.added == []


@pytest.mark.parametrize(
    "new_total,expected_credit", [("100", "0.00"), ("200", "10.00")]
)
def test_edit_does_not_renew_cashback_that_already_expired(
    monkeypatch, new_total, expected_credit
):
    db = Db(revoked=True)
    db.sale.total = Decimal(new_total)
    original_query = db.query
    db.query = lambda model: (
        Query([]) if model is CashbackTransaction.amount else original_query(model)
    )
    monkeypatch.setattr(
        cashback_handler, "lock_cashback_customer", lambda *a, **k: None
    )
    monkeypatch.setattr(
        cashback_handler,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            expected_expiration_by_credit={50: Decimal("10.00")}
        ),
    )
    campaign = SimpleNamespace(
        id=3, tenant_id="tenant-a", params={"bronze_percent": 10}
    )

    cashback_handler.CashbackHandler()._process(db, campaign, 42, 99, 123)

    assert sum((row.amount for row in db.added), Decimal("0.00")) == Decimal(
        expected_credit
    )
    assert db.execution.reward_meta["cashback_expired_before_recalculation"] == 10.0
    assert db.execution.reward_meta["cashback_consumed_excess"] == 0.0
