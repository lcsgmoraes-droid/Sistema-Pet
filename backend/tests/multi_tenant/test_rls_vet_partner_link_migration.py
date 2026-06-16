from tests.multi_tenant.rls_migration_helpers import (
    capture_migration_sql,
    load_migration,
    migration_path,
)


MIGRATION_FILE = migration_path("rq20260612a1_rls_vet_partner_link.py")
TABLE_NAME = "vet_partner_link"
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
SELECT_GUARD = (
    f"empresa_tenant_id = {TENANT_SETTING_UUID} "
    f"OR vet_tenant_id = {TENANT_SETTING_UUID}"
)
WRITE_GUARD = f"empresa_tenant_id = {TENANT_SETTING_UUID}"

POLICY_NAMES = (
    "vet_partner_link_partner_select",
    "vet_partner_link_empresa_insert",
    "vet_partner_link_empresa_update",
    "vet_partner_link_empresa_delete",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        (TABLE_NAME,),
        dialect=dialect,
        existing=existing,
    )


def test_vet_partner_link_rls_migration_metadata_and_scope():
    assert MIGRATION_FILE.exists()

    migration = load_migration(MIGRATION_FILE)

    assert migration["revision"] == "rq20260612a1"
    assert migration["down_revision"] == "rp20260612a1"
    assert migration["VET_PARTNER_LINK_RLS_TABLE"] == TABLE_NAME
    assert migration["TENANT_SETTING_UUID"] == TENANT_SETTING_UUID
    assert migration["SELECT_GUARD"] == SELECT_GUARD
    assert migration["WRITE_GUARD"] == WRITE_GUARD
    assert migration["POLICY_NAMES"] == POLICY_NAMES


def test_vet_partner_link_rls_upgrade_uses_bilateral_read_and_empresa_write(
    monkeypatch,
):
    emitted = _capture(monkeypatch, "upgrade")

    assert emitted == [
        "ALTER TABLE vet_partner_link ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE vet_partner_link FORCE ROW LEVEL SECURITY",
        "DROP POLICY IF EXISTS vet_partner_link_partner_select ON vet_partner_link",
        "DROP POLICY IF EXISTS vet_partner_link_empresa_insert ON vet_partner_link",
        "DROP POLICY IF EXISTS vet_partner_link_empresa_update ON vet_partner_link",
        "DROP POLICY IF EXISTS vet_partner_link_empresa_delete ON vet_partner_link",
        (
            "CREATE POLICY vet_partner_link_partner_select ON vet_partner_link "
            f"FOR SELECT USING ({SELECT_GUARD})"
        ),
        (
            "CREATE POLICY vet_partner_link_empresa_insert ON vet_partner_link "
            f"FOR INSERT WITH CHECK ({WRITE_GUARD})"
        ),
        (
            "CREATE POLICY vet_partner_link_empresa_update ON vet_partner_link "
            f"FOR UPDATE USING ({WRITE_GUARD}) WITH CHECK ({WRITE_GUARD})"
        ),
        (
            "CREATE POLICY vet_partner_link_empresa_delete ON vet_partner_link "
            f"FOR DELETE USING ({WRITE_GUARD})"
        ),
    ]


def test_vet_partner_link_rls_upgrade_skips_missing_table(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_vet_partner_link_rls_downgrade_removes_custom_policies(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")

    assert emitted == [
        "DROP POLICY IF EXISTS vet_partner_link_empresa_delete ON vet_partner_link",
        "DROP POLICY IF EXISTS vet_partner_link_empresa_update ON vet_partner_link",
        "DROP POLICY IF EXISTS vet_partner_link_empresa_insert ON vet_partner_link",
        "DROP POLICY IF EXISTS vet_partner_link_partner_select ON vet_partner_link",
        "ALTER TABLE vet_partner_link NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE vet_partner_link DISABLE ROW LEVEL SECURITY",
    ]


def test_vet_partner_link_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
