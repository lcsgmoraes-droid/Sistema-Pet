from pathlib import Path
from types import SimpleNamespace
import runpy


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "qd20260611a1_rls_delivery_config_table.py"
)


def _load_with_fake_bind(monkeypatch, *, dialect="postgresql", table_exists=True):
    module = runpy.run_path(str(MIGRATION))
    emitted: list[str] = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    inspector = SimpleNamespace(
        has_table=lambda name: table_exists and name == "configuracoes_entrega"
    )

    monkeypatch.setattr(module["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(module["op"], "execute", emitted.append)
    monkeypatch.setattr(module["sa"], "inspect", lambda _bind: inspector)
    return module, emitted


def test_delivery_config_rls_migration_points_to_current_head():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "qd20260611a1"' in source
    assert 'down_revision = "qe20260611a1"' in source
    assert 'TABLE_NAME = "configuracoes_entrega"' in source
    assert 'POLICY_NAME = f"{TABLE_NAME}_tenant_isolation"' in source


def test_delivery_config_upgrade_and_downgrade_emit_expected_policy_sql(monkeypatch):
    module, emitted = _load_with_fake_bind(monkeypatch)

    module["upgrade"]()
    assert emitted == [
        "ALTER TABLE configuracoes_entrega ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE configuracoes_entrega FORCE ROW LEVEL SECURITY",
        "DROP POLICY IF EXISTS configuracoes_entrega_tenant_isolation ON configuracoes_entrega",
        (
            "CREATE POLICY configuracoes_entrega_tenant_isolation ON configuracoes_entrega "
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
        ),
    ]

    emitted.clear()
    module["downgrade"]()
    assert emitted == [
        "DROP POLICY IF EXISTS configuracoes_entrega_tenant_isolation ON configuracoes_entrega",
        "ALTER TABLE configuracoes_entrega NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE configuracoes_entrega DISABLE ROW LEVEL SECURITY",
    ]


def test_delivery_config_rls_migration_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"table_exists": False}):
        module, emitted = _load_with_fake_bind(monkeypatch, **kwargs)
        module["upgrade"]()
        module["downgrade"]()
        assert emitted == []
