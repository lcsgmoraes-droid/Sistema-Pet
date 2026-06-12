from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qv20260612a1_rls_purchase_pending_tables.py")

PURCHASE_PENDING_RLS_TABLES = (
    "compras_pendencias_fornecedor",
    "compras_pendencias_fornecedor_itens",
    "compras_pendencias_fornecedor_historico",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        PURCHASE_PENDING_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_purchase_pending_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qv20260612a1",
        down_revision="qu20260612a1",
        table_constant="PURCHASE_PENDING_RLS_TABLES",
        table_names=PURCHASE_PENDING_RLS_TABLES,
    )


def test_purchase_pending_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        PURCHASE_PENDING_RLS_TABLES,
    )


def test_purchase_pending_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=(
                "compras_pendencias_fornecedor",
                "compras_pendencias_fornecedor_historico",
            ),
        )
    )

    assert "compras_pendencias_fornecedor" in emitted
    assert "compras_pendencias_fornecedor_historico" in emitted
    assert "compras_pendencias_fornecedor_itens" not in emitted


def test_purchase_pending_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        PURCHASE_PENDING_RLS_TABLES,
    )


def test_purchase_pending_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
