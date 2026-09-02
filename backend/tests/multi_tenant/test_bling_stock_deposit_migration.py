from __future__ import annotations

from tests.multi_tenant.rls_migration_helpers import load_migration, migration_path


MIGRATION_FILE = migration_path("zyv20260830a1_bling_stock_deposit_per_tenant.py")


def test_bling_stock_deposit_migration_contract():
    migration = load_migration(MIGRATION_FILE)
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert migration["revision"] == "zyv20260830a1"
    assert migration["down_revision"] == "zyu20260830a1"
    assert migration["CONNECTIONS"] == "bling_connections"
    assert migration["COLUMN"] == "stock_deposit_id"
    assert "sa.BigInteger()" in source
