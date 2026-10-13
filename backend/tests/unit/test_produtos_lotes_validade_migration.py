import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_migration_preserva_lotes_anteriores_e_persiste_identificacao():
    caminho = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/zzzl20261009a1_lotes_apenas_identificacao.py"
    )
    spec = importlib.util.spec_from_file_location(
        "lotes_identificacao_migration", caminho
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "zzzk20261009a1"

    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE produto_lotes (id INTEGER PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO produto_lotes (id) VALUES (1)"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            # Lotes anteriores continuam sendo entradas normais, sem conversão de origem.
            assert (
                conn.execute(
                    sa.text("SELECT apenas_identificacao FROM produto_lotes WHERE id=1")
                ).scalar()
                == 0
            )
            conn.execute(
                sa.text(
                    "INSERT INTO produto_lotes (id, apenas_identificacao) VALUES (2, true)"
                )
            )
            assert (
                conn.execute(
                    sa.text("SELECT apenas_identificacao FROM produto_lotes WHERE id=2")
                ).scalar()
                == 1
            )
            migration.downgrade()
        assert [
            item["name"] for item in sa.inspect(conn).get_columns("produto_lotes")
        ] == ["id"]
    engine.dispose()
