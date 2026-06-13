from app.db.sql_audit import TENANT_TABLES
from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    capture_migration_sql,
    load_migration,
    migration_path,
)


MIGRATION_FILE = migration_path("sr20260613a1_rls_ecommerce_payment_gateway_configs.py")
TABLE_NAME = "ecommerce_payment_gateway_configs"
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
WEBHOOK_TOKEN_SETTING = "app.payment_webhook_token"
TENANT_GUARD = f"tenant_id = {TENANT_SETTING_UUID}"
WEBHOOK_TOKEN_GUARD = (
    "provider = 'mercadopago' "
    "AND webhook_token = NULLIF(current_setting('app.payment_webhook_token', true), '')"
)

POLICY_NAMES = (
    "ecommerce_payment_gateway_configs_tenant_select",
    "ecommerce_payment_gateway_configs_webhook_select",
    "ecommerce_payment_gateway_configs_tenant_insert",
    "ecommerce_payment_gateway_configs_tenant_update",
    "ecommerce_payment_gateway_configs_tenant_delete",
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


def test_ecommerce_payment_gateway_configs_rls_migration_metadata_and_scope():
    assert MIGRATION_FILE.exists()

    migration = load_migration(MIGRATION_FILE)

    assert migration["revision"] == "sr20260613a1"
    assert migration["down_revision"] == "sq20260613a1"
    assert migration["PAYMENT_GATEWAY_CONFIGS_RLS_TABLE"] == TABLE_NAME
    assert migration["TENANT_SETTING_UUID"] == TENANT_SETTING_UUID
    assert migration["WEBHOOK_TOKEN_SETTING"] == WEBHOOK_TOKEN_SETTING
    assert migration["TENANT_GUARD"] == TENANT_GUARD
    assert migration["WEBHOOK_TOKEN_GUARD"] == WEBHOOK_TOKEN_GUARD
    assert migration["POLICY_NAMES"] == POLICY_NAMES


def test_ecommerce_payment_gateway_configs_rls_upgrade_adds_tenant_and_webhook_select(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    assert emitted == [
        f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_select ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_webhook_select ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_insert ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_update ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_delete ON {TABLE_NAME}",
        (
            f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_select ON {TABLE_NAME} "
            f"FOR SELECT USING ({TENANT_GUARD})"
        ),
        (
            f"CREATE POLICY ecommerce_payment_gateway_configs_webhook_select ON {TABLE_NAME} "
            f"FOR SELECT USING ({WEBHOOK_TOKEN_GUARD})"
        ),
        (
            f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_insert ON {TABLE_NAME} "
            f"FOR INSERT WITH CHECK ({TENANT_GUARD})"
        ),
        (
            f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_update ON {TABLE_NAME} "
            f"FOR UPDATE USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
        ),
        (
            f"CREATE POLICY ecommerce_payment_gateway_configs_tenant_delete ON {TABLE_NAME} "
            f"FOR DELETE USING ({TENANT_GUARD})"
        ),
    ]


def test_ecommerce_payment_gateway_configs_rls_upgrade_skips_missing_table(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_ecommerce_payment_gateway_configs_rls_downgrade_removes_custom_policies(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")

    assert emitted == [
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_delete ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_update ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_insert ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_webhook_select ON {TABLE_NAME}",
        f"DROP POLICY IF EXISTS ecommerce_payment_gateway_configs_tenant_select ON {TABLE_NAME}",
        f"ALTER TABLE {TABLE_NAME} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {TABLE_NAME} DISABLE ROW LEVEL SECURITY",
    ]


def test_ecommerce_payment_gateway_configs_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_ecommerce_payment_gateway_configs_table_is_tracked_by_sql_guardrails():
    assert TABLE_NAME in TENANT_SCOPED_TABLES
    assert TABLE_NAME in TENANT_TABLES
