"""whatsapp security/LGPD: tenant_id UUID + TenantScoped (Leva 3)

As quatro tabelas legadas de LGPD/seguranca do WhatsApp passam a ser cobertas
pelo filtro global de tenant via TenantScoped. Em producao, validado read-only
em 2026-06-11: tenant_id esta textual NOT NULL, sem nulos e sem valores
invalidos para UUID.

Revision ID: pp20260611a1
Revises: po20260610a1
Create Date: 2026-06-11 08:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pp20260611a1"
down_revision: Union[str, None] = "po20260610a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = (
    "data_privacy_consents",
    "data_access_logs",
    "data_deletion_requests",
    "security_audit_logs",
)


def _table_names(insp) -> set[str]:
    return set(insp.get_table_names())


def _column(insp, table: str, column: str):
    if table not in _table_names(insp):
        return None
    return {col["name"]: col for col in insp.get_columns(table)}.get(column)


def _index_names(insp, table: str) -> set[str]:
    if table not in _table_names(insp):
        return set()
    return {index["name"] for index in insp.get_indexes(table)}


def _is_uuid_column(col) -> bool:
    return col is not None and str(col["type"]).upper() == "UUID"


def _create_tenant_index_if_missing(insp, table: str) -> None:
    index_name = f"ix_{table}_tenant_id"
    if index_name in _index_names(insp, table):
        return
    op.create_index(index_name, table, ["tenant_id"], unique=False)


def _drop_tenant_index_if_present(insp, table: str) -> None:
    index_name = f"ix_{table}_tenant_id"
    if index_name in _index_names(insp, table):
        op.drop_index(index_name, table_name=table)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    insp = sa.inspect(bind)
    for table in _TABLES:
        col = _column(insp, table, "tenant_id")
        if col is None:
            continue

        if not _is_uuid_column(col):
            op.alter_column(
                table,
                "tenant_id",
                existing_type=sa.Text(),
                type_=postgresql.UUID(as_uuid=True),
                existing_nullable=False,
                postgresql_using="tenant_id::uuid",
            )
            insp = sa.inspect(bind)

        _create_tenant_index_if_missing(insp, table)
        insp = sa.inspect(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    insp = sa.inspect(bind)
    for table in reversed(_TABLES):
        col = _column(insp, table, "tenant_id")
        if col is None or not _is_uuid_column(col):
            continue

        _drop_tenant_index_if_present(insp, table)
        op.alter_column(
            table,
            "tenant_id",
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.Text(),
            existing_nullable=False,
            postgresql_using="tenant_id::text",
        )
        insp = sa.inspect(bind)
