"""enable RLS on campaign reward tenant tables

Revision ID: py20260611a1
Revises: px20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "py20260611a1"
down_revision = "px20260611a1"
branch_labels = None
depends_on = None


REWARD_TABLES = (
    "loyalty_stamps",
    "cashback_transactions",
    "coupons",
    "coupon_redemptions",
)

TENANT_SCOPE = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _bind_if_postgresql():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else None


def _available_reward_tables(bind) -> tuple[str, ...]:
    inspector = sa.inspect(bind)
    return tuple(table for table in REWARD_TABLES if inspector.has_table(table))


def _tenant_policy(table: str) -> str:
    return f"{table}_tenant_isolation"


def _install_policy(table: str) -> None:
    policy = _tenant_policy(table)
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute(
        f"CREATE POLICY {policy} ON {table} "
        f"USING ({TENANT_SCOPE}) WITH CHECK ({TENANT_SCOPE})"
    )


def _remove_policy(table: str) -> None:
    policy = _tenant_policy(table)
    op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    bind = _bind_if_postgresql()
    if bind is None:
        return

    existing_tables = _available_reward_tables(bind)
    for table in REWARD_TABLES:
        if table in existing_tables:
            _install_policy(table)


def downgrade() -> None:
    bind = _bind_if_postgresql()
    if bind is None:
        return

    existing_tables = _available_reward_tables(bind)
    for table in reversed(REWARD_TABLES):
        if table in existing_tables:
            _remove_policy(table)
