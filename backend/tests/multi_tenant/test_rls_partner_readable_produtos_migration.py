from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    capture_migration_sql,
    load_migration,
    migration_path,
)
from tests.multi_tenant.test_rls_partner_readable_pets_migration import (
    OWN_TENANT_GUARD,
    PARTNER_LINK_EXISTS_GUARD,
    PARTNER_SELECT_GUARD,
    TENANT_SETTING_UUID,
    _drop_custom_sql_for,
    _upgrade_sql_for,
)


MIGRATION_FILE = migration_path("ty20260614a1_rls_partner_readable_produtos.py")
PARTNER_READABLE_PRODUCT_RLS_TABLES = ("produtos",)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        PARTNER_READABLE_PRODUCT_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_partner_readable_produtos_rls_migration_metadata_and_scope():
    assert MIGRATION_FILE.exists()

    migration = load_migration(MIGRATION_FILE)

    assert migration["revision"] == "ty20260614a1"
    assert migration["down_revision"] == "tx20260614a1"
    assert (
        migration["PARTNER_READABLE_PRODUCT_RLS_TABLES"]
        == PARTNER_READABLE_PRODUCT_RLS_TABLES
    )
    assert migration["TENANT_SETTING_UUID"] == TENANT_SETTING_UUID
    assert migration["OWN_TENANT_GUARD"] == OWN_TENANT_GUARD
    assert migration["PARTNER_LINK_EXISTS_GUARD"] == PARTNER_LINK_EXISTS_GUARD
    assert migration["PARTNER_SELECT_GUARD"] == PARTNER_SELECT_GUARD


def test_partner_readable_produtos_rls_upgrade_enables_partner_read_and_own_writes(
    monkeypatch,
):
    assert _capture(monkeypatch, "upgrade") == _upgrade_sql_for("produtos")


def test_partner_readable_produtos_rls_downgrade_removes_custom_policies(monkeypatch):
    assert _capture(monkeypatch, "downgrade") == [
        *_drop_custom_sql_for("produtos"),
        "ALTER TABLE produtos NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE produtos DISABLE ROW LEVEL SECURITY",
    ]


def test_partner_readable_produtos_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_produtos_are_tracked_by_tenant_safe_sql_guardrail():
    assert "produtos" in TENANT_SCOPED_TABLES
