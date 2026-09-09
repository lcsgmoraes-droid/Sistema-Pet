"""Contrato da migração: executada só em SQLite descartável neste arquivo."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic/versions/zzm20260909a1_creditos_base.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location(
        "creditos_base_migration", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_is_linear_no_payment_or_balance_seed():
    migration = load_migration()
    assert migration.revision == "zzm20260909a1"
    assert migration.down_revision == "zzl20260909a1"
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "INSERT INTO" not in source
    assert "iter_tenant_rls_statements" in source
    assert "BEFORE UPDATE OR DELETE" in source
    assert "BEFORE TRUNCATE" in source
    assert "fk_creditos_ledger_tenant_operation" in source


def test_upgrade_twice_and_downgrade_twice_on_isolated_database():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    Table("tenants", metadata, Column("id", String(36), primary_key=True))
    Table("users", metadata, Column("id", Integer, primary_key=True))
    metadata.create_all(engine)
    migration = load_migration()
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        migration.upgrade()
        inspector = inspect(connection)
        assert set(migration.TABLES) <= set(inspector.get_table_names())
        for table in migration.TABLES:
            fields = {col["name"]: col for col in inspector.get_columns(table)}
            assert fields["tenant_id"]["nullable"] is False
            assert fields["tenant_ref_id"]["computed"]["persisted"] is True
            assert any(
                fk["referred_table"] == "tenants"
                for fk in inspector.get_foreign_keys(table)
            )
        migration.downgrade()
        migration.downgrade()
        assert set(inspect(connection).get_table_names()) == {"tenants", "users"}
    engine.dispose()
