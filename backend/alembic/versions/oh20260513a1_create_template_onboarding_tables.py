"""create template onboarding tables

Revision ID: oh20260513a1
Revises: og20260512a1
Create Date: 2026-05-13 11:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "oh20260513a1"
down_revision = "og20260512a1"
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
    if not _table_exists("template_bundles"):
        op.create_table(
            "template_bundles",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("bundle_code", sa.String(length=80), nullable=False),
            sa.Column("version", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
            ),
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
                "bundle_code", "version", name="uq_template_bundles_code_version"
            ),
        )
    _create_index_once("ix_template_bundles_id", "template_bundles", ["id"])
    _create_index_once(
        "ix_template_bundles_bundle_code", "template_bundles", ["bundle_code"]
    )
    _create_index_once("ix_template_bundles_version", "template_bundles", ["version"])

    if not _table_exists("template_items"):
        op.create_table(
            "template_items",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("bundle_code", sa.String(length=80), nullable=False),
            sa.Column("bundle_version", sa.String(length=40), nullable=False),
            sa.Column("item_type", sa.String(length=80), nullable=False),
            sa.Column("template_code", sa.String(length=120), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
            ),
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
                "bundle_code",
                "bundle_version",
                "item_type",
                "template_code",
                name="uq_template_items_bundle_type_code",
            ),
        )
    _create_index_once("ix_template_items_id", "template_items", ["id"])
    _create_index_once(
        "ix_template_items_bundle_code", "template_items", ["bundle_code"]
    )
    _create_index_once(
        "ix_template_items_bundle_version", "template_items", ["bundle_version"]
    )
    _create_index_once("ix_template_items_item_type", "template_items", ["item_type"])
    _create_index_once(
        "ix_template_items_template_code", "template_items", ["template_code"]
    )

    if not _table_exists("tenant_template_installs"):
        op.create_table(
            "tenant_template_installs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("bundle_code", sa.String(length=80), nullable=False),
            sa.Column("bundle_version", sa.String(length=40), nullable=False),
            sa.Column(
                "status",
                sa.String(length=40),
                nullable=False,
                server_default="completed",
            ),
            sa.Column(
                "dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")
            ),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column(
                "summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
            ),
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
                name="uq_tenant_template_installs_tenant_bundle_version",
            ),
        )
    _create_index_once(
        "ix_tenant_template_installs_id", "tenant_template_installs", ["id"]
    )
    _create_index_once(
        "ix_tenant_template_installs_tenant_id",
        "tenant_template_installs",
        ["tenant_id"],
    )
    _create_index_once(
        "ix_tenant_template_installs_bundle_code",
        "tenant_template_installs",
        ["bundle_code"],
    )
    _create_index_once(
        "ix_tenant_template_installs_bundle_version",
        "tenant_template_installs",
        ["bundle_version"],
    )


def downgrade() -> None:
    for index_name in (
        "ix_tenant_template_installs_bundle_version",
        "ix_tenant_template_installs_bundle_code",
        "ix_tenant_template_installs_tenant_id",
        "ix_tenant_template_installs_id",
    ):
        _drop_index_once(index_name, "tenant_template_installs")
    if _table_exists("tenant_template_installs"):
        op.drop_table("tenant_template_installs")

    for index_name in (
        "ix_template_items_template_code",
        "ix_template_items_item_type",
        "ix_template_items_bundle_version",
        "ix_template_items_bundle_code",
        "ix_template_items_id",
    ):
        _drop_index_once(index_name, "template_items")
    if _table_exists("template_items"):
        op.drop_table("template_items")

    for index_name in (
        "ix_template_bundles_version",
        "ix_template_bundles_bundle_code",
        "ix_template_bundles_id",
    ):
        _drop_index_once(index_name, "template_bundles")
    if _table_exists("template_bundles"):
        op.drop_table("template_bundles")
