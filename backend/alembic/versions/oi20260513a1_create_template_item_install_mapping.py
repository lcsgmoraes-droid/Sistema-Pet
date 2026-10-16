"""create template item install mapping

Revision ID: oi20260513a1
Revises: oh20260513a1
Create Date: 2026-05-13 13:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "oi20260513a1"
down_revision = "oh20260513a1"
branch_labels = None
depends_on = None


def _bind():
    return op.get_bind()


def _inspector():
    return sa.inspect(_bind())


def _table_exists(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        index["name"] == index_name for index in _inspector().get_indexes(table_name)
    )


def _create_index_once(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _drop_index_once(index_name: str, table_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    if not _table_exists("tenant_template_item_installs"):
        op.create_table(
            "tenant_template_item_installs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("bundle_code", sa.String(length=80), nullable=False),
            sa.Column("bundle_version", sa.String(length=40), nullable=False),
            sa.Column("item_type", sa.String(length=80), nullable=False),
            sa.Column("template_code", sa.String(length=120), nullable=False),
            sa.Column("target_table", sa.String(length=120), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=False),
            sa.Column(
                "status", sa.String(length=40), nullable=False, server_default="active"
            ),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint(
                "tenant_id",
                "bundle_code",
                "bundle_version",
                "item_type",
                "template_code",
                name="uq_tenant_template_item_installs_template",
            ),
        )

    _create_index_once(
        "ix_tenant_template_item_installs_id", "tenant_template_item_installs", ["id"]
    )
    _create_index_once(
        "ix_tenant_template_item_installs_tenant_id",
        "tenant_template_item_installs",
        ["tenant_id"],
    )
    _create_index_once(
        "ix_tenant_template_item_installs_bundle_code",
        "tenant_template_item_installs",
        ["bundle_code"],
    )
    _create_index_once(
        "ix_tenant_template_item_installs_bundle_version",
        "tenant_template_item_installs",
        ["bundle_version"],
    )
    _create_index_once(
        "ix_tenant_template_item_installs_item_type",
        "tenant_template_item_installs",
        ["item_type"],
    )
    _create_index_once(
        "ix_tenant_template_item_installs_template_code",
        "tenant_template_item_installs",
        ["template_code"],
    )
    _create_index_once(
        "ix_tenant_template_item_installs_target",
        "tenant_template_item_installs",
        ["target_table", "target_id"],
    )


def downgrade() -> None:
    for index_name in (
        "ix_tenant_template_item_installs_target",
        "ix_tenant_template_item_installs_template_code",
        "ix_tenant_template_item_installs_item_type",
        "ix_tenant_template_item_installs_bundle_version",
        "ix_tenant_template_item_installs_bundle_code",
        "ix_tenant_template_item_installs_tenant_id",
        "ix_tenant_template_item_installs_id",
    ):
        _drop_index_once(index_name, "tenant_template_item_installs")
    if _table_exists("tenant_template_item_installs"):
        op.drop_table("tenant_template_item_installs")
