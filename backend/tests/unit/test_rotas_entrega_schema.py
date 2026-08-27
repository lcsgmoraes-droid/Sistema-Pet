from __future__ import annotations

import pytest

from app.api.endpoints import rotas_entrega_schema as schema


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeSession:
    def __init__(self, schema_snapshots):
        self.schema_snapshots = iter(schema_snapshots)
        self.statements: list[str] = []
        self.commits = 0

    def execute(self, statement):
        sql = str(statement).strip()
        self.statements.append(sql)
        if "information_schema.columns" in sql:
            return FakeResult(next(self.schema_snapshots))
        return FakeResult([])

    def commit(self):
        self.commits += 1


@pytest.fixture(autouse=True)
def reset_schema_check(monkeypatch):
    monkeypatch.setattr(schema, "_rotas_schema_checked", False)


def current_schema_rows():
    return [
        (table_name, column_name)
        for table_name, columns in schema._REQUIRED_COLUMNS.items()
        for column_name in columns
    ]


def test_schema_atual_nao_executa_ddl_nem_commit():
    db = FakeSession([current_schema_rows()])

    schema.ensure_rotas_entrega_schema(db)

    assert len(db.statements) == 1
    assert "information_schema.columns" in db.statements[0]
    assert db.commits == 0
    assert schema._rotas_schema_checked is True


def test_outro_worker_pode_concluir_schema_apos_advisory_lock():
    db = FakeSession([[], current_schema_rows()])

    schema.ensure_rotas_entrega_schema(db)

    assert len(db.statements) == 3
    assert "pg_advisory_xact_lock(739204817)" in db.statements[1]
    assert not any(statement.startswith("ALTER TABLE") for statement in db.statements)
    assert db.commits == 1
    assert schema._rotas_schema_checked is True


def test_schema_legado_executa_ddl_uma_unica_vez():
    db = FakeSession([[], []])

    schema.ensure_rotas_entrega_schema(db)
    schema.ensure_rotas_entrega_schema(db)

    ddl = [
        statement for statement in db.statements if statement.startswith("ALTER TABLE")
    ]
    assert len(ddl) == sum(
        len(columns) for columns in schema._REQUIRED_COLUMNS.values()
    )
    assert db.commits == 1
    assert schema._rotas_schema_checked is True
