from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("ro20260612a1_rls_veterinary_hospitalization_tables.py")

VETERINARY_HOSPITALIZATION_RLS_TABLES = (
    "vet_internacoes",
    "vet_internacao_configuracoes",
    "vet_evolucoes_internacao",
    "vet_internacao_procedimentos_agenda",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        VETERINARY_HOSPITALIZATION_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_veterinary_hospitalization_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="ro20260612a1",
        down_revision="rn20260612a1",
        table_constant="VETERINARY_HOSPITALIZATION_RLS_TABLES",
        table_names=VETERINARY_HOSPITALIZATION_RLS_TABLES,
    )


def test_veterinary_hospitalization_rls_upgrade_targets_declared_tables(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    assert_upgrade_emits_rls_for_declared_tables(emitted, VETERINARY_HOSPITALIZATION_RLS_TABLES)


def test_veterinary_hospitalization_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_veterinary_hospitalization_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        VETERINARY_HOSPITALIZATION_RLS_TABLES,
    )


def test_veterinary_hospitalization_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
