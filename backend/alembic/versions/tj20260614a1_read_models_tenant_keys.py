"""prepare read model tenant keys

Revision ID: tj20260614a1
Revises: ti20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "tj20260614a1"
down_revision = "ti20260614a1"
branch_labels = None
depends_on = None


READ_MODEL_TABLES = {
    "read_vendas_resumo_diario": {
        "tenant_key": ("tenant_id", "data"),
        "tenant_index": "uq_read_vendas_resumo_tenant_data",
        "legacy_indexes": (
            "idx_vendas_resumo_data",
            "idx_vendas_resumo_data_unique",
            "read_vendas_resumo_diario_data_key",
        ),
        "legacy_constraints": ("read_vendas_resumo_diario_data_key",),
        "downgrade_index": "idx_vendas_resumo_data_unique",
        "downgrade_key": ("data",),
    },
    "read_performance_parceiro": {
        "tenant_key": ("tenant_id", "funcionario_id", "mes_referencia"),
        "tenant_index": "uq_read_perf_tenant_func_mes",
        "extra_indexes": {
            "idx_perf_tenant_mes_ranking": (
                "tenant_id",
                "mes_referencia",
                "ranking_mes",
            ),
        },
        "legacy_indexes": (
            "idx_perf_func_mes",
            "idx_perf_func_mes_unique",
            "idx_perf_mes_ranking",
            "read_performance_parceiro_funcionario_id_mes_referencia_key",
        ),
        "legacy_constraints": ("read_performance_parceiro_funcionario_id_mes_referencia_key",),
        "downgrade_index": "idx_perf_func_mes_unique",
        "downgrade_key": ("funcionario_id", "mes_referencia"),
    },
    "read_receita_mensal": {
        "tenant_key": ("tenant_id", "mes_referencia"),
        "tenant_index": "uq_read_receita_tenant_mes",
        "legacy_indexes": (
            "idx_receita_mes",
            "idx_receita_mes_unique",
            "read_receita_mensal_mes_referencia_key",
        ),
        "legacy_constraints": ("read_receita_mensal_mes_referencia_key",),
        "downgrade_index": "idx_receita_mes_unique",
        "downgrade_key": ("mes_referencia",),
    },
}


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _schema_names(table_name: str, *, kind: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()

    reader = inspector.get_columns if kind == "columns" else inspector.get_indexes
    return {item["name"] for item in reader(table_name)}


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    return _schema_names(table_name, kind="columns")


def _indexes(table_name: str) -> set[str]:
    return _schema_names(table_name, kind="indexes")


def _drop_postgres_constraint(table_name: str, constraint_name: str) -> None:
    if _dialect_name() != "postgresql":
        return
    op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")


def _drop_index(index_name: str) -> None:
    op.execute(f"DROP INDEX IF EXISTS {index_name}")


def _create_unique_index(table_name: str, index_name: str, columns: tuple[str, ...]) -> None:
    table_columns = _columns(table_name)
    if not set(columns).issubset(table_columns):
        return
    if index_name in _indexes(table_name):
        return
    op.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
        f"ON {table_name} ({', '.join(columns)})"
    )


def _create_index(table_name: str, index_name: str, columns: tuple[str, ...]) -> None:
    table_columns = _columns(table_name)
    if not set(columns).issubset(table_columns):
        return
    if index_name in _indexes(table_name):
        return
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {index_name} "
        f"ON {table_name} ({', '.join(columns)})"
    )


def _ensure_base_tenant_columns(table_name: str) -> None:
    table_columns = _columns(table_name)
    if "tenant_id" not in table_columns:
        op.add_column(table_name, sa.Column("tenant_id", sa.UUID(), nullable=True))
        table_columns.add("tenant_id")
    if "created_at" not in table_columns:
        op.add_column(
            table_name,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        table_columns.add("created_at")
    if "updated_at" not in table_columns:
        op.add_column(
            table_name,
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def upgrade() -> None:
    for table_name, config in READ_MODEL_TABLES.items():
        if not _table_exists(table_name):
            continue

        _ensure_base_tenant_columns(table_name)

        for constraint_name in config.get("legacy_constraints", ()):
            _drop_postgres_constraint(table_name, constraint_name)
        for index_name in config.get("legacy_indexes", ()):
            _drop_index(index_name)

        _create_unique_index(
            table_name,
            config["tenant_index"],
            config["tenant_key"],
        )
        for index_name, columns in config.get("extra_indexes", {}).items():
            _create_index(table_name, index_name, columns)


def downgrade() -> None:
    for table_name, config in reversed(READ_MODEL_TABLES.items()):
        if not _table_exists(table_name):
            continue

        for index_name in config.get("extra_indexes", {}):
            _drop_index(index_name)
        _drop_index(config["tenant_index"])

        _create_unique_index(
            table_name,
            config["downgrade_index"],
            config["downgrade_key"],
        )
