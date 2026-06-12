from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qt20260612a1_rls_dre_chart_tables.py")

DRE_CHART_RLS_TABLES = (
    "dre_categorias",
    "dre_subcategorias",
    "regras_classificacao_dre",
    "historico_classificacao_dre",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        DRE_CHART_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_dre_chart_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qt20260612a1",
        down_revision="qs20260612a1",
        table_constant="DRE_CHART_RLS_TABLES",
        table_names=DRE_CHART_RLS_TABLES,
    )


def test_dre_chart_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        DRE_CHART_RLS_TABLES,
    )


def test_dre_chart_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("dre_categorias", "regras_classificacao_dre"),
        )
    )

    assert "dre_categorias" in emitted
    assert "regras_classificacao_dre" in emitted
    assert "dre_subcategorias" not in emitted
    assert "historico_classificacao_dre" not in emitted


def test_dre_chart_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        DRE_CHART_RLS_TABLES,
    )


def test_dre_chart_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
