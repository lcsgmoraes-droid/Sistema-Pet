import runpy
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from app.xml_contabilidade_models import XmlContabilidadeConfig, XmlContabilidadeEnvio


def test_migration_cria_esquema_compativel_com_modelos_e_reverte():
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/zzzzh20261019a1_xml_contabilidade.py"
    )
    migration = runpy.run_path(str(path))
    assert migration["down_revision"] == "zzzzg20261019a1"
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration["upgrade"]()
            for model in (XmlContabilidadeConfig, XmlContabilidadeEnvio):
                tabela = model.__tablename__
                assert set(model.__table__.columns.keys()) == {
                    c["name"] for c in inspect(conn).get_columns(tabela)
                }
                assert inspect(conn).get_unique_constraints(tabela)
            migration["downgrade"]()
            assert not inspect(conn).has_table("xml_contabilidade_config")
            assert not inspect(conn).has_table("xml_contabilidade_envios")
    engine.dispose()


def test_migration_aplica_rls_forcado_as_duas_tabelas(monkeypatch):
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/zzzzh20261019a1_xml_contabilidade.py"
    )
    migration = runpy.run_path(str(path))
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
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in captured
        policy = next(
            sql for sql in captured if sql.startswith(f"CREATE POLICY {table}_")
        )
        assert "USING (tenant_id =" in policy
        assert "WITH CHECK (tenant_id =" in policy
        assert "current_setting('app.tenant_id', true)" in policy
