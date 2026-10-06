"""Deterministic, read-only replay of a customer's cashback ledger.

Credits are lots. Ordinary debits consume the active lot with the nearest
expiration first, then the oldest credit. Expiration entries in the ledger are
audit records: the clock expires the remaining lot exactly once, even if the
scheduled job posted an entry early, late, or for the wrong amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from heapq import heappop, heappush
from typing import Iterable

_CENT = Decimal("0.01")
_NO_EXPIRATION = datetime.max.replace(tzinfo=timezone.utc)


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(_CENT)


def _utc(value: datetime) -> datetime:
    # PostgreSQL's timestamptz is aware; accepting naive UTC values also makes
    # replay possible for older fixtures and imported ledger rows.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _source_type(tx: object) -> str:
    source = getattr(tx, "source_type", None)
    return str(getattr(source, "value", source) or "")


@dataclass(frozen=True)
class CashbackWallet:
    available: Decimal
    remaining_by_credit: dict[int, Decimal]
    expected_expiration_by_credit: dict[int, Decimal]
    posted_expiration_by_credit: dict[int, Decimal]
    excess_debits: Decimal
    allocations_by_debit: dict[int, dict[int, Decimal]]
    balance_by_transaction: dict[int, Decimal]
    effective_time_by_transaction: dict[int, datetime]


def replay_cashback_transactions(
    transactions: Iterable[object], *, as_of: datetime | None = None
) -> CashbackWallet:
    """Replay transactions through ``as_of`` without trusting expiration debits.

    ``expected_expiration_by_credit`` records the amount left when each lot
    actually reached its expiry. ``posted_expiration_by_credit`` records what
    the scheduler posted, including premature and excessive entries. Both
    amounts are positive. A linked credit reversal can consume only that
    credit's unspent portion; its excess is reported instead of taking funds
    from another lot.
    """
    cutoff = _utc(as_of or datetime.now(timezone.utc))
    rows = [tx for tx in transactions if _utc(tx.created_at) <= cutoff]
    # BIGSERIAL ids follow INSERT order. A legacy created_at=now() records the
    # transaction start, which can precede a credit committed before this
    # debit was inserted. Sorting by created_at would invert that causality.
    rows.sort(key=lambda tx: int(tx.id))
    by_id = {int(tx.id): tx for tx in rows}
    remaining: dict[int, Decimal] = {}
    spendable_heap: list[tuple[datetime, datetime, int]] = []
    expiration_heap: list[tuple[datetime, int]] = []
    expected: dict[int, Decimal] = {}
    posted: dict[int, Decimal] = {}
    excess = Decimal("0.00")
    allocations: dict[int, dict[int, Decimal]] = {}
    balances: dict[int, Decimal] = {}
    effective_times: dict[int, datetime] = {}
    balance = Decimal("0.00")

    def expire_due(instant: datetime) -> None:
        nonlocal balance
        while expiration_heap and expiration_heap[0][0] <= instant:
            _, credit_id = heappop(expiration_heap)
            expected[credit_id] = remaining[credit_id]
            balance -= remaining[credit_id]
            remaining[credit_id] = Decimal("0.00")

    # Clamp retrograde legacy timestamps to the previous INSERT. This repairs
    # a debit ordered before its funding credit by transaction-start time. An
    # exact historical INSERT instant lost by now() cannot be reconstructed;
    # the new clock_timestamp() default prevents that ambiguity going forward.
    last_insert_time: datetime | None = None
    for tx in rows:
        tx_id = int(tx.id)
        event_time = _utc(tx.created_at)
        if last_insert_time is not None:
            event_time = max(event_time, last_insert_time)
        expire_due(event_time)
        last_insert_time = event_time
        effective_times[tx_id] = event_time

        amount = _money(tx.amount)
        source_type = _source_type(tx)
        source_id = getattr(tx, "source_id", None)
        source_id = int(source_id) if source_id is not None else None

        if source_type == "expiration":
            if amount <= 0 and source_id is not None:
                posted[source_id] = posted.get(source_id, Decimal("0.00")) - amount
            balances[tx_id] = balance
            continue

        # A positive reversal of a bad expiration repairs the append-only
        # ledger's arithmetic. It does not create another spendable credit.
        if amount > 0 and source_type == "reversal" and source_id is not None:
            origin = by_id.get(source_id)
            if origin is not None and _source_type(origin) == "expiration":
                balances[tx_id] = balance
                continue

        if amount > 0:
            expiry_value = getattr(tx, "expires_at", None)
            expiry = _utc(expiry_value) if expiry_value is not None else None
            remaining[tx_id] = amount
            balance += amount
            heappush(spendable_heap, (expiry or _NO_EXPIRATION, event_time, tx_id))
            if expiry is not None:
                heappush(expiration_heap, (expiry, tx_id))
                expire_due(event_time)
            balances[tx_id] = balance
            continue

        if amount >= 0:
            balances[tx_id] = balance
            continue

        to_consume = -amount
        if source_type == "reversal" and source_id is not None:
            # A campaign reward revoked after partial use cannot claw the
            # already redeemed amount back from unrelated credits.
            active = remaining.get(source_id, Decimal("0.00"))
            consumed = min(to_consume, active)
            if consumed:
                remaining[source_id] = active - consumed
                balance -= consumed
            excess += to_consume - consumed
            balances[tx_id] = balance
            continue

        while to_consume > 0 and spendable_heap:
            lot = heappop(spendable_heap)
            credit_id = lot[2]
            active = remaining[credit_id]
            if active <= 0:
                continue
            consumed = min(to_consume, active)
            remaining[credit_id] = active - consumed
            balance -= consumed
            to_consume -= consumed
            allocations.setdefault(tx_id, {})[credit_id] = consumed
            if remaining[credit_id] > 0:
                heappush(spendable_heap, lot)
        excess += to_consume
        balances[tx_id] = balance

    expire_due(cutoff)

    return CashbackWallet(
        available=balance,
        remaining_by_credit=remaining,
        expected_expiration_by_credit=expected,
        posted_expiration_by_credit=posted,
        excess_debits=excess,
        allocations_by_debit=allocations,
        balance_by_transaction=balances,
        effective_time_by_transaction=effective_times,
    )


def get_cashback_wallet(db, *, tenant_id, customer_id, as_of=None) -> CashbackWallet:
    """Load one tenant/customer ledger and compute the wallet as of a UTC time."""
    from app.campaigns.models import CashbackTransaction

    cutoff = _utc(as_of or datetime.now(timezone.utc))
    transactions = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.created_at <= cutoff,
        )
        .order_by(CashbackTransaction.id)
        .all()
    )
    return replay_cashback_transactions(transactions, as_of=cutoff)


def get_tenant_cashback_liability(db, *, tenant_id, as_of=None) -> Decimal:
    """Total of spendable balances across the tenant's customer wallets."""
    from app.campaigns.models import CashbackTransaction

    cutoff = _utc(as_of or datetime.now(timezone.utc))
    transactions = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.created_at <= cutoff,
        )
        .order_by(CashbackTransaction.customer_id, CashbackTransaction.id)
        .all()
    )
    by_customer = defaultdict(list)
    for tx in transactions:
        by_customer[tx.customer_id].append(tx)
    return sum(
        (
            replay_cashback_transactions(rows, as_of=cutoff).available
            for rows in by_customer.values()
        ),
        Decimal("0.00"),
    )


def lock_cashback_customer(db, *, tenant_id, customer_id):
    """Serialize all balance-changing operations for a customer.

    Call inside the same database transaction, before reading the wallet or
    inserting any cashback debit. The caller owns the commit/rollback.
    """
    from app.models import Cliente

    customer = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.id == customer_id)
        .with_for_update()
        .first()
    )
    if customer is None:
        raise LookupError(f"Cliente {customer_id} não encontrado no tenant {tenant_id}")
    return customer


__all__ = [
    "CashbackWallet",
    "get_cashback_wallet",
    "get_tenant_cashback_liability",
    "lock_cashback_customer",
    "replay_cashback_transactions",
]
