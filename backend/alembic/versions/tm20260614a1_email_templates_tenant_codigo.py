"""prepare email templates tenant codigo uniqueness

Revision ID: tm20260614a1
Revises: tl20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "tm20260614a1"
down_revision = "tl20260614a1"
branch_labels = None
depends_on = None


EMAIL_TEMPLATES_TABLE = "emails_templates"
LEGACY_CODIGO_INDEX = "ix_emails_templates_codigo"
TENANT_CODIGO_INDEX = "uq_emails_templates_tenant_codigo"


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _index_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _drop_index(index_name: str) -> None:
    if index_name in _index_names(EMAIL_TEMPLATES_TABLE):
        op.drop_index(index_name, table_name=EMAIL_TEMPLATES_TABLE)


def _create_index(index_name: str, columns: tuple[str, ...], *, unique: bool) -> None:
    if index_name not in _index_names(EMAIL_TEMPLATES_TABLE):
        op.create_index(index_name, EMAIL_TEMPLATES_TABLE, list(columns), unique=unique)


def upgrade() -> None:
    if not _table_exists(EMAIL_TEMPLATES_TABLE):
        return

    _drop_index(LEGACY_CODIGO_INDEX)
    _create_index(LEGACY_CODIGO_INDEX, ("codigo",), unique=False)
    _create_index(TENANT_CODIGO_INDEX, ("tenant_id", "codigo"), unique=True)


def downgrade() -> None:
    if not _table_exists(EMAIL_TEMPLATES_TABLE):
        return

    _drop_index(TENANT_CODIGO_INDEX)
    _drop_index(LEGACY_CODIGO_INDEX)
    _create_index(LEGACY_CODIGO_INDEX, ("codigo",), unique=True)
