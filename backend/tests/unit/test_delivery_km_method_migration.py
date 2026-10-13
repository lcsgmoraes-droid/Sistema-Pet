import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


@pytest.mark.parametrize("legacy", [False, True])
def test_migration_completa_schema_e_preserva_metodo_legado(legacy):
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/zzzm20261009a1_delivery_km_method.py"
    )
    spec = importlib.util.spec_from_file_location("delivery_km_method_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "zzzl20261009a1"

    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            sa.text("CREATE TABLE configuracoes_entrega (id INTEGER PRIMARY KEY)")
        )
        if legacy:
            connection.execute(
                sa.text(
                    "ALTER TABLE configuracoes_entrega ADD COLUMN "
                    "metodo_km_entrega VARCHAR(20) DEFAULT 'auto_rota'"
                )
            )
            connection.execute(
                sa.text(
                    "INSERT INTO configuracoes_entrega (id, metodo_km_entrega) "
                    "VALUES (1, 'manual')"
                )
            )
        else:
            connection.execute(
                sa.text("INSERT INTO configuracoes_entrega (id) VALUES (1)")
            )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.upgrade()
            assert connection.scalar(
                sa.text(
                    "SELECT metodo_km_entrega FROM configuracoes_entrega WHERE id=1"
                )
            ) == ("manual" if legacy else "auto_rota")
            connection.execute(
                sa.text("INSERT INTO configuracoes_entrega (id) VALUES (2)")
            )
            assert (
                connection.scalar(
                    sa.text(
                        "SELECT metodo_km_entrega FROM configuracoes_entrega WHERE id=2"
                    )
                )
                == "auto_rota"
            )
            migration.downgrade()
        assert [
            column["name"]
            for column in sa.inspect(connection).get_columns("configuracoes_entrega")
        ] == ["id"]
    engine.dispose()
