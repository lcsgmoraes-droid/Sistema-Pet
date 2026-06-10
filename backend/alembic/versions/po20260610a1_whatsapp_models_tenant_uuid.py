"""whatsapp core: tenant_id UUID + TenantScoped (Leva 2)

As quatro tabelas centrais do WhatsApp passam a ser cobertas pelo filtro global
de tenant via TenantScoped. Em producao, validado read-only em 2026-06-10:
tenant_id ja esta como UUID NOT NULL nas quatro tabelas; esta migration fica
idempotente para ambientes antigos onde a coluna ainda esteja textual.

Revision ID: po20260610a1
Revises: pn20260610a1
Create Date: 2026-06-10 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "po20260610a1"
down_revision: Union[str, None] = "pn20260610a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = (
    "tenant_whatsapp_config",
    "whatsapp_ia_sessions",
    "whatsapp_ia_messages",
    "whatsapp_ia_metrics",
)


def _table_names(insp) -> set[str]:
    return set(insp.get_table_names())


def _column(insp, table: str, column: str):
    if table not in _table_names(insp):
        return None
    return {col["name"]: col for col in insp.get_columns(table)}.get(column)


def _is_uuid_column(col) -> bool:
    return col is not None and str(col["type"]).upper() == "UUID"


def _tenant_fk_names(insp, table: str) -> list[str]:
    names: list[str] = []
    for fk in insp.get_foreign_keys(table):
        if fk.get("referred_table") != "tenants":
            continue
        if fk.get("constrained_columns") == ["tenant_id"]:
            if fk.get("name"):
                names.append(fk["name"])
    return names


def _create_tenant_fk_if_missing(insp, table: str) -> None:
    if "tenants" not in _table_names(insp):
        return
    if _tenant_fk_names(insp, table):
        return
    op.create_foreign_key(
        f"{table}_tenant_id_fkey",
        table,
        "tenants",
        ["tenant_id"],
        ["id"],
    )


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
            for fk_name in _tenant_fk_names(insp, table):
                op.drop_constraint(fk_name, table, type_="foreignkey")

            op.alter_column(
                table,
                "tenant_id",
                existing_type=sa.String(),
                type_=postgresql.UUID(as_uuid=True),
                existing_nullable=False,
                postgresql_using="tenant_id::uuid",
            )

            insp = sa.inspect(bind)

        _create_tenant_fk_if_missing(insp, table)
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

        for fk_name in _tenant_fk_names(insp, table):
            op.drop_constraint(fk_name, table, type_="foreignkey")

        op.alter_column(
            table,
            "tenant_id",
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.String(),
            existing_nullable=False,
            postgresql_using="tenant_id::text",
        )
        insp = sa.inspect(bind)
