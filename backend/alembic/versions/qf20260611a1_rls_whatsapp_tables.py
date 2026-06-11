"""enable RLS on WhatsApp tenant tables

Revision ID: qf20260611a1
Revises: qd20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "qf20260611a1"
down_revision = "qd20260611a1"
branch_labels = None
depends_on = None


WHATSAPP_RLS_TABLES = (
    "tenant_whatsapp_config",
    "whatsapp_ia_sessions",
    "whatsapp_ia_messages",
    "whatsapp_ia_metrics",
    "whatsapp_agents",
    "whatsapp_handoffs",
    "whatsapp_internal_notes",
    "data_privacy_consents",
    "data_access_logs",
    "data_deletion_requests",
    "security_audit_logs",
)

TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _postgres_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_whatsapp_tables(bind) -> tuple[str, ...]:
    inspector = sa.inspect(bind)
    return tuple(table for table in WHATSAPP_RLS_TABLES if inspector.has_table(table))


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _commands(table_name: str, *, enable: bool) -> tuple[str, ...]:
    policy = _policy_name(table_name)
    if enable:
        return (
            f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
            f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
            f"DROP POLICY IF EXISTS {policy} ON {table_name}",
            (
                f"CREATE POLICY {policy} ON {table_name} "
                f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
            ),
        )
    return (
        f"DROP POLICY IF EXISTS {policy} ON {table_name}",
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY",
    )


def _apply_policy(table_names: tuple[str, ...], *, enable: bool) -> None:
    ordered_tables = table_names if enable else tuple(reversed(table_names))
    for table_name in ordered_tables:
        for statement in _commands(table_name, enable=enable):
            op.execute(statement)


def upgrade() -> None:
    bind = _postgres_bind()
    if bind is None:
        return

    _apply_policy(_existing_whatsapp_tables(bind), enable=True)


def downgrade() -> None:
    bind = _postgres_bind()
    if bind is None:
        return

    _apply_policy(_existing_whatsapp_tables(bind), enable=False)
