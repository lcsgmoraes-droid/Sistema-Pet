from pathlib import Path
import importlib.util
from types import SimpleNamespace


MIGRATION_PATH = (
    Path(__file__)
    .resolve()
    .parents[2]
    .joinpath(
        "alembic",
        "versions",
        "py20260611a1_rls_campaign_rewards_tables.py",
    )
)

REWARD_TABLES = (
    "loyalty_stamps",
    "cashback_transactions",
    "coupons",
    "coupon_redemptions",
)

TENANT_SCOPE = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "campaign_rewards_rls", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _patch_alembic(
    monkeypatch, module, *, dialect="postgresql", existing=REWARD_TABLES
):
    class _Bind:
        def __init__(self, dialect_name):
            self.dialect = SimpleNamespace(name=dialect_name)

    class _Inspector:
        def has_table(self, table_name):
            return table_name in existing

    emitted: list[str] = []
    monkeypatch.setattr(module.op, "get_bind", lambda: _Bind(dialect))
    monkeypatch.setattr(module.sa, "inspect", lambda bind: _Inspector())
    monkeypatch.setattr(module.op, "execute", lambda sql: emitted.append(str(sql)))
    return emitted


def test_campaign_rewards_migration_is_chained_after_campaign_core():
    assert MIGRATION_PATH.exists()

    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert 'revision = "py20260611a1"' in source
    assert 'down_revision = "px20260611a1"' in source
    assert TENANT_SCOPE in source
    assert "campaign_event_queue" not in source
    assert "notification_queue" not in source
    assert "drawings" not in source


def test_campaign_rewards_upgrade_emits_tenant_policies_for_present_tables(monkeypatch):
    module = _load_module()
    present_tables = ("loyalty_stamps", "coupons", "coupon_redemptions")
    emitted = _patch_alembic(monkeypatch, module, existing=present_tables)

    module.upgrade()
    joined = "\n".join(emitted)

    assert "cashback_transactions" not in joined
    assert joined.count("ENABLE ROW LEVEL SECURITY") == len(present_tables)
    assert joined.count("FORCE ROW LEVEL SECURITY") == len(present_tables)
    assert joined.count("CREATE POLICY") == len(present_tables)

    for table_name in present_tables:
        assert (
            f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"
            in joined
        )
        assert f"USING ({TENANT_SCOPE}) WITH CHECK ({TENANT_SCOPE})" in joined


def test_campaign_rewards_downgrade_disables_tables_from_child_to_parent(monkeypatch):
    module = _load_module()
    emitted = _patch_alembic(monkeypatch, module)

    module.downgrade()

    drop_policy_sql = [
        sql for sql in emitted if sql.startswith("DROP POLICY IF EXISTS")
    ]
    assert drop_policy_sql == [
        f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"
        for table_name in reversed(REWARD_TABLES)
    ]

    for table_name in REWARD_TABLES:
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in emitted
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in emitted


def test_campaign_rewards_migration_is_noop_for_sqlite(monkeypatch):
    module = _load_module()
    emitted = _patch_alembic(monkeypatch, module, dialect="sqlite")

    module.upgrade()
    module.downgrade()

    assert emitted == []
