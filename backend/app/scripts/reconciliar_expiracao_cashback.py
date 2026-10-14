"""Audita e compensa expirações de cashback acima do crédito não usado.

Dry-run por padrão. A aplicação exige tenant, contagem e total exatos do plano
revisado. O histórico é preservado com lançamentos positivos vinculados ao
débito de expiração original; nenhum crédito gastável novo é criado.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.campaigns.cashback_wallet import (
    get_cashback_wallet,
    lock_cashback_customer,
)
from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.db import SessionLocal
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant


@dataclass(frozen=True)
class Correction:
    customer_id: int
    credit_id: int
    expiration_id: int
    amount: Decimal


def _customer_corrections(db, *, tenant_id, customer_id, rows, now) -> list[Correction]:
    wallet = get_cashback_wallet(
        db, tenant_id=tenant_id, customer_id=customer_id, as_of=now
    )
    reversals = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
            CashbackTransaction.source_id.in_([row.id for row in rows]),
            CashbackTransaction.amount > 0,
        )
        .all()
    )
    corrected_by_expiration: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for reversal in reversals:
        corrected_by_expiration[reversal.source_id] += Decimal(str(reversal.amount))
    source_counts = Counter(row.source_id for row in rows)
    plan: list[Correction] = []
    for row in rows:
        if row.source_id is None:
            raise ValueError(f"Expiração {row.id} sem crédito de origem")
        if source_counts[row.source_id] != 1:
            raise ValueError(
                f"Crédito {row.source_id} com múltiplas expirações; revisão manual"
            )
        expected = wallet.expected_expiration_by_credit.get(
            row.source_id, Decimal("0.00")
        )
        posted = wallet.posted_expiration_by_credit.get(row.source_id, Decimal("0.00"))
        excess = posted - corrected_by_expiration[row.id] - expected
        if excess > 0:
            plan.append(Correction(customer_id, row.source_id, row.id, excess))
    return plan


def build_plan(db, *, tenant_id, as_of=None) -> list[Correction]:
    """Return only excess expiration amounts, without changing the database."""
    now = as_of or datetime.now(timezone.utc)
    expiration_rows = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.expiration,
            CashbackTransaction.amount < 0,
        )
        .all()
    )
    by_customer: dict[int, list] = defaultdict(list)
    for row in expiration_rows:
        by_customer[row.customer_id].append(row)
    plan: list[Correction] = []
    for customer_id, rows in sorted(by_customer.items()):
        plan.extend(
            _customer_corrections(
                db, tenant_id=tenant_id, customer_id=customer_id, rows=rows, now=now
            )
        )
    return sorted(plan, key=lambda item: item.expiration_id)


def reconcile(db, *, tenant_id, apply=False, expected_count=None, expected_total=None):
    """Prepare a reviewable plan, then recheck under locks before applying."""
    tenant = UUID(str(tenant_id))
    with tenant_context(tenant):
        sync_rls_tenant(db, tenant)
        plan = build_plan(db, tenant_id=tenant)
        total = sum((item.amount for item in plan), Decimal("0.00"))
        result = {
            "tenant_id": str(tenant),
            "count": len(plan),
            "total": str(total),
            "items": [
                {
                    "customer_id": item.customer_id,
                    "credit_id": item.credit_id,
                    "expiration_id": item.expiration_id,
                    "amount": str(item.amount),
                }
                for item in plan
            ],
            "applied": False,
        }
        if not apply:
            db.rollback()
            return result

        if expected_count is None or expected_total is None:
            raise ValueError("--apply exige --expected-count e --expected-total")
        if len(plan) != expected_count or total != expected_total:
            raise ValueError("Plano mudou desde a revisão; aplicação recusada")
        for customer_id in sorted({item.customer_id for item in plan}):
            lock_cashback_customer(db, tenant_id=tenant, customer_id=customer_id)
        if build_plan(db, tenant_id=tenant) != plan:
            raise ValueError("Plano mudou durante a trava; aplicação recusada")
        for item in plan:
            db.add(
                CashbackTransaction(
                    tenant_id=tenant,
                    customer_id=item.customer_id,
                    amount=item.amount,
                    source_type=CashbackSourceTypeEnum.reversal,
                    source_id=item.expiration_id,
                    tx_type="credit",
                    description=(
                        "Compensação do excesso de expiração do cashback "
                        f"#CBTX-{item.credit_id}"
                    ),
                )
            )
        db.commit()
        result["applied"] = True
        return result


def main() -> None:
    # Register all ORM models before a customer row lock configures mappers.
    # This command runs outside the API startup path, which normally does it.
    import app.main  # noqa: F401
    from sqlalchemy.orm import configure_mappers

    configure_mappers()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--expected-total", type=Decimal)
    args = parser.parse_args()
    with SessionLocal() as db:
        try:
            result = reconcile(
                db,
                tenant_id=args.tenant_id,
                apply=args.apply,
                expected_count=args.expected_count,
                expected_total=args.expected_total,
            )
        except Exception:
            db.rollback()
            raise
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
