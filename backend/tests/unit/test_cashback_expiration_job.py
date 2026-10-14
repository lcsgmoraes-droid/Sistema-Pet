"""The expiration job posts only the balance left in a due credit."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401 -- registra relacionamentos ORM para teste SQLite
from app.campaigns import cashback_wallet, scheduler_cashback
from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.tenancy.context import clear_current_tenant, set_current_tenant

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


class FakeQuery:
    def __init__(self, db, target):
        self.db = db
        self.target = target

    def filter(self, *args):
        return self

    def first(self):
        if self.target is CashbackTransaction.id and self.db.added:
            return SimpleNamespace(id=1)
        return None


class FakeDb:
    def __init__(self):
        self.added = []

    def query(self, *args):
        return FakeQuery(self, args[0])

    def add(self, row):
        self.added.append(row)

    def flush(self):
        pass


def _run(monkeypatch, remaining, expiry, *, attempts=1):
    db = FakeDb()
    tenant = SimpleNamespace(id="tenant-a")
    credit = SimpleNamespace(id=17, customer_id=42, expires_at=expiry)
    monkeypatch.setattr(cashback_wallet, "lock_cashback_customer", lambda *a, **k: None)
    monkeypatch.setattr(
        cashback_wallet,
        "get_cashback_wallet",
        lambda *a, **k: SimpleNamespace(
            expected_expiration_by_credit={17: Decimal(remaining)}
        ),
    )
    posted = [
        scheduler_cashback._expire_cashback_credit_if_needed(
            db, tenant, credit, now_utc=NOW
        )
        for _ in range(attempts)
    ]
    return posted, db.added


def test_job_posts_only_unspent_part_of_due_credit(monkeypatch):
    posted, rows = _run(monkeypatch, "3.00", NOW - timedelta(seconds=1), attempts=2)
    assert posted == [True, False]
    assert len(rows) == 1
    assert rows[0].amount == Decimal("-3.00")
    assert rows[0].source_id == 17


def test_job_closes_fully_spent_credit_once_without_expiring_balance(monkeypatch):
    posted, rows = _run(monkeypatch, "0.00", NOW - timedelta(seconds=1), attempts=2)
    assert posted == [False, False]
    assert len(rows) == 1
    assert rows[0].amount == Decimal("0.00")
    assert rows[0].tx_type == "closed"
    assert "sem expiração de saldo" in rows[0].description
    assert rows[0].source_id == 17


def test_job_does_not_expire_before_exact_time(monkeypatch):
    posted, rows = _run(monkeypatch, "7.00", NOW + timedelta(seconds=1))
    assert posted == [False]
    assert rows == []


def test_due_query_catches_backlog_without_revisiting_processed_credits():
    tenant_id = uuid.uuid4()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    CashbackTransaction.__table__.create(engine)
    common = {
        "tenant_id": tenant_id,
        "customer_id": 42,
        "created_at": NOW - timedelta(days=5),
    }
    rows = [
        {
            "id": 1,
            "amount": Decimal("3.00"),
            "source_type": CashbackSourceTypeEnum.campaign,
            "tx_type": "credit",
            "expires_at": NOW - timedelta(days=3),
        },
        {
            "id": 2,
            "amount": Decimal("2.00"),
            "source_type": CashbackSourceTypeEnum.campaign,
            "tx_type": "credit",
            "expires_at": NOW - timedelta(days=1),
        },
        {
            "id": 3,
            "amount": Decimal("0.00"),
            "source_type": CashbackSourceTypeEnum.expiration,
            "source_id": 2,
            "tx_type": "closed",
        },
    ]
    with engine.begin() as conn:
        for row in rows:
            conn.execute(CashbackTransaction.__table__.insert().values(**common, **row))

    set_current_tenant(tenant_id)
    try:
        with Session(engine) as db:
            pending = scheduler_cashback._cashback_credits_expiring_today(
                db, tenant_id, NOW
            )
            assert [tx.id for tx in pending] == [1]

            db.execute(
                CashbackTransaction.__table__.insert().values(
                    **common,
                    id=4,
                    amount=Decimal("-3.00"),
                    source_type=CashbackSourceTypeEnum.expiration,
                    source_id=1,
                    tx_type="expired",
                )
            )
            assert (
                scheduler_cashback._cashback_credits_expiring_today(db, tenant_id, NOW)
                == []
            )
    finally:
        clear_current_tenant()
