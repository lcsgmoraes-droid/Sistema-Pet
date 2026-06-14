from tests.multi_tenant.rls_migration_helpers import (
    TENANT_RLS_GUARD,
    capture_migration_sql,
    load_migration,
    migration_path,
)


MIGRATION_FILE = migration_path("tx20260614a1_rls_partner_readable_pets.py")
PARTNER_READABLE_RLS_TABLES = ("clientes", "pets")
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
OWN_TENANT_GUARD = f"tenant_id = {TENANT_SETTING_UUID}"
PARTNER_LINK_EXISTS_GUARD = (
    "EXISTS (SELECT 1 FROM vet_partner_link vpl "
    "WHERE vpl.empresa_tenant_id = tenant_id "
    f"AND vpl.vet_tenant_id = {TENANT_SETTING_UUID} "
    "AND vpl.ativo = true)"
)
PARTNER_SELECT_GUARD = f"({OWN_TENANT_GUARD}) OR ({PARTNER_LINK_EXISTS_GUARD})"


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        PARTNER_READABLE_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def _policy_names(table_name: str) -> tuple[str, ...]:
    return (
        f"{table_name}_partner_select",
        f"{table_name}_tenant_insert",
        f"{table_name}_tenant_update",
        f"{table_name}_tenant_delete",
    )


def _upgrade_sql_for(table_name: str) -> list[str]:
    select_policy, insert_policy, update_policy, delete_policy = _policy_names(table_name)
    return [
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}",
        f"DROP POLICY IF EXISTS {select_policy} ON {table_name}",
        f"DROP POLICY IF EXISTS {insert_policy} ON {table_name}",
        f"DROP POLICY IF EXISTS {update_policy} ON {table_name}",
        f"DROP POLICY IF EXISTS {delete_policy} ON {table_name}",
        (
            f"CREATE POLICY {select_policy} ON {table_name} "
            f"FOR SELECT USING ({PARTNER_SELECT_GUARD})"
        ),
        (
            f"CREATE POLICY {insert_policy} ON {table_name} "
            f"FOR INSERT WITH CHECK ({OWN_TENANT_GUARD})"
        ),
        (
            f"CREATE POLICY {update_policy} ON {table_name} "
            f"FOR UPDATE USING ({OWN_TENANT_GUARD}) WITH CHECK ({OWN_TENANT_GUARD})"
        ),
        (
            f"CREATE POLICY {delete_policy} ON {table_name} "
            f"FOR DELETE USING ({OWN_TENANT_GUARD})"
        ),
    ]


def _drop_custom_sql_for(table_name: str) -> list[str]:
    return [
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"
        for policy_name in reversed(_policy_names(table_name))
    ]


def test_partner_readable_pets_rls_migration_metadata_and_scope():
    assert MIGRATION_FILE.exists()

    migration = load_migration(MIGRATION_FILE)

    assert migration["revision"] == "tx20260614a1"
    assert migration["down_revision"] == "tw20260614a1"
    assert migration["PARTNER_READABLE_RLS_TABLES"] == PARTNER_READABLE_RLS_TABLES
    assert migration["TENANT_SETTING_UUID"] == TENANT_SETTING_UUID
    assert migration["OWN_TENANT_GUARD"] == OWN_TENANT_GUARD
    assert migration["PARTNER_LINK_EXISTS_GUARD"] == PARTNER_LINK_EXISTS_GUARD
    assert migration["PARTNER_SELECT_GUARD"] == PARTNER_SELECT_GUARD
    assert migration["TENANT_GUARD"] == TENANT_RLS_GUARD


def test_partner_readable_pets_rls_upgrade_enables_partner_read_and_own_writes(monkeypatch):
    assert _capture(monkeypatch, "upgrade") == (
        _upgrade_sql_for("clientes") + _upgrade_sql_for("pets")
    )


def test_partner_readable_pets_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=("clientes",)) == _upgrade_sql_for("clientes")


def test_partner_readable_pets_rls_downgrade_restores_clientes_and_unwinds_pets(monkeypatch):
    assert _capture(monkeypatch, "downgrade") == [
        *_drop_custom_sql_for("pets"),
        "ALTER TABLE pets NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE pets DISABLE ROW LEVEL SECURITY",
        *_drop_custom_sql_for("clientes"),
        "DROP POLICY IF EXISTS clientes_tenant_isolation ON clientes",
        (
            "CREATE POLICY clientes_tenant_isolation ON clientes "
            f"USING ({TENANT_RLS_GUARD}) WITH CHECK ({TENANT_RLS_GUARD})"
        ),
    ]


def test_partner_readable_pets_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
