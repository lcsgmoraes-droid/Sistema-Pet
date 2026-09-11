"""Roundtrip local e contrato do DDL PostgreSQL da nova tabela fiscal."""

import importlib.util
from io import StringIO
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def migration_module():
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/zzn20260909a1_intnfe_activation.py"
    )
    spec = importlib.util.spec_from_file_location("intnfe_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_roundtrip_preserves_unrelated_tables():
    engine = create_engine("sqlite://")
    migration = migration_module()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE existing_data (id INTEGER PRIMARY KEY)"
        )
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
            inspector = inspect(connection)
            assert inspector.has_table("intnfe_connections")
            unique = {
                tuple(row["column_names"])
                for row in inspector.get_unique_constraints("intnfe_connections")
            }
            assert unique == {("tenant_id",), ("cnpj",), ("emitente_id",)}
            migration.downgrade()
        assert not inspect(connection).has_table("intnfe_connections")
        assert inspect(connection).has_table("existing_data")
    engine.dispose()


def test_postgresql_ddl_requires_tenant_for_reads_and_writes():
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration_module().upgrade()
    ddl = output.getvalue()
    assert "tenant_id UUID NOT NULL" in ddl
    assert "ENABLE ROW LEVEL SECURITY" in ddl
    assert "FORCE ROW LEVEL SECURITY" in ddl
    guard = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
    assert f"USING ({guard}) WITH CHECK ({guard})" in ddl
