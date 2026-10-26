"""O novo contexto não reescreve vendas ou documentos fiscais existentes."""

from pathlib import Path
import runpy
from unittest.mock import Mock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    select,
)


def migration_data():
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    candidates = list(versions.glob("zzzzy20261026a1_*.py"))
    assert len(candidates) == 1
    return runpy.run_path(str(candidates[0]))


def test_migration_adiciona_contexto_sem_alterar_dados_fiscais_existentes():
    migration = migration_data()
    assert migration["revision"] == "zzzzy20261026a1"
    assert migration["down_revision"] == "zzzzx20261026a1"
    metadata = MetaData()
    sales = Table(
        "vendas",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("tenant_id", String, nullable=False),
        Column("numero_venda", String),
        Column("canal", String),
        Column("status", String),
        Column("nfe_status", String),
        Column("nfe_numero", Integer),
        Column("nfe_xml", String),
    )
    original = {
        "id": 1,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "numero_venda": "202610260023",
        "canal": "loja_fisica",
        "status": "pago_nf",
        "nfe_status": "autorizada",
        "nfe_numero": 1648,
        "nfe_xml": "<xml>documento-original-preservado</xml>",
    }
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sales.insert().values(**original))
        with Operations.context(MigrationContext.configure(conn)):
            migration["upgrade"]()
            columns = {
                column["name"]: column for column in inspect(conn).get_columns("vendas")
            }
            assert columns["nfe_contexto_comercial"]["nullable"] is True
            migrated = Table("vendas", MetaData(), autoload_with=conn)
            saved = conn.execute(select(migrated)).mappings().one()
            assert {key: saved[key] for key in original} == original
            assert saved["nfe_contexto_comercial"] is None
    engine.dispose()


@pytest.mark.parametrize("has_context", [True, False])
def test_downgrade_preserva_historico_comercial_existente(monkeypatch, has_context):
    migration = migration_data()
    bind = Mock()
    bind.execute.return_value.first.return_value = (1,) if has_context else None
    drop = Mock()
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(migration["op"], "execute", Mock())
    monkeypatch.setattr(migration["op"], "drop_column", drop)

    if has_context:
        with pytest.raises(RuntimeError, match="Preserve o histórico"):
            migration["downgrade"]()
        drop.assert_not_called()
    else:
        migration["downgrade"]()
        drop.assert_called_once_with("vendas", "nfe_contexto_comercial")
