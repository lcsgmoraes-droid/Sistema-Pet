"""add tenant_id nullable to dre_periodos

Revision ID: of20260512a1
Revises: oe20260512a1
Create Date: 2026-05-12 21:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "of20260512a1"
down_revision = "oe20260512a1"
branch_labels = None
depends_on = None


TABLE_NAME = "dre_periodos"
USERS_TABLE = "users"
IX_TENANT = "ix_dre_periodos_tenant_id"
IX_TENANT_DATAS_CANAL = "ix_dre_periodos_tenant_datas_canal"
IX_TENANT_MES_ANO_CANAL = "ix_dre_periodos_tenant_mes_ano_canal"


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _create_index_if_possible(index_name: str, columns: tuple[str, ...]) -> None:
    table_columns = _columns(TABLE_NAME)
    if not set(columns).issubset(table_columns):
        return
    if index_name in _indexes(TABLE_NAME):
        return
    quoted_columns = ", ".join(columns)
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {index_name} ON {TABLE_NAME} ({quoted_columns})"
    )


def _backfill_tenant_id() -> None:
    if not _table_exists(USERS_TABLE):
        return
    if not {"usuario_id", "tenant_id"}.issubset(_columns(TABLE_NAME)):
        return
    if not {"id", "tenant_id"}.issubset(_columns(USERS_TABLE)):
        return

    dialect_name = op.get_bind().dialect.name
    if dialect_name == "postgresql":
        op.execute(
            """
            UPDATE dre_periodos dp
            SET tenant_id = u.tenant_id
            FROM users u
            WHERE dp.usuario_id = u.id
              AND dp.tenant_id IS NULL
              AND u.tenant_id IS NOT NULL
            """
        )
        return

    op.execute(
        """
        UPDATE dre_periodos
        SET tenant_id = (
            SELECT u.tenant_id
            FROM users u
            WHERE u.id = dre_periodos.usuario_id
              AND u.tenant_id IS NOT NULL
        )
        WHERE tenant_id IS NULL
          AND usuario_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM users u
              WHERE u.id = dre_periodos.usuario_id
                AND u.tenant_id IS NOT NULL
          )
        """
    )


def upgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    if "tenant_id" not in _columns(TABLE_NAME):
        op.add_column(TABLE_NAME, sa.Column("tenant_id", sa.UUID(), nullable=True))

    _create_index_if_possible(IX_TENANT, ("tenant_id",))
    _backfill_tenant_id()
    _create_index_if_possible(
        IX_TENANT_DATAS_CANAL,
        ("tenant_id", "data_inicio", "data_fim", "canal"),
    )
    _create_index_if_possible(
        IX_TENANT_MES_ANO_CANAL,
        ("tenant_id", "mes", "ano", "canal"),
    )


def downgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    op.execute(f"DROP INDEX IF EXISTS {IX_TENANT_MES_ANO_CANAL}")
    op.execute(f"DROP INDEX IF EXISTS {IX_TENANT_DATAS_CANAL}")
    op.execute(f"DROP INDEX IF EXISTS {IX_TENANT}")

    if "tenant_id" in _columns(TABLE_NAME):
        op.drop_column(TABLE_NAME, "tenant_id")
