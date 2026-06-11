from pathlib import Path
import runpy
from types import SimpleNamespace


MIGRATION = Path(__file__).resolve().parents[2] / "alembic" / "versions" / (
    "qd20260611a1_rls_delivery_config_table.py"
)
TARGETS = ("configuracoes_entrega",)
TENANT_POLICY = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _migration_module():
    return runpy.run_path(str(MIGRATION))


def _fake_alembic(monkeypatch, module, *, present=TARGETS, dialect="postgresql"):
    statements: list[str] = []
    available = set(present)

    monkeypatch.setattr(
        module["op"],
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name=dialect)),
    )
    monkeypatch.setattr(module["op"], "execute", lambda sql: statements.append(str(sql)))
    monkeypatch.setattr(
        module["sa"],
        "inspect",
        lambda _bind: SimpleNamespace(has_table=lambda table_name: table_name in available),
    )
    return statements


def test_delivery_config_rls_migration_chains_after_store_config():
    source = MIGRATION.read_text(encoding="utf-8")

    expected_snippets = [
        'revision = "qd20260611a1"',
        'down_revision = "qc20260611a1"',
        "configuracoes_entrega",
        TENANT_POLICY,
    ]
    for snippet in expected_snippets:
        assert snippet in source


def test_delivery_config_upgrade_honors_existing_table_detection(monkeypatch):
    module = _migration_module()
    emitted = _fake_alembic(monkeypatch, module)

    module["upgrade"]()
    joined = "\n".join(emitted)

    assert joined.count("ENABLE ROW LEVEL SECURITY") == 1
    assert joined.count("FORCE ROW LEVEL SECURITY") == 1
    assert "DROP POLICY IF EXISTS configuracoes_entrega_tenant_isolation" in joined
    assert f"USING ({TENANT_POLICY}) WITH CHECK ({TENANT_POLICY})" in joined


def test_delivery_config_downgrade_removes_policy_before_disabling_rls(monkeypatch):
    module = _migration_module()
    emitted = _fake_alembic(monkeypatch, module)

    module["downgrade"]()

    assert emitted == [
        "DROP POLICY IF EXISTS configuracoes_entrega_tenant_isolation ON configuracoes_entrega",
        "ALTER TABLE configuracoes_entrega NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE configuracoes_entrega DISABLE ROW LEVEL SECURITY",
    ]


def test_delivery_config_rls_migration_ignores_non_postgresql_binds(monkeypatch):
    module = _migration_module()
    emitted = _fake_alembic(monkeypatch, module, dialect="sqlite")

    module["upgrade"]()
    module["downgrade"]()

    assert emitted == []
