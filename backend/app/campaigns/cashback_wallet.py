"""Deterministic, read-only replay of a customer's cashback ledger.

Credits are lots. Ordinary debits consume the active lot with the nearest
expiration first, then the oldest credit. Expiration entries in the ledger are
audit records: the clock expires the remaining lot exactly once, even if the
scheduled job posted an entry early, late, or for the wrong amount.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
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


@dataclass
class _ReplayState:
    by_id: dict[int, object]
    remaining: dict[int, Decimal] = field(default_factory=dict)
    spendable_heap: list[tuple[datetime, datetime, int]] = field(default_factory=list)
    expiration_heap: list[tuple[datetime, int]] = field(default_factory=list)
    expected: dict[int, Decimal] = field(default_factory=dict)
    posted: dict[int, Decimal] = field(default_factory=dict)
    allocations: dict[int, dict[int, Decimal]] = field(default_factory=dict)
    balances: dict[int, Decimal] = field(default_factory=dict)
    effective_times: dict[int, datetime] = field(default_factory=dict)
    excess: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")
    last_insert_time: datetime | None = None

    def expire_due(self, instant: datetime) -> None:
        while self.expiration_heap and self.expiration_heap[0][0] <= instant:
            _, credit_id = heappop(self.expiration_heap)
            unspent = self.remaining[credit_id]
            self.expected[credit_id] = unspent
            self.balance -= unspent
            self.remaining[credit_id] = Decimal("0.00")

    def _advance_time(self, tx: object) -> datetime:
        event_time = _utc(tx.created_at)
        if self.last_insert_time is not None:
            event_time = max(event_time, self.last_insert_time)
        self.expire_due(event_time)
        self.last_insert_time = event_time
        self.effective_times[int(tx.id)] = event_time
        return event_time

    def _record_expiration(self, amount: Decimal, source_id: int | None) -> None:
        if amount <= 0 and source_id is not None:
            self.posted[source_id] = (
                self.posted.get(source_id, Decimal("0.00")) - amount
            )

    def _is_expiration_reversal(
        self, amount: Decimal, source_type: str, source_id: int | None
    ) -> bool:
        if amount <= 0 or source_type != "reversal" or source_id is None:
            return False
        origin = self.by_id.get(source_id)
        return origin is not None and _source_type(origin) == "expiration"

    def _credit(self, tx: object, amount: Decimal, event_time: datetime) -> None:
        credit_id = int(tx.id)
        expiry_value = getattr(tx, "expires_at", None)
        expiry = _utc(expiry_value) if expiry_value is not None else None
        self.remaining[credit_id] = amount
        self.balance += amount
        heappush(self.spendable_heap, (expiry or _NO_EXPIRATION, event_time, credit_id))
        if expiry is not None:
            heappush(self.expiration_heap, (expiry, credit_id))
            self.expire_due(event_time)

    def _consume_reversal(self, source_id: int, amount: Decimal) -> None:
        # Revoking a partly used reward cannot take unrelated credits.
        active = self.remaining.get(source_id, Decimal("0.00"))
        consumed = min(amount, active)
        if consumed:
            self.remaining[source_id] = active - consumed
            self.balance -= consumed
        self.excess += amount - consumed

    def _consume_fefo(self, debit_id: int, amount: Decimal) -> None:
        to_consume = amount
        while to_consume > 0 and self.spendable_heap:
            lot = heappop(self.spendable_heap)
            credit_id = lot[2]
            active = self.remaining[credit_id]
            if active <= 0:
                continue
            consumed = min(to_consume, active)
            self.remaining[credit_id] = active - consumed
            self.balance -= consumed
            to_consume -= consumed
            self.allocations.setdefault(debit_id, {})[credit_id] = consumed
            if self.remaining[credit_id] > 0:
                heappush(self.spendable_heap, lot)
        self.excess += to_consume

    def apply(self, tx: object) -> None:
        event_time = self._advance_time(tx)
        amount = _money(tx.amount)
        source_type = _source_type(tx)
        source_id = getattr(tx, "source_id", None)
        source_id = int(source_id) if source_id is not None else None
        if source_type == "expiration":
            self._record_expiration(amount, source_id)
        elif self._is_expiration_reversal(amount, source_type, source_id):
            pass  # Compensation fixes ledger arithmetic, not spendable credit.
        elif amount > 0:
            self._credit(tx, amount, event_time)
        elif amount < 0 and source_type == "reversal" and source_id is not None:
            self._consume_reversal(source_id, -amount)
        elif amount < 0:
            self._consume_fefo(int(tx.id), -amount)
        self.balances[int(tx.id)] = self.balance

    def wallet(self) -> CashbackWallet:
        return CashbackWallet(
            available=self.balance,
            remaining_by_credit=self.remaining,
            expected_expiration_by_credit=self.expected,
            posted_expiration_by_credit=self.posted,
            excess_debits=self.excess,
            allocations_by_debit=self.allocations,
            balance_by_transaction=self.balances,
            effective_time_by_transaction=self.effective_times,
        )


def replay_cashback_transactions(
    transactions: Iterable[object], *, as_of: datetime | None = None
) -> CashbackWallet:
    """Replay a customer ledger through ``as_of`` without double expiration.

    BIGSERIAL ids preserve INSERT order even when a legacy ``created_at=now()``
    predates a credit committed before a later debit was inserted. Historical
    event times are clamped to that causal order; new rows use the INSERT clock.
    """
    cutoff = _utc(as_of or datetime.now(timezone.utc))
    rows = [tx for tx in transactions if _utc(tx.created_at) <= cutoff]
    rows.sort(key=lambda tx: int(tx.id))
    state = _ReplayState(by_id={int(tx.id): tx for tx in rows})
    for tx in rows:
        state.apply(tx)
    state.expire_due(cutoff)
    return state.wallet()


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
