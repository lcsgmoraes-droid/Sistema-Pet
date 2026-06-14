from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("tt20260614a1_rls_legacy_product_backup_tables.py")

LEGACY_PRODUCT_BACKUP_RLS_TABLES = (
    "backup_barras_cleanup_20260327",
    "backup_produto_bling_sync_cleanup_20260327",
    "backup_produto_bling_sync_excluidos_decisao_manual_20260327",
    "backup_produto_bling_sync_excluidos_pos_barra_20260327",
    "backup_produto_bling_sync_excluidos_sku_cleanup_20260327",
    "backup_produto_kit_componentes_cleanup_20260327",
    "backup_produtos_cleanup_20260327",
    "backup_produtos_excluidos_decisao_manual_20260327",
    "backup_produtos_excluidos_pos_barra_20260327",
    "backup_produtos_excluidos_sku_cleanup_20260327",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        LEGACY_PRODUCT_BACKUP_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_legacy_product_backup_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="tt20260614a1",
        down_revision="ts20260614a1",
        table_constant="LEGACY_PRODUCT_BACKUP_RLS_TABLES",
        table_names=LEGACY_PRODUCT_BACKUP_RLS_TABLES,
    )


def test_legacy_product_backup_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        LEGACY_PRODUCT_BACKUP_RLS_TABLES,
    )


def test_legacy_product_backup_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_legacy_product_backup_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        LEGACY_PRODUCT_BACKUP_RLS_TABLES,
    )


def test_legacy_product_backup_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
