import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zyw20260830a1_catalogo_compartilhado_grupo.py"
)


def _carregar_migration():
    spec = importlib.util.spec_from_file_location(
        "catalogo_compartilhado_migration", MIGRATION
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_adiciona_e_remove_acesso_catalogo_completo(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'catalogo-compartilhado.db'}")
    metadata = sa.MetaData()
    sa.Table(
        "empresa_grupo_estoques_compartilhados",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
    )
    metadata.create_all(engine)

    migration = _carregar_migration()
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        colunas = {
            item["name"]
            for item in sa.inspect(connection).get_columns(
                "empresa_grupo_estoques_compartilhados"
            )
        }
        assert "acesso_catalogo_completo" in colunas

        migration.downgrade()
        colunas = {
            item["name"]
            for item in sa.inspect(connection).get_columns(
                "empresa_grupo_estoques_compartilhados"
            )
        }
        assert "acesso_catalogo_completo" not in colunas

    engine.dispose()
