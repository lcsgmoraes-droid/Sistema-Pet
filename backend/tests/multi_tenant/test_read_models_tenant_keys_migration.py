from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect, text

from app.read_models.models import (
    PerformanceParceiro,
    ReceitaMensal,
    VendasResumoDiario,
)
from tests.multi_tenant.rls_migration_helpers import load_migration


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "tj20260614a1_read_models_tenant_keys.py"
)

TABLE_COLUMNS = {
    "read_vendas_resumo_diario": (
        "data DATE NOT NULL",
        "quantidade_aberta INTEGER DEFAULT 0",
    ),
    "read_performance_parceiro": (
        "funcionario_id INTEGER NOT NULL",
        "mes_referencia DATE NOT NULL",
        "quantidade_vendas INTEGER DEFAULT 0",
    ),
    "read_receita_mensal": (
        "mes_referencia DATE NOT NULL",
        "receita_bruta NUMERIC DEFAULT 0",
    ),
}

LEGACY_INDEXES = {
    "read_vendas_resumo_diario": ("idx_vendas_resumo_data_unique", ("data",)),
    "read_performance_parceiro": (
        "idx_perf_func_mes_unique",
        ("funcionario_id", "mes_referencia"),
    ),
    "read_receita_mensal": ("idx_receita_mes_unique", ("mes_referencia",)),
}


def _load_migration():
    return load_migration(MIGRATION_PATH)


def _run_migration(migration, engine, action):
    with engine.begin() as connection:

        def execute(statement):
            if isinstance(statement, str):
                return connection.execute(text(statement))
            return connection.execute(statement)

        def add_column(table_name, column):
            type_sql = "TEXT" if column.name == "tenant_id" else "DATETIME"
            nullable_sql = "" if column.nullable else " NOT NULL"
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column.name} {type_sql}{nullable_sql}"
                )
            )

        fake_op = SimpleNamespace(
            get_bind=lambda: connection,
            execute=execute,
            add_column=add_column,
        )
        migration[action].__globals__["op"] = fake_op
        migration[action]()


def _create_schema(*, include_tenant_id=True):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        for table_name, columns in TABLE_COLUMNS.items():
            table_columns = ["id INTEGER PRIMARY KEY"]
            if include_tenant_id:
                table_columns.append("tenant_id TEXT NULL")
            table_columns.extend(columns)
            connection.execute(
                text(f"CREATE TABLE {table_name} ({', '.join(table_columns)})")
            )

        for table_name, (index_name, columns) in LEGACY_INDEXES.items():
            connection.execute(
                text(
                    f"CREATE UNIQUE INDEX {index_name} "
                    f"ON {table_name} ({', '.join(columns)})"
                )
            )
    return engine


def _index_map(engine, table_name):
    return {index["name"]: index for index in inspect(engine).get_indexes(table_name)}


def _columns(engine, table_name):
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def test_migration_metadata():
    migration = _load_migration()

    assert migration["revision"] == "tj20260614a1"
    assert migration["down_revision"] == "ti20260614a1"


def test_upgrade_cria_indices_unicos_por_tenant_e_remove_legados():
    migration = _load_migration()
    engine = _create_schema()

    _run_migration(migration, engine, "upgrade")

    for table_name, config in migration["READ_MODEL_TABLES"].items():
        index_name = config["tenant_index"]
        indexes = _index_map(engine, table_name)
        assert index_name in indexes
        assert bool(indexes[index_name]["unique"]) is True
        assert LEGACY_INDEXES[table_name][0] not in indexes


def test_upgrade_adiciona_tenant_id_em_tabelas_legadas():
    migration = _load_migration()
    engine = _create_schema(include_tenant_id=False)

    _run_migration(migration, engine, "upgrade")

    for table_name, config in migration["READ_MODEL_TABLES"].items():
        assert "tenant_id" in _columns(engine, table_name)
        assert config["tenant_index"] in _index_map(engine, table_name)


def test_downgrade_remove_indices_tenant_aware_e_recria_legados():
    migration = _load_migration()
    engine = _create_schema()

    _run_migration(migration, engine, "upgrade")
    _run_migration(migration, engine, "downgrade")

    for table_name, config in migration["READ_MODEL_TABLES"].items():
        indexes = _index_map(engine, table_name)
        assert config["tenant_index"] not in indexes
        assert config["downgrade_index"] in indexes


def _unique_index_columns(model, index_name):
    for index in model.__table__.indexes:
        if index.name == index_name:
            return index.unique, tuple(column.name for column in index.columns)
    raise AssertionError(f"Indice {index_name} nao encontrado em {model.__name__}")


def test_models_de_read_model_declaram_indices_unicos_por_tenant():
    assert _unique_index_columns(
        VendasResumoDiario,
        "uq_read_vendas_resumo_tenant_data",
    ) == (True, ("tenant_id", "data"))
    assert _unique_index_columns(
        PerformanceParceiro,
        "uq_read_perf_tenant_func_mes",
    ) == (True, ("tenant_id", "funcionario_id", "mes_referencia"))
    assert _unique_index_columns(
        ReceitaMensal,
        "uq_read_receita_tenant_mes",
    ) == (True, ("tenant_id", "mes_referencia"))
