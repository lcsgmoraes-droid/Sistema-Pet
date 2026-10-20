import runpy
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import UniqueConstraint, create_engine, inspect, text

from app.xml_contabilidade_models import (
    XmlContabilidadeEvento,
    XmlContabilidadeMonitor,
)


def _migration():
    return runpy.run_path(
        str(
            Path(__file__).parents[2]
            / "alembic/versions/zzzzj20261019a1_xml_contabilidade_eventos.py"
        )
    )


def test_migration_eventos_compativel_com_modelos_e_reverte_sem_tocar_historico():
    migration = _migration()
    assert migration["down_revision"] == "zzzzi20261019a1"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE historico_existente (id INTEGER)"))
            conn.execute(text("INSERT INTO historico_existente VALUES (42)"))
            with Operations.context(MigrationContext.configure(conn)):
                migration["upgrade"]()
                for model in (XmlContabilidadeMonitor, XmlContabilidadeEvento):
                    tabela = model.__tablename__
                    colunas = {c["name"]: c for c in inspect(conn).get_columns(tabela)}
                    assert set(model.__table__.columns.keys()) == set(colunas)
                    for column in model.__table__.columns:
                        assert colunas[column.name]["nullable"] == column.nullable
                        # SQLite adapta UUID/Identity; tamanho e tipo dos dados
                        # fiscais continuam precisando acompanhar o modelo.
                        if column.name not in {"id", "tenant_id"}:
                            assert str(colunas[column.name]["type"]) == str(column.type)
                    assert {
                        (constraint["name"], tuple(constraint["column_names"]))
                        for constraint in inspect(conn).get_unique_constraints(tabela)
                    } == {
                        (constraint.name, tuple(c.name for c in constraint.columns))
                        for constraint in model.__table__.constraints
                        if isinstance(constraint, UniqueConstraint)
                    }
                    assert {
                        (index["name"], tuple(index["column_names"]))
                        for index in inspect(conn).get_indexes(tabela)
                    } == {
                        (index.name, tuple(c.name for c in index.columns))
                        for index in model.__table__.indexes
                    }
                migration["downgrade"]()
            assert not any(
                inspect(conn).has_table(tabela) for tabela in migration["TABLES"]
            )
            assert (
                conn.execute(text("SELECT id FROM historico_existente")).scalar() == 42
            )
    finally:
        engine.dispose()


def test_migration_eventos_aplica_rls_forcado_a_monitor_e_comprovantes(monkeypatch):
    migration = _migration()
    captured = []
    monkeypatch.setattr(migration["op"], "create_table", lambda *_a, **_kw: None)
    monkeypatch.setattr(migration["op"], "create_index", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        migration["op"],
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    monkeypatch.setattr(
        migration["sa"], "inspect", lambda _: SimpleNamespace(has_table=lambda _: True)
    )
    monkeypatch.setattr(migration["op"], "execute", captured.append)
    migration["upgrade"]()
    for table in migration["TABLES"]:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in captured
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in captured
        policy = next(
            sql for sql in captured if sql.startswith(f"CREATE POLICY {table}_")
        )
        assert "USING (tenant_id =" in policy
        assert "WITH CHECK (tenant_id =" in policy
        assert "current_setting('app.tenant_id', true)" in policy
