from pathlib import Path
import runpy
from types import SimpleNamespace


MIGRATION = Path(__file__).resolve().parents[2] / "alembic" / "versions" / (
    "qc20260611a1_rls_store_config_tables.py"
)
TARGETS = ("empresa_config_geral", "configuracoes_custo_moto")
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


def test_store_config_rls_migration_chains_after_validity_campaign():
    source = MIGRATION.read_text(encoding="utf-8")

    expected_snippets = [
        'revision = "qc20260611a1"',
        'down_revision = "qb20260611a1"',
        "empresa_config_geral",
        "configuracoes_custo_moto",
        TENANT_POLICY,
    ]
    for snippet in expected_snippets:
        assert snippet in source

    intentionally_deferred = (
        "configuracoes_entrega",
        "empresa_config_fiscal",
        "simples_nacional_mensal",
    )
    for table_name in intentionally_deferred:
        assert table_name not in source


def test_store_config_upgrade_honors_existing_table_detection(monkeypatch):
    module = _migration_module()
    emitted = _fake_alembic(monkeypatch, module, present=("empresa_config_geral",))

    module["upgrade"]()
    joined = "\n".join(emitted)

    assert "configuracoes_custo_moto" not in joined
    assert joined.count("ENABLE ROW LEVEL SECURITY") == 1
    assert joined.count("FORCE ROW LEVEL SECURITY") == 1
    assert "DROP POLICY IF EXISTS empresa_config_geral_tenant_isolation" in joined
    assert f"USING ({TENANT_POLICY}) WITH CHECK ({TENANT_POLICY})" in joined


def test_store_config_downgrade_uses_reverse_target_order(monkeypatch):
    module = _migration_module()
    emitted = _fake_alembic(monkeypatch, module)

    module["downgrade"]()
    policy_drops = [sql for sql in emitted if sql.startswith("DROP POLICY IF EXISTS")]

    assert policy_drops == [
        "DROP POLICY IF EXISTS configuracoes_custo_moto_tenant_isolation ON configuracoes_custo_moto",
        "DROP POLICY IF EXISTS empresa_config_geral_tenant_isolation ON empresa_config_geral",
    ]
    assert emitted[-2:] == [
        "ALTER TABLE empresa_config_geral NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE empresa_config_geral DISABLE ROW LEVEL SECURITY",
    ]


def test_store_config_rls_migration_ignores_non_postgresql_binds(monkeypatch):
    module = _migration_module()
    emitted = _fake_alembic(monkeypatch, module, dialect="sqlite")

    module["upgrade"]()
    module["downgrade"]()

    assert emitted == []
