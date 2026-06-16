"""Fail if PostgreSQL has unexpected tenant_id tables without RLS."""

from __future__ import annotations

from app.db import SessionLocal
from app.tenancy.rls_no_debt import (
    assert_no_unexpected_no_rls_tables,
    tenant_id_tables_without_rls,
)


def main() -> int:
    with SessionLocal() as db:
        assert_no_unexpected_no_rls_tables(db)
        remaining = tenant_id_tables_without_rls(db)

    if remaining:
        print(
            "RLS no-debt OK. Intentional globals without RLS:",
            ", ".join(sorted(remaining)),
        )
    else:
        print("RLS no-debt OK. No tenant_id tables without RLS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
