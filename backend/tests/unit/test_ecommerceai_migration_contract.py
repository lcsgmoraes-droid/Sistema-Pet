from __future__ import annotations

import importlib.util
from pathlib import Path


class _RecordingOp:
    def __init__(self):
        self.create_tables = []
        self.create_indexes = []
        self.executed = []

    def create_table(self, name, *args, **kwargs):
        self.create_tables.append((name, kwargs))

    def create_index(self, name, table_name, columns, **kwargs):
        self.create_indexes.append((name, table_name, columns, kwargs))

    def execute(self, statement):
        self.executed.append(str(statement))


def _load_migration():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "zws20260807a1_ecommerceai_integration.py"
    )
    spec = importlib.util.spec_from_file_location("ecommerceai_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ecommerceai_migration_is_idempotent_by_contract(monkeypatch):
    migration = _load_migration()
    recorder = _RecordingOp()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()
    migration.upgrade()
    migration.downgrade()
    migration.downgrade()

    assert recorder.create_tables
    assert all(
        kwargs.get("if_not_exists") is True for _, kwargs in recorder.create_tables
    )
    assert recorder.create_indexes
    assert all(
        kwargs.get("if_not_exists") is True
        for _, _, _, kwargs in recorder.create_indexes
    )
    assert len(recorder.executed) == 6
    assert all("DROP TABLE IF EXISTS" in statement for statement in recorder.executed)
