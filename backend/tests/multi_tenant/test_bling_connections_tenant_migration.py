from __future__ import annotations

from app.db.sql_audit import TENANT_TABLES
from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import load_migration, migration_path


MIGRATION_FILE = migration_path("zxq20260829a1_bling_connections_per_tenant.py")


def test_bling_connections_migration_metadata_and_security_contract():
    migration = load_migration(MIGRATION_FILE)
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert migration["revision"] == "zxq20260829a1"
    assert migration["down_revision"] == "zxp20260829a1"
    assert migration["CONNECTIONS"] == "bling_connections"
    assert migration["COMPANY_LINKS"] == "bling_company_tenant_links"
    assert "ALTER TABLE {CONNECTIONS} ENABLE ROW LEVEL SECURITY" in source
    assert "ALTER TABLE {CONNECTIONS} FORCE ROW LEVEL SECURITY" in source
    assert "CREATE POLICY {POLICY}" in source


def test_bling_connections_are_tracked_by_raw_sql_guardrails():
    assert "bling_connections" in TENANT_SCOPED_TABLES
    assert "bling_connections" in TENANT_TABLES
