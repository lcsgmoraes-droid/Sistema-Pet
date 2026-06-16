from pathlib import Path
import runpy
from types import SimpleNamespace


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / ("qe20260611a1_add_cliente_alertas_pdv.py")
)


def _migration_module():
    return runpy.run_path(str(MIGRATION))


def test_cliente_alertas_pdv_migration_chains_from_current_main_head():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "qe20260611a1"' in source
    assert 'down_revision = "qc20260611a1"' in source
    assert "alertas_pdv" in source
    assert "clientes" in source


def test_cliente_alertas_pdv_upgrade_adds_json_column_when_table_exists(monkeypatch):
    module = _migration_module()
    operations = []

    monkeypatch.setattr(
        module["op"],
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    monkeypatch.setattr(
        module["sa"],
        "inspect",
        lambda _bind: SimpleNamespace(
            has_table=lambda table_name: table_name == "clientes"
        ),
    )
    monkeypatch.setattr(
        module["op"],
        "add_column",
        lambda table_name, column: operations.append(("add", table_name, column.name)),
    )

    module["upgrade"]()

    assert operations == [("add", "clientes", "alertas_pdv")]


def test_cliente_alertas_pdv_migration_skips_missing_legacy_table(monkeypatch):
    module = _migration_module()
    operations = []

    monkeypatch.setattr(
        module["op"],
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    monkeypatch.setattr(
        module["sa"],
        "inspect",
        lambda _bind: SimpleNamespace(has_table=lambda _table_name: False),
    )
    monkeypatch.setattr(
        module["op"], "add_column", lambda *_args: operations.append("add")
    )
    monkeypatch.setattr(
        module["op"], "drop_column", lambda *_args: operations.append("drop")
    )

    module["upgrade"]()
    module["downgrade"]()

    assert operations == []
