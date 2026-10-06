"""Behavioral regression tests for cashback lot accounting."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from random import Random
from types import SimpleNamespace

from app.campaigns.cashback_wallet import replay_cashback_transactions

BASE = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)


def tx(
    tx_id,
    amount,
    created_at,
    *,
    expires_at=None,
    source_type="campaign",
    source_id=None,
    tx_type=None,
):
    return SimpleNamespace(
        id=tx_id,
        amount=Decimal(str(amount)),
        created_at=created_at,
        expires_at=expires_at,
        source_type=source_type,
        source_id=source_id,
        tx_type=tx_type or ("credit" if Decimal(str(amount)) > 0 else "debit"),
    )


def wallet(rows, when):
    return replay_cashback_transactions(rows, as_of=when)


def test_new_cashback_rows_use_insert_clock_instead_of_transaction_start():
    from app.campaigns.models import CashbackTransaction

    default = CashbackTransaction.__table__.c.created_at.server_default
    assert str(default.arg).lower() == "clock_timestamp()"


def test_fully_redeemed_credit_has_nothing_to_expire():
    expiry = BASE + timedelta(days=2)
    rows = [
        tx(1, "7.00", BASE, expires_at=expiry),
        tx(2, "-7.00", BASE + timedelta(days=1), source_type="redemption"),
    ]

    result = wallet(rows, expiry)

    assert result.available == Decimal("0.00")
    assert result.remaining_by_credit == {1: Decimal("0.00")}
    assert result.expected_expiration_by_credit == {1: Decimal("0.00")}
    assert result.excess_debits == Decimal("0.00")


def test_partial_redemption_expires_only_unspent_remainder():
    expiry = BASE + timedelta(days=2)
    rows = [
        tx(1, "7.00", BASE, expires_at=expiry),
        tx(2, "-4.00", BASE + timedelta(days=1), source_type="redemption"),
    ]

    assert wallet(rows, expiry - timedelta(microseconds=1)).available == Decimal("3.00")
    result = wallet(rows, expiry)
    assert result.available == Decimal("0.00")
    assert result.expected_expiration_by_credit == {1: Decimal("3.00")}


def test_multiple_expiries_consume_soonest_expiring_credit_first():
    early = BASE + timedelta(days=2)
    late = BASE + timedelta(days=20)
    rows = [
        tx(1, "5.00", BASE, expires_at=late),
        tx(2, "7.00", BASE + timedelta(hours=1), expires_at=early),
        tx(3, "-9.00", BASE + timedelta(days=1), source_type="redemption"),
    ]

    result = wallet(rows, early)

    assert result.remaining_by_credit == {
        1: Decimal("3.00"),
        2: Decimal("0.00"),
    }
    assert result.expected_expiration_by_credit == {2: Decimal("0.00")}
    assert result.available == Decimal("3.00")
    assert result.allocations_by_debit[3] == {
        2: Decimal("7.00"),
        1: Decimal("2.00"),
    }


def test_insert_order_preserves_credit_before_debit_with_legacy_backdated_timestamp():
    # PostgreSQL now() records transaction start. The debit transaction may
    # start first yet INSERT after the credit transaction has committed.
    rows = [
        tx(1, "7.00", BASE + timedelta(hours=1)),
        tx(2, "-3.00", BASE, source_type="redemption"),
    ]

    result = wallet(rows, BASE + timedelta(hours=2))

    assert result.available == Decimal("4.00")
    assert result.excess_debits == Decimal("0.00")
    assert result.allocations_by_debit == {2: {1: Decimal("3.00")}}
    assert result.balance_by_transaction == {
        1: Decimal("7.00"),
        2: Decimal("4.00"),
    }
    assert result.effective_time_by_transaction == {
        1: BASE + timedelta(hours=1),
        2: BASE + timedelta(hours=1),
    }


def test_never_expiring_lot_survives_expiration_of_other_lot():
    expiry = BASE + timedelta(days=1)
    rows = [
        tx(1, "5.00", BASE, expires_at=None),
        tx(2, "3.00", BASE + timedelta(minutes=1), expires_at=expiry),
    ]

    result = wallet(rows, expiry + timedelta(days=1))

    assert result.available == Decimal("5.00")
    assert result.expected_expiration_by_credit == {2: Decimal("3.00")}


def test_same_expiry_uses_created_at_then_id_to_break_ties():
    expiry = BASE + timedelta(days=2)
    rows = [
        tx(2, "3.00", BASE, expires_at=expiry),
        tx(1, "2.00", BASE, expires_at=expiry),
        tx(3, "-2.50", BASE + timedelta(days=1), source_type="redemption"),
    ]

    result = wallet(rows, BASE + timedelta(days=1))

    assert result.remaining_by_credit == {
        1: Decimal("0.00"),
        2: Decimal("2.50"),
    }


def test_expiration_occurs_at_exact_instant_not_start_of_day():
    expiry = datetime(2026, 10, 3, 20, 45, tzinfo=timezone.utc)
    rows = [tx(1, "7.00", BASE, expires_at=expiry)]

    assert wallet(rows, expiry - timedelta(microseconds=1)).available == Decimal("7.00")
    assert wallet(rows, expiry).available == Decimal("0.00")
    assert wallet(rows, expiry).expected_expiration_by_credit[1] == Decimal("7.00")


def test_redemption_at_exact_expiry_cannot_consume_expired_lot():
    expiry = BASE + timedelta(days=1)
    rows = [
        tx(1, "7.00", BASE, expires_at=expiry),
        tx(2, "-1.00", expiry, source_type="redemption"),
    ]

    result = wallet(rows, expiry)

    assert result.expected_expiration_by_credit == {1: Decimal("7.00")}
    assert result.available == Decimal("0.00")
    assert result.excess_debits == Decimal("1.00")


def test_late_job_does_not_keep_expired_credit_spendable():
    expiry = BASE + timedelta(days=1)
    rows = [
        tx(1, "7.00", BASE, expires_at=expiry),
        tx(2, "-2.00", expiry + timedelta(hours=1), source_type="redemption"),
        tx(
            3,
            "-7.00",
            expiry + timedelta(days=1),
            source_type="expiration",
            source_id=1,
            tx_type="expired",
        ),
    ]

    result = wallet(rows, expiry + timedelta(days=2))

    assert result.available == Decimal("0.00")
    assert result.expected_expiration_by_credit == {1: Decimal("7.00")}
    assert result.posted_expiration_by_credit == {1: Decimal("7.00")}
    assert result.excess_debits == Decimal("2.00")


def test_credit_reversal_takes_only_its_unspent_amount():
    rows = [
        tx(1, "7.00", BASE),
        tx(2, "5.00", BASE + timedelta(minutes=1)),
        tx(3, "-4.00", BASE + timedelta(minutes=2), source_type="redemption"),
        tx(
            4,
            "-7.00",
            BASE + timedelta(minutes=3),
            source_type="reversal",
            source_id=1,
        ),
    ]

    result = wallet(rows, BASE + timedelta(minutes=4))

    assert result.remaining_by_credit == {
        1: Decimal("0.00"),
        2: Decimal("5.00"),
    }
    assert result.excess_debits == Decimal("4.00")


def test_premature_and_excessive_expiration_entries_do_not_reduce_wallet_twice():
    expiry = BASE + timedelta(days=2, hours=8)
    rows = [
        tx(1, "7.00", BASE, expires_at=expiry),
        tx(2, "-4.00", BASE + timedelta(days=1), source_type="redemption"),
        tx(
            3,
            "-7.00",
            expiry - timedelta(hours=2),
            source_type="expiration",
            source_id=1,
            tx_type="expired",
        ),
    ]

    before_expiry = wallet(rows, expiry - timedelta(hours=1))
    assert before_expiry.available == Decimal("3.00")
    assert before_expiry.expected_expiration_by_credit == {}
    assert before_expiry.posted_expiration_by_credit == {1: Decimal("7.00")}
    assert before_expiry.balance_by_transaction[3] == Decimal("3.00")

    after_expiry = wallet(rows, expiry)
    assert after_expiry.available == Decimal("0.00")
    assert after_expiry.expected_expiration_by_credit == {1: Decimal("3.00")}
    assert after_expiry.posted_expiration_by_credit[
        1
    ] - after_expiry.expected_expiration_by_credit[1] == Decimal("4.00")


def test_positive_reversal_of_bad_expiration_is_audit_only():
    expiry = BASE + timedelta(days=2)
    rows = [
        tx(1, "7.00", BASE, expires_at=expiry),
        tx(2, "-7.00", BASE + timedelta(days=1), source_type="redemption"),
        tx(
            3,
            "-7.00",
            expiry + timedelta(hours=1),
            source_type="expiration",
            source_id=1,
            tx_type="expired",
        ),
        tx(
            4,
            "7.00",
            expiry + timedelta(hours=2),
            source_type="reversal",
            source_id=3,
        ),
    ]

    result = wallet(rows, expiry + timedelta(hours=3))

    assert result.available == Decimal("0.00")
    assert result.expected_expiration_by_credit == {1: Decimal("0.00")}
    assert result.posted_expiration_by_credit == {1: Decimal("7.00")}


def test_zero_expiration_marker_is_recorded_without_reducing_balance():
    expiry = BASE + timedelta(days=1)
    rows = [
        tx(1, "7.00", BASE, expires_at=expiry),
        tx(2, "-7.00", BASE + timedelta(hours=1), source_type="redemption"),
        tx(
            3,
            "0.00",
            expiry + timedelta(hours=1),
            source_type="expiration",
            source_id=1,
            tx_type="closed",
        ),
    ]

    result = wallet(rows, expiry + timedelta(hours=2))

    assert result.expected_expiration_by_credit == {1: Decimal("0.00")}
    assert result.posted_expiration_by_credit == {1: Decimal("0.00")}
    assert result.available == Decimal("0.00")
    assert result.balance_by_transaction[3] == Decimal("0.00")


def test_manual_overdraft_is_reported_without_negative_available_balance():
    rows = [
        tx(1, "1.00", BASE, source_type="manual"),
        tx(2, "-2.00", BASE + timedelta(minutes=1), source_type="manual"),
    ]

    result = wallet(rows, BASE + timedelta(minutes=2))

    assert result.available == Decimal("0.00")
    assert result.excess_debits == Decimal("1.00")


def test_fefo_heap_matches_simple_reference_across_deterministic_ledgers():
    rng = Random(20261005)

    def reference(rows, as_of):
        remaining = {}
        expiries = {}
        credit_times = {}
        expected = {}
        posted = {}
        allocations = {}
        balances = {}
        excess = Decimal("0.00")

        def expire(instant):
            for credit_id, expiry in expiries.items():
                if (
                    expiry is not None
                    and expiry <= instant
                    and credit_id not in expected
                ):
                    expected[credit_id] = remaining[credit_id]
                    remaining[credit_id] = Decimal("0.00")

        for item in rows:
            expire(item.created_at)
            amount = item.amount
            if item.source_type == "expiration":
                posted[item.source_id] = (
                    posted.get(item.source_id, Decimal("0.00")) - amount
                )
            elif amount > 0:
                remaining[item.id] = amount
                expiries[item.id] = item.expires_at
                credit_times[item.id] = item.created_at
                expire(item.created_at)
            elif amount < 0:
                needed = -amount
                if item.source_type == "reversal":
                    consumed = min(
                        needed, remaining.get(item.source_id, Decimal("0.00"))
                    )
                    remaining[item.source_id] -= consumed
                    excess += needed - consumed
                else:
                    for credit_id in sorted(
                        remaining,
                        key=lambda cid: (
                            expiries[cid] or datetime.max.replace(tzinfo=timezone.utc),
                            credit_times[cid],
                            cid,
                        ),
                    ):
                        consumed = min(needed, remaining[credit_id])
                        if consumed:
                            remaining[credit_id] -= consumed
                            needed -= consumed
                            allocations.setdefault(item.id, {})[credit_id] = consumed
                        if needed == 0:
                            break
                    excess += needed
            balances[item.id] = sum(remaining.values(), Decimal("0.00"))

        expire(as_of)
        return remaining, expected, posted, excess, allocations, balances

    for _ in range(300):
        rows = []
        credit_ids = []
        for item_id in range(1, rng.randint(12, 35)):
            created = BASE + timedelta(minutes=item_id)
            choice = rng.random()
            amount = Decimal(rng.randint(1, 2000)) / 100
            if choice < 0.45 or not credit_ids:
                expiry = (
                    created + timedelta(minutes=rng.randint(1, 20))
                    if rng.random() < 0.75
                    else None
                )
                rows.append(tx(item_id, amount, created, expires_at=expiry))
                credit_ids.append(item_id)
            elif choice < 0.83:
                rows.append(tx(item_id, -amount, created, source_type="redemption"))
            elif choice < 0.94:
                rows.append(
                    tx(
                        item_id,
                        -amount,
                        created,
                        source_type="reversal",
                        source_id=rng.choice(credit_ids),
                    )
                )
            else:
                rows.append(
                    tx(
                        item_id,
                        -amount,
                        created,
                        source_type="expiration",
                        source_id=rng.choice(credit_ids),
                        tx_type="expired",
                    )
                )

        as_of = BASE + timedelta(minutes=60)
        result = wallet(rows, as_of)
        remaining, expected, posted, excess, allocations, balances = reference(
            rows, as_of
        )
        assert result.remaining_by_credit == remaining
        assert result.expected_expiration_by_credit == expected
        assert result.posted_expiration_by_credit == posted
        assert result.excess_debits == excess
        assert result.allocations_by_debit == allocations
        assert result.balance_by_transaction == balances
        assert result.available == sum(remaining.values(), Decimal("0.00"))
